import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8055"

def test_plaid_pipeline():
    print("--- STEP 1: Creating Plaid Link Token ---")
    res = requests.post(f"{BASE_URL}/api/create_link_token")
    assert res.status_code == 200, f"Create link token failed: {res.text}"
    link_token = res.json().get("link_token")
    assert link_token, "No link token returned"
    print(f"✓ Link token created successfully: {link_token[:20]}...")

    print("\n--- STEP 2: Testing Plaid Forecast Endpoint (with fallback transactions) ---")
    res_forecast = requests.post(
        f"{BASE_URL}/forecast/plaid",
        json={"access_token": "access-sandbox-fake-test-token"}
    )
    print(f"Response status: {res_forecast.status_code}")
    if res_forecast.status_code == 200:
        data = res_forecast.json()
        print(f"✓ Forecast generated successfully!")
        print(f"Historical points: {len(data['historical'])}")
        print(f"Forecast points: {len(data['forecast'])}")
        print(f"AI Roast preview: {data['roast'][:80]}...")
        if data.get("copilot_action"):
            print(f"Copilot Action Target: {data['copilot_action']['target_vendor']}")
    else:
        print(f"Status detail: {res_forecast.text}")

if __name__ == "__main__":
    test_plaid_pipeline()
