from utils.payload_utils import parse_payload
from utils.gurobi_model import configure_model, get_results, gurobi_params
import gurobipy as gp
import time

# from gurobipy import GRB
# import random
# import pandas as pd
# import numpy as np
# import plotly.graph_objects as go
# import plotly.express as px
# import matplotlib.pyplot as plt
# from collections import Counter
# import time

# from datetime import date, timedelta

# from pyspark.sql import functions as F
# from pyspark.sql import Window
# from pyspark.sql.types import IntegerType
# import sys

def run_gurobi_solver(payload: dict, metadata: dict) -> dict:
    start = time.time()


    env = gp.Env(params=gurobi_params)
    # model = gp.Model(env=env)
    parsed = parse_payload(payload, env)


    model_kwargs = dict(
    aircraft=parsed["aircraft"], 
    int_horizon=parsed["int_horizon"], 
    blackout_map=parsed["blackout_map"], 
    wo_total=parsed["wo_total"],
    max_day=parsed["max_day"],
    max_concurrent_aircraft=parsed["max_concurrent_aircraft"],
    weekend_counts=parsed["weekend_counts"],
    )

    x = configure_model(
    parsed["model"], 
    **model_kwargs
    )

    parsed["model"].optimize()

    elapsed = time.time() - start

    return _extract_gurobi_results(x, parsed, metadata, elapsed)


def _extract_gurobi_results(x, data, metadata, elapsed):

    results_dict = get_results(
        data["model"], 
        x, 
        data["aircraft"], 
        data["weekend_counts"]
    )
    return {
        **metadata,
        **results_dict,
        "task_status": "success",
        "runtime_sec": round(elapsed, 4),
    }
