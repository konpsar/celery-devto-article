# import requests
# import os
# import json
# import redis

# API_BASE = "http://localhost:5000"
# REDIS_KEY = "lp_tasks"
# FILES = [
#     "test_problems/example1.mps",
#     "test_problems/example2.mps",
#     "test_problems/heavy_problem.mps",
#     "test_problems/misc07.mps",
# ]

# redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
# for path in FILES:
#     if not os.path.exists(path):
#         print(f"File missing: {path}")
#         continue

#     with open(path, "r") as f:
#         content = f.read()

#     payload = {
#         "content": content,
#     }

#     # resp = requests.post(f"{API_BASE}/solve_lp_payload", json={"content": content})
#     resp = requests.post(f"{API_BASE}/solve_lp_payload", json=payload)
#     if resp.status_code == 202:
#         task_id = resp.json().get("task_id")
#         redis_client.hset(REDIS_KEY, path, task_id)
#         print(f"✅ Submitted {path} → Task ID: {task_id}")
#     else:
#         print(f"❌ Failed to submit {path}: {resp.text}")



import requests
import os
import json
import redis
API_BASE = "http://localhost:5000"
REDIS_TASKS_KEY = "lp_tasks"
FILES = [
    "test_problems/example1.mps",
    "test_problems/example2.mps",
    "test_problems/heavy_problem.mps",
    "test_problems/misc07.mps",
    "test_problems/misc07.random",
]

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
user_id = "user_001"

for path in FILES:
    if not os.path.exists(path):
        print(f"File missing: {path}")
        continue

    with open(path, "r") as f:
        content = f.read()

    payload = {
        "content": content,
        "metadata": {
            "source_file_name": os.path.basename(path),
            "content_file_ext": path.split(".")[-1].lower(),
            # "file_size": os.path.getsize(path),
            "user_id": user_id,
        }
    }

    resp = requests.post(f"{API_BASE}/solve_lp_payload", json=payload)
    if resp.status_code == 202:
        task_id = resp.json().get("task_id")
        redis_client.hset(REDIS_TASKS_KEY, task_id, json.dumps(payload["metadata"]))
        print(f"✅ Submitted {path} → Task ID: {task_id}")
    else:
        print(f"❌ Failed to submit {path}: {resp.text}")