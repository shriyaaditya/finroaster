import io
import datetime
import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# Import our roast generation module
from roaster import generate_roast
from chronos import ChronosPipeline

app = FastAPI(title="FinRoast API")

# Add CORS Middleware to support requests from the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Chronos Pipeline once at startup
print("Loading Chronos forecasting model...")
pipeline = ChronosPipeline.from_pretrained(
    "amazon/chronos-t5-small",
    device_map="cpu",
    dtype=torch.float32,
)

class HistoricalItem(BaseModel):
    date: str
    amount: float

class ForecastItem(BaseModel):
    date: str
    p10: float
    p50: float
    p90: float

class ForecastResponse(BaseModel):
    historical: List[HistoricalItem]
    forecast: List[ForecastItem]
    roast: str

@app.post("/forecast/upload", response_model=ForecastResponse)
async def upload_transactions(file: UploadFile = File(...)):
    # 1. Read CSV Upload
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {str(e)}")

    # 2. Normalize and Validate Headers
    col_mapping = {col.strip().lower(): col for col in df.columns}
    required_cols = ["date", "amount", "category"]
    for col in required_cols:
        if col not in col_mapping:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required column: {col.capitalize()}. CSV must contain Date, Amount, and Category."
            )

    # Rename columns to standard lowercase names
    df = df.rename(columns={col_mapping[c]: c for c in required_cols})

    # 3. Clean and parse data
    try:
        df["date"] = pd.to_datetime(df["date"])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.dropna(subset=["date", "amount"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing date or amount columns: {str(e)}")

    # Standardize on spending: filter out income (amounts <= 0)
    df = df[df["amount"] > 0]

    if df.empty:
        raise HTTPException(
            status_code=400, 
            detail="The CSV contains no valid positive expense transactions."
        )

    # 4. Group by Date to get total daily spend
    df_sorted = df.sort_values(by="date")
    daily_spend = df_sorted.groupby(df_sorted["date"].dt.date)["amount"].sum().sort_index()

    if len(daily_spend) == 0:
        raise HTTPException(status_code=400, detail="Not enough historical spend data to forecast.")

    # 5. Execute Chronos 14-day Forecast
    # Convert daily spend values to torch tensor
    context_values = daily_spend.values.astype(np.float32)
    context_tensor = torch.tensor(context_values, dtype=torch.float32)
    
    try:
        # Perform inference
        raw_forecast = pipeline.predict(context_tensor, prediction_length=14)
        
        # Calculate percentiles (10th, 50th, 90th) across the samples
        p10, p50, p90 = np.percentile(raw_forecast[0].numpy(), [10, 50, 90], axis=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chronos inference failed: {str(e)}")

    # 6. Generate dates for the 14-day forecast
    last_date = daily_spend.index[-1]
    forecast_dates = [
        (last_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(1, 15)
    ]

    # Assemble response items
    historical_items = [
        HistoricalItem(date=d.strftime("%Y-%m-%d"), amount=float(a))
        for d, a in daily_spend.items()
    ]
    
    forecast_items = [
        ForecastItem(
            date=forecast_dates[i],
            p10=max(0.0, float(p10[i])), # Clamp negative spending to 0
            p50=max(0.0, float(p50[i])),
            p90=max(0.0, float(p90[i]))
        )
        for i in range(14)
    ]

    # Generate the roast based on historical items and forecast items
    # Pass raw transactions for category details
    raw_tx_list = [
        {"date": row["date"].strftime("%Y-%m-%d"), "amount": float(row["amount"]), "category": str(row["category"])}
        for _, row in df.iterrows()
    ]
    
    forecast_list = [item.model_dump() for item in forecast_items]
    
    try:
        roast_text = generate_roast(raw_tx_list, forecast_list)
    except Exception as e:
        roast_text = "Your spending is so unpredictable even the AI is speechless. Try buying less stuff."

    return ForecastResponse(
        historical=historical_items,
        forecast=forecast_items,
        roast=roast_text
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8055, reload=True)
