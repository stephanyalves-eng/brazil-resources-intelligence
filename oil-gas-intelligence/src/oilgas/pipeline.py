"""End-to-end pipeline runner.

CLI (from oil-gas-intelligence/src):
    python -m oilgas.pipeline                 # profile -> clean -> features -> eda -> stats -> charts -> export
    python -m oilgas.pipeline --download      # re-download raw files first
    python -m oilgas.pipeline --steps clean features
"""
from __future__ import annotations

import argparse
import time

from oilgas import acquisition, charts, cleaning, eda, features, profiling, stats_analysis, tableau_export

STEPS = {
    "download": acquisition.main,
    "profile": profiling.main,
    "clean": cleaning.main,
    "features": features.main,
    "eda": eda.main,
    "stats": stats_analysis.main,
    "charts": charts.main,
    "export": tableau_export.main,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--download", action="store_true", help="re-download raw data before running")
    ap.add_argument("--steps", nargs="+", choices=[s for s in STEPS if s != "download"],
                    default=["profile", "clean", "features", "eda", "stats", "charts", "export"])
    a = ap.parse_args()
    steps = (["download"] if a.download else []) + a.steps
    for s in steps:
        t = time.perf_counter()
        print(f"\n=== {s} ===")
        if s == "download":
            acquisition.acquire()
        else:
            STEPS[s]()
        print(f"=== {s} done in {time.perf_counter() - t:.1f}s ===")


if __name__ == "__main__":
    main()
