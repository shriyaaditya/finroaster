import os
import time
import requests

BASE_URL = "http://localhost:8055"

def test_stage4_task_pipeline():
    print("=== STEP 1: Creating Cancellation Task ===")
    payload = {
        "vendor": "Amazon Prime",
        "target_url": "https://www.amazon.com/mc/pipelines/cancellation"
    }
    res = requests.post(f"{BASE_URL}/api/cancellation-tasks", json=payload)
    print("POST /api/cancellation-tasks status:", res.status_code)
    assert res.status_code == 200, f"Failed creating task: {res.text}"
    
    data = res.json()
    task = data.get("task", {})
    task_id = task.get("id")
    print(f"✓ Task registered successfully: ID={task_id}, Vendor={task.get('vendor')}")

    print("\n=== STEP 2: Polling Cancellation Tasks (Chrome Extension Simulation) ===")
    res_get = requests.get(f"{BASE_URL}/api/cancellation-tasks")
    print("GET /api/cancellation-tasks status:", res_get.status_code)
    assert res_get.status_code == 200, f"Failed getting tasks: {res_get.text}"
    
    tasks_list = res_get.json().get("tasks", [])
    matching_task = next((t for t in tasks_list if t["id"] == task_id), None)
    assert matching_task, "Created task not found in pending tasks list!"
    print(f"✓ Extension poll received task: {matching_task['vendor']} ({matching_task['target_url']})")

    print("\n=== STEP 3: Marking Task Complete ===")
    res_complete = requests.post(f"{BASE_URL}/api/cancellation-tasks/{task_id}/complete")
    print("POST complete status:", res_complete.status_code)
    assert res_complete.status_code == 200, f"Failed completing task: {res_complete.text}"
    print("✓ Task marked completed successfully!")

    print("\n✅ STAGE 4 VERIFICATION PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_stage4_task_pipeline()
