from solvers.highs_mps import run_highs_on_mps

def dispatch_solver(content: str, metadata: dict) -> dict:
    content_file_ext = metadata.get("content_file_ext", "").lower()

    if content_file_ext == "mps":
        return run_highs_on_mps(content, metadata)
    else:
        raise ValueError(f"Unsupported content_file_ext: '{content_file_ext}'")
