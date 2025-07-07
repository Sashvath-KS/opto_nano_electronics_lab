# main.py

import json
from experiment import PLExperiment

def main():
    with open("config_user.json") as f:
        config = json.load(f)
    experiment_type = config.get("experiment_type", "degradation")

    exp = PLExperiment()

    try:
        if experiment_type == "steady_state":
            exp.run_steady_state()
        elif experiment_type == "degradation":
            exp.run_degradation_study()
        elif experiment_type == "pre_tuning":
            exp.run_pre_tuning()
        else:
            raise ValueError(f"Unknown experiment type: {experiment_type}")
    finally:
        exp.shutdown()

if __name__ == "__main__":
    main()
