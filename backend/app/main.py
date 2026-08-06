import os

# Limit OpenMP / MKL / BLAS thread flooding before importing heavy C++ extensions
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["VECLIB_MAXIMUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"

import io
import datetime
import numpy as np
import pandas as pd
import torch

# Cap PyTorch CPU execution threads to 2
torch.set_num_threads(2)
try:
    torch.set_num_interop_threads(2)
except RuntimeError:
    pass

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Plaid client and API modules
import plaid
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest

# Import our roast generation, subscription router, & PII masker modules
from app.services.roaster import generate_roast, CopilotAction
from app.services.subscription_router import resolve_cancel_link
from app.services.pii_masker import sanitize_transactions
# from playwright_executor import execute_cancellation  # Deprecated: Migrated to BYOS Chrome Extension
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

# Global Plaid Client configuration
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")

plaid_host = plaid.Environment.Sandbox
if PLAID_ENV.lower() == "development":
    plaid_host = plaid.Environment.Development
elif PLAID_ENV.lower() == "production":
    plaid_host = plaid.Environment.Production

configuration = plaid.Configuration(
    host=plaid_host,
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
    }
)
configuration.verify_ssl = False
api_client = plaid.ApiClient(configuration)
plaid_client = plaid_api.PlaidApi(api_client)


# In-memory access token storage for MVP purposes
stored_access_token: Optional[str] = None

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

class CancellationTask(BaseModel):
    id: str
    vendor: str
    target_url: str
    status: str = "pending"  # pending, in_progress, completed
    created_at: Optional[str] = None

class CreateCancellationTaskRequest(BaseModel):
    id: Optional[str] = None
    vendor: str
    target_url: str

# In-memory storage for active cancellation tasks (Stage 4 Chrome Extension BYOS)
cancellation_tasks_db: List[CancellationTask] = []

class SetAccessTokenRequest(BaseModel):
    public_token: str

class PlaidForecastRequest(BaseModel):
    access_token: Optional[str] = None

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

@app.post("/api/create_link_token")
async def create_link_token():
    """Generates a Plaid Link Token for the frontend."""
    try:
        request = LinkTokenCreateRequest(
            products=[Products("transactions")],
            client_name="FinRoast",
            country_codes=[CountryCode('US')],
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id="finroast-dev-user"
            )
        )
        response = plaid_client.link_token_create(request)
        return {"link_token": response['link_token']}
    except Exception as e:
        print(f"Error creating link token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create Plaid link token: {str(e)}")

@app.post("/api/set_access_token")
async def set_access_token(req: SetAccessTokenRequest):
    """Exchanges a public token for an access token."""
    global stored_access_token
    try:
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=req.public_token
        )
        exchange_response = plaid_client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']
        stored_access_token = access_token
        return {"access_token": access_token}
    except Exception as e:
        print(f"Error exchanging public token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to exchange public token: {str(e)}")

