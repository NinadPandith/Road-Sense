"""M11: experiments E3 (does the severity score agree with people?) and E4 (which factors matter?).

Input CSV (one row per hand-labelled pothole), e.g. made by joining
ml/data/severity_labels.csv (id,label - labelled BEFORE looking at scores) with the factors exported
by backend/scripts/export_severity_factors.py:
    id,label,size,depth,type,position
label is minor / moderate / dangerous. depth may be empty (depth model skipped).

E3: accuracy, confusion matrix and weighted kappa of the PRD weights; then the weights are tuned
on a stratified half and both versions are scored on the other half (never tuned on).
E4: ablation - drop each factor (rescaling the rest) and report the change in kappa.

Usage:
    python -m scripts.eval_severity data/severity_eval.csv [--settings-out results/settings_v2.json]
"""

import argparse
import csv
import itertools
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix
from sklearn.model_selection import train_test_split

from scripts.common import RESULTS, markdown_table, write_json

LABELS = ["minor", "moderate", "dangerous"]
FACTORS = ["size", "depth", "type", "position"]
KEYS = {"size": "A", "depth": "D", "type": "T", "position": "P"}
PRD_WEIGHTS = {"size": 0.35, "depth": 0.35, "type": 0.20, "position": 0.10}
THRESHOLDS = (0.40, 0.70)


def load(path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rows = list(csv.DictReader(path.open()))
    x = np.array(
        [[float(r[f]) if r.get(f) not in (None, "") else np.nan for f in FACTORS] for r in rows]
    )
    y = np.array([LABELS.index(r["label"].strip().lower()) for r in rows])
    return x, y, [r["id"] for r in rows]


def scores(x: np.ndarray, w: dict[str, float]) -> np.ndarray:
    """The backend formula: weighted sum, with the weights of missing (or dropped) factors
    spread over the others so they still add up to 1."""
    wv = np.array([w[f] for f in FACTORS])
    present = ~np.isnan(x)
    num = np.nansum(x * wv, axis=1)
    den = (present * wv).sum(axis=1)
    return np.clip(num / np.where(den > 0, den, 1), 0, 1)


def to_labels(s: np.ndarray, thresholds=THRESHOLDS) -> np.ndarray:
    return np.digitize(s, thresholds)


def metrics(y: np.ndarray, pred: np.ndarray) -> dict:
    return {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "kappa_linear": float(cohen_kappa_score(y, pred, weights="linear", labels=[0, 1, 2])),
        "kappa_quadratic": float(cohen_kappa_score(y, pred, weights="quadratic", labels=[0, 1, 2])),
        "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1, 2]).tolist(),
        "labels": LABELS,
    }


def grid_search(x: np.ndarray, y: np.ndarray, step: float = 0.05) -> dict[str, float]:
    """All weight vectors on a 0.05 grid that sum to 1; maximise linear weighted kappa."""
    best, best_w = -2.0, PRD_WEIGHTS
    ticks = np.round(np.arange(0, 1 + 1e-9, step), 2)
    for a, d, t in itertools.product(ticks, ticks, ticks):
        p = round(1 - a - d - t, 2)
        if p < 0:
            continue
        w = {"size": a, "depth": d, "type": t, "position": p}
        k = cohen_kappa_score(y, to_labels(scores(x, w)), weights="linear", labels=[0, 1, 2])
        if k > best + 1e-9:
            best, best_w = k, w
    return {k: float(v) for k, v in best_w.items()}


def ablation(x: np.ndarray, y: np.ndarray, w: dict[str, float]) -> list[dict]:
    base = metrics(y, to_labels(scores(x, w)))["kappa_linear"]
    out = [{"variant": "all factors", "kappa_linear": base, "change": 0.0}]
    for f in FACTORS:
        w2 = {k: (0.0 if k == f else v) for k, v in w.items()}
        k = metrics(y, to_labels(scores(x, w2)))["kappa_linear"]
        out.append({"variant": f"without {f}", "kappa_linear": k, "change": k - base})
    return out


def plot_confusion(cm: list[list[int]], title: str, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4, 3.6), dpi=150)
    m = np.array(cm)
    ax.imshow(m, cmap="Blues")
    for i in range(3):
        for j in range(3):
            ax.text(
                j,
                i,
                str(m[i, j]),
                ha="center",
                va="center",
                color="white" if m[i, j] > m.max() / 2 else "#1e293b",
            )
    names = [s.capitalize() for s in LABELS]
    ax.set_xticks(range(3), names)
    ax.set_yticks(range(3), names)
    ax.set_xlabel("Formula")
    ax.set_ylabel("Hand label")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def run(path: Path, out_dir: Path = RESULTS, seed: int = 42) -> dict:
    x, y, _ = load(path)
    full = metrics(y, to_labels(scores(x, PRD_WEIGHTS)))
    strat = y if min(np.bincount(y, minlength=3)) >= 2 else None
    idx_tune, idx_test = train_test_split(
        np.arange(len(y)), test_size=0.5, random_state=seed, stratify=strat
    )
    tuned = grid_search(x[idx_tune], y[idx_tune])
    held_out = {
        "prd_weights": metrics(y[idx_test], to_labels(scores(x[idx_test], PRD_WEIGHTS))),
        "tuned_weights": metrics(y[idx_test], to_labels(scores(x[idx_test], tuned))),
    }
    e3 = {
        "prd_weights": PRD_WEIGHTS,
        "tuned_weights": tuned,
        "all_data_prd": full,
        "held_out_half": held_out,
        "tune_n": int(len(idx_tune)),
        "test_n": int(len(idx_test)),
    }
    e4 = {"weights": PRD_WEIGHTS, "ablation": ablation(x, y, PRD_WEIGHTS)}
    write_json("e3_severity.json", e3, out_dir)
    write_json("e4_ablation.json", e4, out_dir)
    plot_confusion(
        full["confusion_matrix"], "Severity: formula vs hand labels", out_dir / "e3_confusion.png"
    )
    md = (
        markdown_table(
            ["Weights", "Test n", "Accuracy", "Kappa (linear)"],
            [[name, m["n"], m["accuracy"], m["kappa_linear"]] for name, m in held_out.items()],
        )
        + "\n"
        + markdown_table(
            ["Variant", "Kappa (linear)", "Change"],
            [[r["variant"], r["kappa_linear"], r["change"]] for r in e4["ablation"]],
        )
    )
    (out_dir / "e3_e4_severity.md").write_text(md)
    return {"e3": e3, "e4": e4}


def settings_v2(tuned: dict[str, float]) -> dict:
    return {"severity_weights": {KEYS[k]: v for k, v in tuned.items()}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path, default=RESULTS)
    ap.add_argument("--settings-out", type=Path, help="write tuned weights for the Settings screen")
    a = ap.parse_args()
    res = run(a.csv, a.out)
    if a.settings_out:
        a.settings_out.write_text(json.dumps(settings_v2(res["e3"]["tuned_weights"]), indent=2))
    print(json.dumps(res["e3"]["held_out_half"], indent=2))


if __name__ == "__main__":
    main()
