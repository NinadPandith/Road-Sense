"""M12: experiment E5 - does merging work? Ride the same route twice, then check that each real
pothole ends up as exactly one map point.

Input CSV: one row per uploaded report from both rides, with a hand-assigned pothole_id
(look at the photos; use 'none' for false detections):
    report_id,ride,lat,lon,pothole_id
Export the rows with backend/scripts/export_reports.py --survey <ride1> --survey <ride2>.

Runs DBSCAN (haversine, min_samples = 1) at several radii, like the PRD specifies, and reports:
- merge accuracy: share of real potholes whose reports all fall in one cluster holding no other
  pothole;
- duplicates left: extra clusters for potholes that were split;
- wrongly merged: clusters holding two or more different potholes.

Usage:
    python -m scripts.eval_merge data/merge_eval.csv
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.cluster import DBSCAN

from scripts.common import RESULTS, markdown_table, write_json

EARTH_M = 6_371_000
RADII = [2, 3, 5, 8, 10, 15]


def cluster(latlon: np.ndarray, eps_m: float) -> np.ndarray:
    db = DBSCAN(eps=eps_m / EARTH_M, min_samples=1, metric="haversine", algorithm="ball_tree")
    return db.fit_predict(np.radians(latlon))


def score(labels: np.ndarray, potholes: list[str]) -> dict:
    by_pothole: dict[str, set[int]] = defaultdict(set)
    by_cluster: dict[int, set[str]] = defaultdict(set)
    for c, p in zip(labels, potholes, strict=True):
        if p and p.lower() != "none":
            by_pothole[p].add(int(c))
            by_cluster[int(c)].add(p)
    real = len(by_pothole)
    correct = sum(
        1 for cs in by_pothole.values() if len(cs) == 1 and len(by_cluster[next(iter(cs))]) == 1
    )
    return {
        "reports": len(potholes),
        "real_potholes": real,
        "clusters": int(len(set(labels.tolist()))),
        "merge_accuracy": correct / real if real else 0.0,
        "duplicates_left": sum(len(cs) - 1 for cs in by_pothole.values()),
        "wrongly_merged": sum(1 for ps in by_cluster.values() if len(ps) > 1),
    }


def run(path: Path, out_dir: Path = RESULTS) -> dict:
    rows = list(csv.DictReader(path.open()))
    latlon = np.array([[float(r["lat"]), float(r["lon"])] for r in rows])
    potholes = [r["pothole_id"].strip() for r in rows]
    sweep = []
    for eps in RADII:
        s = score(cluster(latlon, eps), potholes)
        sweep.append({"eps_m": eps, **s})
    before = {"reports": len(rows), "real_potholes": sweep[0]["real_potholes"]}
    result = {"before": before, "sweep": sweep, "chosen_eps_m": 5}
    write_json("e5_merge.json", result, out_dir)
    (out_dir / "e5_merge.md").write_text(
        markdown_table(
            ["Radius (m)", "Clusters", "Merge accuracy", "Duplicates left", "Wrongly merged"],
            [
                [
                    s["eps_m"],
                    s["clusters"],
                    s["merge_accuracy"],
                    s["duplicates_left"],
                    s["wrongly_merged"],
                ]
                for s in sweep
            ],
        )
    )
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path, default=RESULTS)
    a = ap.parse_args()
    res = run(a.csv, a.out)
    for s in res["sweep"]:
        print(s)


if __name__ == "__main__":
    main()
