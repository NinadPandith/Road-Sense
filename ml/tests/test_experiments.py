import csv
import json

import numpy as np
import pytest

from scripts.build_results_json import build
from scripts.eval_merge import run as run_merge
from scripts.eval_merge import score
from scripts.eval_severity import PRD_WEIGHTS, scores, to_labels
from scripts.eval_severity import run as run_severity
from scripts.split_local import assign, find_segment


def test_severity_formula_matches_backend():
    x = np.array([[0.5, 0.5, 1.0, 1.0], [1, np.nan, 1, 1]])
    s = scores(x, PRD_WEIGHTS)
    assert s[0] == pytest.approx(0.35 * 0.5 + 0.35 * 0.5 + 0.2 + 0.1)
    assert s[1] == pytest.approx(1.0)  # missing depth -> other weights rescaled
    assert to_labels(np.array([0.39, 0.4, 0.69, 0.7])).tolist() == [0, 1, 1, 2]


def test_eval_severity_writes_e3_e4(tmp_path):
    rng = np.random.default_rng(0)
    rows = []
    for i in range(120):
        size, depth, typ, pos = (
            rng.random(),
            rng.random(),
            rng.choice([0.4, 0.5, 0.7, 1.0]),
            rng.random(),
        )
        true = 0.2 * size + 0.5 * depth + 0.2 * typ + 0.1 * pos  # people weigh depth more
        label = ["minor", "moderate", "dangerous"][int(np.digitize(true, [0.4, 0.7]))]
        rows.append(
            {"id": i, "label": label, "size": size, "depth": depth, "type": typ, "position": pos}
        )
    p = tmp_path / "sev.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    res = run_severity(p, tmp_path)
    held = res["e3"]["held_out_half"]
    assert held["tuned_weights"]["kappa_linear"] >= held["prd_weights"]["kappa_linear"]
    assert res["e3"]["tuned_weights"]["depth"] > 0.35  # tuning finds the heavier depth weight
    assert sum(res["e3"]["tuned_weights"].values()) == pytest.approx(1.0)
    without_depth = next(r for r in res["e4"]["ablation"] if r["variant"] == "without depth")
    assert without_depth["change"] < 0
    assert (tmp_path / "e3_confusion.png").exists()


def test_merge_scoring():
    labels = np.array([0, 0, 1, 2, 2, 3])
    potholes = ["a", "a", "b", "c", "d", "none"]
    s = score(labels, potholes)
    assert s["real_potholes"] == 4
    assert s["merge_accuracy"] == 0.5  # a and b fine; c and d merged together
    assert s["wrongly_merged"] == 1 and s["duplicates_left"] == 0


def test_eval_merge_two_rides(tmp_path):
    lat0, lon0 = 12.97, 77.59
    rows = []
    for k in range(10):  # 10 potholes 30 m apart, seen on two rides 3 m apart (GPS error)
        for ride in (1, 2):
            jitter = (ride - 1.5) * 3 / 111_320
            rows.append(
                {
                    "report_id": f"{k}-{ride}",
                    "ride": ride,
                    "lat": lat0 + k * 30 / 111_320 + jitter,
                    "lon": lon0,
                    "pothole_id": f"p{k}",
                }
            )
    p = tmp_path / "merge.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    res = run_merge(p, tmp_path)
    by_eps = {s["eps_m"]: s for s in res["sweep"]}
    assert by_eps[5]["merge_accuracy"] == 1.0 and by_eps[5]["clusters"] == 10
    assert by_eps[2]["duplicates_left"] > 0  # too small a radius leaves duplicates


def test_split_by_segment_keeps_segments_together():
    split = assign([f"ride1:{i}" for i in range(20)], seed=1)
    assert sorted(set(split.values())) == ["test", "train", "val"]
    assert list(split.values()).count("train") == 14
    seg = {"ride1_00012000": "ride1:3"}
    assert find_segment("ride1_00012000_jpg.rf.abc123", seg) == "ride1:3"


def test_results_bundle(tmp_path):
    res = tmp_path / "results"
    res.mkdir()
    (res / "e5_merge.json").write_text(json.dumps({"chosen_eps_m": 5}))
    data = build(res, tmp_path / "out")
    assert data["e5"] == {"chosen_eps_m": 5} and data["e1"] is None
    assert (tmp_path / "out" / "results.json").exists()
