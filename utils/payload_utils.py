
def parse_payload(payload: dict, env: dict):
    import gurobipy as gp
    from data_model import Aircraft
    from datetime import date

    model = gp.Model(env=env)
    namespace = payload.get("namespace", {})

    date_mapping_raw = namespace["date_mapping_serialized"]
    date_mapping = {
        date.fromisoformat(k): v for k, v in date_mapping_raw.items()
    }

    aircraft_dict = namespace["aircraft"]
    aircraft = {
        ac_id: Aircraft.from_dict(ac_data, date_mapping)
        for ac_id, ac_data in aircraft_dict.items()
    }


    return {
        "model": model,
        "aircraft": aircraft,
        "int_horizon": namespace["int_horizon"],
        "blackout_map": namespace["blackout_map"],
        "date_mapping": date_mapping,
        "wo_total": namespace["wo_total"],
        "max_day": namespace["max_day"],
        "max_concurrent_aircraft": namespace["max_concurrent_aircraft"],
        "weekend_counts": namespace["weekend_counts"],
    }