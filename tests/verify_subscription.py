import json
import pandas as pd
from fastapi.testclient import TestClient
from app.services.subscription_router import resolve_cancel_link
from app.main import app, detect_parasitic_subscriptions
from app.services.roaster import generate_roast

print("=== 1. Testing Subscription Router Tier 1 & Tier 2 ===")
res1 = resolve_cancel_link("Amazon Prime")
print("Tier 1 (Amazon Prime):", json.dumps(res1, indent=2))
assert res1["action_mode"] == "playwright_auto"
assert res1["requires_auth"] == True
assert res1["target_url"] == "https://www.amazon.com/mc/pipelines/cancellation"

res2 = resolve_cancel_link("Gym Membership XYZ")
print("\nTier 2 (Unknown Vendor):", json.dumps(res2, indent=2))
assert res2["action_mode"] == "tavily_search"
assert res2["target_vendor"] == "Gym Membership XYZ"

print("\n=== 2. Testing Anomaly Detection ===")
sample_df = pd.DataFrame([
    {"date": "2026-06-01", "amount": 14.99, "category": "Netflix"},
    {"date": "2026-07-01", "amount": 14.99, "category": "Netflix"},
    {"date": "2026-07-05", "amount": 120.00, "category": "Dining"}
])
sample_df["date"] = pd.to_datetime(sample_df["date"])
detected = detect_parasitic_subscriptions(sample_df)
print("Detected subscription vendor:", detected)
assert detected == "Netflix"

print("\n=== 3. Testing Roast Generation with Copilot Action ===")
sample_hist = [
    {"date": "2026-06-01", "amount": 14.99, "category": "Netflix"},
    {"date": "2026-07-01", "amount": 14.99, "category": "Netflix"}
]
sample_forecast = [
    {"date": "2026-07-02", "p10": 10.0, "p50": 15.0, "p90": 25.0}
]
roast = generate_roast(sample_hist, sample_forecast, res1)
print("Generated Roast with Action:\n", roast)

print("\n=== 4. Testing End-to-End FastAPI Upload Endpoint ===")
client = TestClient(app)

with open("synthetic_transactions.csv", "rb") as f:
    response = client.post("/forecast/upload", files={"file": ("synthetic_transactions.csv", f, "text/csv")})

print("Endpoint status code:", response.status_code)
assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"

data = response.json()
print("Response JSON keys:", list(data.keys()))
print("Copilot Action payload:", json.dumps(data.get("copilot_action"), indent=2))
print("Roast:\n", data.get("roast"))

print("\n✅ ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
