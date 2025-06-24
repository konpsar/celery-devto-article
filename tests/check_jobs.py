import requests
import redis
import argparse
import json 

def print_lp_result(result: dict, detailed: bool = False) -> None:
    print(f"\nTask ID        : {result.get('task_id')}")
    print(f"Submitted by   : {result.get('user_id')}")
    print(f"Source file    : {result.get('source_file_name')}")
    print(f"Content file extension : {result.get('content_file_ext')}")
    print(f"Submitted at   : {result.get('submitted_at')}")

    if "error" in result:
        print(f"\nError          : {result['error']}")
        return

    print(f"\nTask status    : {result.get('task_status', 'unknown')}")
    print(f"Model status   : {result.get('model_status')}")
    print(f"Objective      : {result.get('objective')}")
    print(f"Iteration count: {result.get('iteration_count')}")
    print(f"Runtime (sec)  : {result.get('runtime_sec')}")
    print(f"Variables      : {result.get('variables')}")

    if detailed:
        print(f"Dual values    : {result.get('dual_values')}")
        print(f"Row values     : {result.get('row_values')}")
        print(f"Row duals      : {result.get('row_duals')}")
        print(f"Primal status  : {result.get('primal_status')}")
        print(f"Dual status    : {result.get('dual_status')}")
        print(f"Basis validity : {result.get('basis_validity')}")




API_BASE = "http://localhost:5000"
REDIS_KEY = "lp_tasks"

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

tasks = redis_client.hgetall(REDIS_KEY)

if not tasks:
    print("No tasks found in Redis.")
    exit()

for task_id, meta_str in tasks.items():
    try:
        url = f"{API_BASE}/check_lp_task/{task_id}"
        resp = requests.get(url)
        data = resp.json()
        metadata = json.loads(meta_str)

        print(f"\n🔍 {task_id} → Metadata: {metadata}")
        if not data.get("exists"):
            print("❌ Task not found")
        elif data.get("result") in [None, "output file missing"]:
            print("⏳ Still running...")
        else:
            print("✅ Done")
            result = data["result"]
            print_lp_result(result, detailed=False)
    except Exception as e:
        print(f"Error checking task {task_id}: {str(e)}")
