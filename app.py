from flask import Flask, jsonify, request
from celery import Celery
from celery.result import AsyncResult
import time
import redis
import config_app
import time
import json 
import os
from datetime import datetime, timezone
from highspy import Highs
import tempfile

SUPPORTED_FILE_EXTENSIONS = {"mps"}

redis_server = redis.Redis(config_app.REDIS_HOST, config_app.REDIS_PORT)

app = Flask(__name__)

# Configure Celery
xxx = Celery(app.name, backend=config_app.CELERY_RESULT_BACKEND, broker=config_app.CELERY_BROKER_URL)
xxx.conf.update(
    result_persistent=True,
    result_expires=3600,
)


def run_highs_on_mps(content: str, metadata: dict) -> dict:
    start = time.time()

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".mps", delete=False) as tmp_file:
        tmp_file.write(content)
        tmp_file.flush()
        mps_path = tmp_file.name

    highs = Highs()
    highs.readModel(mps_path)
    highs.run()
    os.remove(mps_path)

    elapsed = time.time() - start
    return _extract_highs_results(highs, metadata, elapsed)


def _extract_highs_results(highs: Highs, metadata: dict, elapsed: float) -> dict:
    info = highs.getInfo()
    solution = highs.getSolution()
    model_status = highs.getModelStatus()

    return {
        **metadata,
        "task_status": "success",
        "model_status": highs.modelStatusToString(model_status),
        "objective": info.objective_function_value,
        "iteration_count": info.simplex_iteration_count,
        "primal_status": highs.solutionStatusToString(info.primal_solution_status),
        "dual_status": highs.solutionStatusToString(info.dual_solution_status),
        "basis_validity": highs.basisValidityToString(info.basis_validity),
        "variables": solution.col_value,
        "dual_values": solution.col_dual,
        "row_values": solution.row_value,
        "row_duals": solution.row_dual,
        "runtime_sec": round(elapsed, 4),
    }


@xxx.task
def solve_lp_payload_task(content: str, metadata: dict) -> dict:
    task_id = solve_lp_payload_task.request.id
    content_file_ext = metadata.get("content_file_ext", "").lower()

    try:
        if content_file_ext == "mps":
            result = run_highs_on_mps(content, metadata)
        else:
            raise ValueError(f"Unsupported content format: '{content_file_ext}'")

        return {
            **result,
            "task_id": task_id
        }

    except Exception as e:
        return {
            **metadata,
            "error": str(e),
            "task_id": task_id
        }

# @xxx.task
# def solve_mps_highs_payload(content: str, metadata: dict) -> dict:

#     task_id = solve_mps_highs_payload.request.id

#     try:
#         start = time.time()

#         with tempfile.NamedTemporaryFile(mode="w+", suffix=".mps", delete=False) as tmp_file:
#             tmp_file.write(content)
#             tmp_file.flush()
#             mps_path = tmp_file.name

#         highs = Highs()
#         highs.readModel(mps_path)
#         highs.run()
#         os.remove(mps_path)

#         elapsed = time.time() - start

#         return extract_highs_results(highs, metadata, elapsed, task_id)

#     except Exception as e:
#         return {
#             **metadata,
#             "error": str(e),
#             "task_id": task_id
#         }

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