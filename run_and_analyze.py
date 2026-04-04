import subprocess
import os
import pandas as pd
import concurrent.futures

runs = {
    "sprint66_f1": "spec/proposals/sprint66_f1.yaml",
    "sprint66_f2": "spec/proposals/sprint66_f2.yaml",
    "sprint66_f3": "spec/proposals/sprint66_f3.yaml",
    "sprint66_f4": "spec/proposals/sprint66_f4.yaml",
    "sprint66_f5": "spec/proposals/sprint66_f5.yaml",
    "sprint66_f6_final": "spec/proposals/sprint66_f6.yaml",
    "sprint66_f7": "spec/proposals/sprint66_f7.yaml",
    "sprint66_f8": "spec/proposals/sprint66_f8.yaml",
    "sprint66_f9": "spec/proposals/sprint66_f9.yaml",
    "sprint66_f10": "spec/proposals/sprint66_f10.yaml",
}

def execute_run(run_id, proposal):
    cmd = [".venv/bin/python", "project/cli.py", "discover", "run", "--proposal", proposal, "--run_id", run_id]
    print(f"Executing {run_id}...")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Finished {run_id}")
    except subprocess.CalledProcessError as e:
        print(f"Error in {run_id}: {e.stderr.decode()}")

# Parallel execution with limited workers (4 to be safe)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(execute_run, rid, prop) for rid, prop in runs.items()]
    concurrent.futures.wait(futures)

# Analysis
results = []
for run_id in runs.keys():
    parquet_path = f"data/reports/phase2/{run_id}/regime_conditional_candidates.parquet"
    if os.path.exists(parquet_path):
        try:
            df = pd.read_parquet(parquet_path)
            if 't_stat' in df.columns:
                candidates = df[df['t_stat'] > 1.5]
                if not candidates.empty:
                    max_t = candidates['t_stat'].max()
                    results.append({"run_id": run_id, "best_t_stat": round(max_t, 4)})
                else:
                    max_t = df['t_stat'].max() if not df.empty else None
                    results.append({"run_id": run_id, "best_t_stat": f"None > 1.5 (Max: {round(max_t, 4)})" if max_t is not None else "No data"})
            else:
                results.append({"run_id": run_id, "best_t_stat": "Column t_stat not found"})
        except Exception as e:
            results.append({"run_id": run_id, "best_t_stat": f"Error: {str(e)}"})
    else:
        results.append({"run_id": run_id, "best_t_stat": "Parquet file not found"})

summary_df = pd.DataFrame(results)
print("\n--- Summary Table ---")
print(summary_df.to_string(index=False))
