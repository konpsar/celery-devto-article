
import time
import time
import os
from highspy import Highs
import tempfile

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