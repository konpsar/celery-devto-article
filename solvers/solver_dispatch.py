from solvers.highs_mps import run_highs_on_mps
from solvers.gurobi_runner import  run_gurobi_solver

def dispatch_solver(content: str, metadata: dict, payload: dict) -> dict:
    content_file_ext = metadata.get("content_file_ext", "").lower()
    payload_type = metadata.get("payload_type", "").lower()

    if content_file_ext == "mps":
        return run_highs_on_mps(content, metadata)
    elif payload_type == "gurobi":
        return run_gurobi_solver(payload, metadata)
    else:
        raise ValueError(f"Unsupported content_file_ext: '{content_file_ext}'")