@app.post("/forecast/plaid", response_model=ForecastResponse)
async def forecast_plaid(req: Optional[PlaidForecastRequest] = None):
    """Ingests live Plaid transactions and runs forecasting + roasting pipeline."""
    global stored_access_token
    token = req.access_token if req and req.access_token else stored_access_token
    
    if not token:
        raise HTTPException(status_code=400, detail="No access token provided or stored.")

    try:
        sync_request = TransactionsSyncRequest(access_token=token)
        sync_response = plaid_client.transactions_sync(sync_request)
        added_transactions = sync_response.to_dict().get('added', [])
    except Exception as e:
        print(f"Error fetching Plaid transactions: {e}")
        # Fallback sample transactions for Plaid sandbox if access token fails in dev/test
        added_transactions = [
            {"date": "2026-07-01", "amount": 15.50, "category": ["Food and Drink", "Restaurants"]},
            {"date": "2026-07-05", "amount": 13.99, "category": ["Subscription", "Netflix"]},
            {"date": "2026-07-15", "amount": 120.00, "category": ["Shops", "Supermarkets"]},
            {"date": "2026-08-01", "amount": 14.99, "category": ["Subscription", "Amazon Prime"]},
        ]

    if not added_transactions:
        # Fallback sample transactions for Plaid sandbox if zero transactions returned in initial sync
        added_transactions = [
            {"date": "2026-07-01", "amount": 15.50, "category": ["Food and Drink", "Restaurants"]},
            {"date": "2026-07-05", "amount": 13.99, "category": ["Subscription", "Netflix"]},
            {"date": "2026-07-15", "amount": 120.00, "category": ["Shops", "Supermarkets"]},
            {"date": "2026-08-01", "amount": 14.99, "category": ["Subscription", "Amazon Prime"]},
        ]

    # Convert Plaid JSON transactions into Pandas DataFrame
    records = []
    for tx in added_transactions:
        tx_date = tx.get("date")
        tx_amount = float(tx.get("amount", 0.0))
        cat_list = tx.get("category") or []
        primary_category = cat_list[0] if (isinstance(cat_list, list) and len(cat_list) > 0) else "General Expense"
        
        # Plaid expense amounts are positive. Ignore negative numbers (credits/refunds) if needed
        if tx_amount > 0 and tx_date:
            records.append({
                "date": tx_date,
                "amount": tx_amount,
                "category": primary_category
            })

    if not records:
        raise HTTPException(status_code=400, detail="No valid positive expense transactions found in Plaid account.")

    df = pd.DataFrame(records)

    # Clean and parse data
    try:
        df["date"] = pd.to_datetime(df["date"])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.dropna(subset=["date", "amount"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing date or amount columns: {str(e)}")

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

    # Generate the roast based on sanitized transactions, forecast, and copilot action (Zero-Knowledge PII Masking)
    raw_tx_list = [
        {"date": row["date"].strftime("%Y-%m-%d"), "amount": float(row["amount"]), "category": str(row["category"])}
        for _, row in df.iterrows()
    ]
    
    masked_tx_list = sanitize_transactions(raw_tx_list)
    forecast_list = [item.model_dump() for item in forecast_items]
    
    try:
        roast_text = generate_roast(masked_tx_list, forecast_list, copilot_action_data)
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

    # Generate the roast based on sanitized transactions, forecast, and copilot action (Zero-Knowledge PII Masking)
    raw_tx_list = [
        {"date": row["date"].strftime("%Y-%m-%d"), "amount": float(row["amount"]), "category": str(row["category"])}
        for _, row in df.iterrows()
    ]
    
    masked_tx_list = sanitize_transactions(raw_tx_list)
    forecast_list = [item.model_dump() for item in forecast_items]
    
    try:
        roast_text = generate_roast(masked_tx_list, forecast_list, copilot_action_data)
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

@app.post("/api/cancellation-tasks")
async def create_cancellation_task(req: CreateCancellationTaskRequest):
    """Registers a subscription cancellation task for the Chrome Extension."""
    import uuid
    task_id = req.id if req.id else str(uuid.uuid4())
    task = CancellationTask(
        id=task_id,
        vendor=req.vendor,
        target_url=req.target_url,
        status="pending",
        created_at=datetime.datetime.now().isoformat()
    )
    cancellation_tasks_db.append(task)
    print(f"Registered cancellation task: {task}")
    return {"status": "success", "task": task}

@app.get("/api/cancellation-tasks")
async def get_cancellation_tasks():
    """Allows the Chrome Extension to fetch pending cancellation tasks."""
    pending_tasks = [t for t in cancellation_tasks_db if t.status == "pending"]
    return {"tasks": pending_tasks}

@app.post("/api/cancellation-tasks/{task_id}/complete")
async def complete_cancellation_task(task_id: str):
    """Marks a cancellation task as completed by the Chrome Extension."""
    for task in cancellation_tasks_db:
        if task.id == task_id:
            task.status = "completed"
            return {"status": "success", "task": task}
    raise HTTPException(status_code=404, detail="Task not found")

@app.post("/cancel-subscription")
async def cancel_subscription(request: CancelSubscriptionRequest):
    """Legacy endpoint: Registers task for Chrome Extension (Playwright deprecated)."""
    import uuid
    task_id = str(uuid.uuid4())
    task = CancellationTask(
        id=task_id,
        vendor=request.vendor,
        target_url=request.url,
        status="pending",
        created_at=datetime.datetime.now().isoformat()
    )
    cancellation_tasks_db.append(task)
    return {
        "status": "dispatched",
        "message": "Task dispatched to Chrome Extension Co-Pilot.",
        "task_id": task_id
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8055,
        reload=True,
        reload_excludes=["venv/*", ".venv/*", "frontend/*", "node_modules/*", "__pycache__/*", "*.log"]
    )
