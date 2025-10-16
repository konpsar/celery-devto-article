import os
import time
import requests
import pytest
from pathlib import Path

API_BASE = "http://localhost:5000"
TIMEOUT_SEC = 60
POLL_INTERVAL = 0.5
test_files_dir = Path(__file__).parent / "test_problems" 

TEST_PROBLEMS = [
    {
        "filename": test_files_dir / "example1.mps",
        "expected": {
            "objective": 3.0,
            "model_status": "Optimal",
            "variables": [1.0, 0.0],
            "iteration_count": 0,
        },
    },
    {
        "filename": test_files_dir / "example2.mps",
        "expected": {
            "objective": 12.0,
            "model_status": "Optimal",
            "variables": [4.0, 2.0, 0.0],
            "iteration_count": 1,
        },
    },
    {
        "filename": test_files_dir / "example3.mps",
        "expected": {
            "objective": 54.0,
            "model_status": "Optimal",
            "variables": [4.0, -1.0, 6.0],
        },
    },
    {
        "filename": test_files_dir / "heavy_problem.mps",
        "expected": {
            "objective": 2809.999999999996,
            "model_status": "Optimal",
        },
    },
]


@pytest.mark.parametrize("problem", TEST_PROBLEMS, ids=lambda p: Path(p["filename"]).name)
def test_mps_problem(problem):
    path = problem["filename"]
    assert path.exists(), f"Missing: {path}"

    content = path.read_text()

    payload = {
        "content": content,
        "metadata": {
            "source_file_name": os.path.basename(path),
            "content_file_ext": "mps",
            "user_id": "pytest_user"
        }
    }

    print(f"\nSubmitting: {os.path.basename(path)}")
    post = requests.post(f"{API_BASE}/solve_lp_payload", json=payload)
    assert post.status_code == 202, f"Submission failed: {post.text}"
    task_id = post.json().get("task_id")
    assert task_id

    print(f"... Waiting for task ID: {task_id} ...")

    start_time = time.monotonic()
    while True:
        get = requests.get(f"{API_BASE}/check_lp_task/{task_id}")
        if get.status_code == 200:
            data = get.json()
            if data.get("ready") and data.get("result") is not None:
                result = data["result"]
                break
        elif get.status_code == 202:
            # Still processing, just wait
            pass
        else:
            pytest.fail(f"Unexpected status code: {get.status_code} → {get.text}")
        
        if time.monotonic() - start_time > TIMEOUT_SEC:
            pytest.fail(f"Timeout waiting for task {task_id}")
        
        elapsed = int(time.monotonic() - start_time)
        remaining = TIMEOUT_SEC - elapsed
        print(f"Waiting {elapsed}s... (Timeout in {remaining}s)", end="\r", flush=True)
        time.sleep(POLL_INTERVAL)


    print(f"Result for {path} - Objective: {result.get('objective')}, Status: {result.get('model_status')}")

    # Basic checks
    assert result["task_status"] == "success"
    assert result["model_status"] == problem["expected"]["model_status"]
    assert result["objective"] == pytest.approx(problem["expected"]["objective"], abs=1e-3)
    # Number of variables and values
    expected_vars = problem["expected"].get("variables")
    if expected_vars is not None:
        assert result["variables"] == pytest.approx(expected_vars, abs=1e-3), "Variable values mismatch"
    # Iteration count if defined
    if "iteration_count" in problem["expected"]:
        assert result.get("iteration_count") == problem["expected"]["iteration_count"]
    # Validate runtime is > 0
    assert result.get("runtime_sec", 0) > 0


def test_unsupported_file_type():
    unsupported_path = test_files_dir / "unsupported.random"
    assert unsupported_path.exists(), f"Missing fixture: {unsupported_path}"

    content = unsupported_path.read_text()

    payload = {
        "content": content,
        "metadata": {
            "source_file_name": unsupported_path.name,
            "content_file_ext": unsupported_path.suffix.lstrip("."),  # "random"
            "user_id": "pytest_user",
        },
    }

    print("\nSubmitting unsupported file type (.random)")
    res = requests.post(f"{API_BASE}/solve_lp_payload", json=payload)
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"

    try:
        msg = res.json().get("message", res.text)
    except Exception:
        msg = res.text

    assert "Unsupported" in msg
    print("Correctly rejected unsupported file type")

