import subprocess
import time
import requests
import sys

print("Starting FastAPI app backend server on port 8055...")
proc = subprocess.Popen(
    ["./venv/bin/uvicorn", "main:app", "--port", "8055"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Wait 8 seconds for server to start and load the Chronos weights
print("Waiting for server to spin up and load models...")
time.sleep(8)

# Check if process is still running
status = proc.poll()
if status is not None:
    print(f"Server process terminated early with exit code {status}!")
    stdout, stderr = proc.communicate()
    print("STDOUT:")
    print(stdout)
    print("STDERR:")
    print(stderr)
    sys.exit(1)

print("Sending test request to /forecast/upload...")
csv_path = "synthetic_transactions.csv"
try:
    with open(csv_path, "rb") as f:
        response = requests.post(
            "http://127.0.0.1:8055/forecast/upload",
            files={"file": (csv_path, f, "text/csv")}
        )
    
    print("\nResponse Status Code:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print("\nHistorical spend count:", len(data.get("historical", [])))
        print("Forecast items count:", len(data.get("forecast", [])))
        print("\nMedian Forecast Example (First Day):", data.get("forecast")[0])
        print("Median Forecast Example (Last Day):", data.get("forecast")[-1])
        print("\nGenerated Roast:\n", data.get("roast"))
        print("\nBackend validation: SUCCESS!")
    else:
        print("Error Response:", response.text)
        print("Backend validation: FAILED!")
except Exception as e:
    print("Verification request failed:", e)
finally:
    print("Stopping FastAPI server...")
    proc.terminate()
    stdout, stderr = proc.communicate()
    print("\nServer Output Logs (STDOUT):")
    print(stdout)
    print("\nServer Error Logs (STDERR):")
    print(stderr)
