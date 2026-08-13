import sys
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MedallionPipeline")
PROJECT_ROOT = Path(__file__).resolve().parent
STAGES = [
    {
        "name": "BRONZE (Ingestion)",
        "script": ["1_bronze_ingestion.py", "bronze/1_bronze_ingestion.py"],
    },
    {
        "name": "SILVER (Cleansing & ETL)",
        "script": ["2_silver_transformation.py", "silver/2_silver_transformation.py"],
    },
    {
        "name": "GOLD (Dimensional Modeling)",
        "script": ["3_gold_dimensional_modeling.py", "gold/3_gold_dimensional_modeling.py", "gold/3_gold_dimensional_modelling.py"],
    },
    {
        "name": "ANALYTICS (RFM & Cohorts)",
        "script": ["4_analytics_and_rfm.py", "4_analytics.py"],
    },
]

def find_script(possible_paths):
    """Searches for script file across potential relative locations."""
    for rel_path in possible_paths:
        full_path = PROJECT_ROOT / rel_path
        if full_path.exists():
            return full_path
    return None

def run_stage(stage_info):
    """Executes a single pipeline stage script in an isolated subprocess."""
    stage_name = stage_info["name"]
    script_path = find_script(stage_info["script"])

    if not script_path:
        logger.error(f"Failed to locate script for {stage_name}. Checked: {stage_info['script']}")
        return False, 0.0

    logger.info(f"Starting Stage: {stage_name}")
    logger.info(f"   Script: {script_path.relative_to(PROJECT_ROOT)}")

    start_time = time.perf_counter()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=False 
        )
        duration = time.perf_counter() - start_time
        logger.info(f"Completed Stage: {stage_name} in {duration:.2f}s\n")
        return True, duration

    except subprocess.CalledProcessError as e:
        duration = time.perf_counter() - start_time
        logger.error(f"Failed Stage: {stage_name} after {duration:.2f}s")
        logger.error(f"   Exit Code: {e.returncode}\n")
        return False, duration

def main():
    """Main Orchestrator Entry Point."""
    pipeline_start = time.perf_counter()

    print("\n" + "=" * 65)
    print("      MEDALLION DATA LAKEHOUSE PIPELINE ORCHESTRATOR      ")
    print(f"   Execution Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65 + "\n")

    results = []
    pipeline_failed = False

    for stage in STAGES:
        success, duration = run_stage(stage)
        results.append({
            "stage": stage["name"],
            "status": "SUCCESS" if success else "FAILED",
            "duration": duration
        })

        if not success:
            logger.error("Halting execution due to stage failure.")
            pipeline_failed = True
            break

    total_duration = time.perf_counter() - pipeline_start
    print("=" * 65)
    print("                 PIPELINE EXECUTION SUMMARY                  ")
    print("=" * 65)
    print(f"{'Stage Name':<35} | {'Status':<10} | {'Time (s)':<10}")
    print("-" * 65)
    
    for res in results:
        print(f"{res['stage']:<35} | {res['status']:<10} | {res['duration']:>8.2f}s")
    
    print("-" * 65)
    print(f"{'TOTAL PIPELINE RUNTIME':<35} | {'COMPLETE':<10} | {total_duration:>8.2f}s")
    print("=" * 65 + "\n")

    if pipeline_failed:
        sys.exit(1)

if __name__ == "__main__":
    main()