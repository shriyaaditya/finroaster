import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.services.deprecated.playwright_executor import execute_cancellation

print("=== 1. Testing Playwright Execution Engine directly ===")
async def test_playwright():
    res = await execute_cancellation(
        vendor_name="Test Vendor",
        url="https://example.com",
        requires_auth=False
    )
    print("Execution Result:", res)
    assert res["status"] == "success"
    assert res["vendor"] == "Test Vendor"

asyncio.run(test_playwright())

print("\n=== 2. Testing POST /cancel-subscription Endpoint ===")
client = TestClient(app)

response = client.post(
    "/cancel-subscription",
    json={
        "vendor": "Amazon Prime",
        "url": "https://example.com",
        "requires_auth": False
    }
)

print("Endpoint Status Code:", response.status_code)
print("Endpoint Response Payload:", response.json())
assert response.status_code == 200
assert response.json()["status"] == "success"

print("\n✅ STAGE 2 VERIFICATION PASSED SUCCESSFULLY!")
