from flask import Flask, jsonify, request
from celery import Celery
from celery.result import AsyncResult
import redis
import config_app
import json 
from datetime import datetime, timezone
from solvers.solver_dispatch import dispatch_solver

SUPPORTED_FILE_EXTENSIONS = {"mps"}

redis_server = redis.Redis(config_app.REDIS_HOST, config_app.REDIS_PORT)

app = Flask(__name__)

# Configure Celery
xxx = Celery(app.name, backend=config_app.CELERY_RESULT_BACKEND, broker=config_app.CELERY_BROKER_URL)
xxx.conf.update(
    result_persistent=True,
    result_expires=3600,
)


@xxx.task
def solve_lp_payload_task(content: str, metadata: dict) -> dict:
    task_id = solve_lp_payload_task.request.id
    try:
        result = dispatch_solver(content, metadata)
        return {**result, "task_id": task_id}
    except Exception as e:
        return {**metadata, "error": str(e), "task_id": task_id}


@app.route('/solve_lp_payload', methods=['POST'])
def solve_lp_payload():
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({"error": "Missing 'content' key in JSON payload"}), 400

    content = data['content']
    metadata = data["metadata"]
    source_file_name = metadata.get('source_file_name', 'unknown_file')
    content_file_ext = metadata.get('content_file_ext', 'unknown_format')
    user_id = metadata.get('user_id', 'anonymous')
    submitted_at = datetime.now(timezone.utc).isoformat()

    if content_file_ext not in SUPPORTED_FILE_EXTENSIONS:
        return jsonify({
            "error": f"Unsupported content_file_ext: '{content_file_ext}'. Supported formats: {', '.join(SUPPORTED_FILE_EXTENSIONS)}"
        }), 400

    # Store task metadata
    metadata = {
        "source_file_name": source_file_name,
        "content_file_ext": content_file_ext,
        "user_id": user_id,
        "submitted_at": submitted_at,
    }
    # task = solve_mps_highs_payload.delay(content, metadata)
    task = solve_lp_payload_task.delay(content, metadata)

    redis_server.hset("lp_tasks", task.id, json.dumps(metadata))

    return jsonify({
        "task_id": task.id,
        "status": "task submitted",
        "metadata": metadata
    }), 202



@app.route('/check_lp_task/<task_id>', methods=['GET'])
def check_lp_task(task_id):
    some_result = AsyncResult(task_id, app=xxx)
    REDIS_KEY = "lp_tasks"

    # task_found = task_id in redis_server.hvals(REDIS_KEY)
    task_found = redis_server.hexists(REDIS_KEY, task_id)

    if not task_found:
        return jsonify({"result": None, "exists": False, "error": "Task ID not found"}), 404

    if some_result.ready():
        result_data = some_result.get()

        return jsonify({"result": result_data, "exists": True, "ready":True}), 200
    else:
        return jsonify({"result": None, "exists": True, "ready":False}), 202 

if __name__ == '__main__':
    app.run(debug=True)