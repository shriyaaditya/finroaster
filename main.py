import io
import datetime
import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Import our roast generation, subscription router, & playwright executor modules
from roaster import generate_roast, CopilotAction
from subscription_router import resolve_cancel_link
from playwright_executor import execute_cancellation
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
    copilot_action: Optional[CopilotAction] = None

class CancelSubscriptionRequest(BaseModel):
    vendor: str
    url: str
    requires_auth: bool = False

def detect_parasitic_subscriptions(df: pd.DataFrame) -> Optional[str]:
    """Flags recurring subscription charges (charges < $30 roughly 30 days apart or keyword match)."""
    try:
        df_sorted = df.sort_values(by="date").copy()
        
        # 1. Direct Category/Vendor keyword match
        known_keywords = ["amazon prime", "amazon", "netflix", "hulu", "spotify", "disney", "apple", "hbo", "youtube", "sub"]
        for cat in df_sorted["category"].dropna().unique():
            cat_str = str(cat).lower()
            for kw in known_keywords:
                if kw in cat_str:
                    return str(cat)

        # 2. Time-series pattern match: charges < $30 appearing ~25-35 days apart
        small_charges = df_sorted[df_sorted["amount"] < 30.0].copy()
        if len(small_charges) >= 2:
            for cat, group in small_charges.groupby("category"):
                if len(group) >= 2:
                    dates = group["date"].sort_values().tolist()
                    for i in range(len(dates) - 1):
                        diff_days = (dates[i+1] - dates[i]).days
                        if 25 <= diff_days <= 35:
                            return str(cat)
                            
        return None
    except Exception as e:
        print(f"Error detecting parasitic subscriptions: {e}")
        return None

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

    # 5. Detect Parasitic Subscriptions & Resolve Copilot Link
    flagged_vendor = detect_parasitic_subscriptions(df)
    copilot_action_data = None
    if flagged_vendor:
        try:
            copilot_action_data = resolve_cancel_link(flagged_vendor)
        except Exception as e:
            print(f"Error resolving cancellation link: {e}")

    # 6. Execute Chronos 14-day Forecast
    context_values = daily_spend.values.astype(np.float32)
    context_tensor = torch.tensor(context_values, dtype=torch.float32)
    
    try:
        raw_forecast = pipeline.predict(context_tensor, prediction_length=14)
        p10, p50, p90 = np.percentile(raw_forecast[0].numpy(), [10, 50, 90], axis=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chronos inference failed: {str(e)}")

    # 7. Generate dates for the 14-day forecast
    last_date = daily_spend.index[-1]
    forecast_dates = [
        (last_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(1, 15)
    ]

    historical_items = [
        HistoricalItem(date=d.strftime("%Y-%m-%d"), amount=float(a))
        for d, a in daily_spend.items()
    ]
    
    forecast_items = [
        ForecastItem(
            date=forecast_dates[i],
            p10=max(0.0, float(p10[i])),
            p50=max(0.0, float(p50[i])),
            p90=max(0.0, float(p90[i]))
        )
        for i in range(14)
    ]

    # Generate the roast based on historical items, forecast, and copilot action
    raw_tx_list = [
        {"date": row["date"].strftime("%Y-%m-%d"), "amount": float(row["amount"]), "category": str(row["category"])}
        for _, row in df.iterrows()
    ]
    
    forecast_list = [item.model_dump() for item in forecast_items]
    
    try:
        roast_text = generate_roast(raw_tx_list, forecast_list, copilot_action_data)
    except Exception as e:
        print(f"Roaster exception: {e}")
        roast_text = "Your spending is so unpredictable even the AI is speechless. Try buying less stuff."

    copilot_action_model = CopilotAction(**copilot_action_data) if copilot_action_data else None

    return ForecastResponse(
        historical=historical_items,
        forecast=forecast_items,
        roast=roast_text,
        copilot_action=copilot_action_model
    )

@app.post("/cancel-subscription")
async def cancel_subscription(request: CancelSubscriptionRequest):
    """Triggers Playwright execution engine to cancel a subscription."""
    try:
        result = await execute_cancellation(
            vendor_name=request.vendor,
            url=request.url,
            requires_auth=request.requires_auth
        )
        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail=result.get("message", "Cancellation failed."))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing subscription cancellation: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8055, reload=True)
