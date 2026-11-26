"""F8: gather ml/results/*.json (+ figures) into frontend/public/results/ for the Results page.

Run after each experiment, commit the output, and the page updates on the next deploy:
    python -m scripts.build_results_json
"""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from scripts.common import ML, RESULTS

OUT = ML.parent / "frontend" / "public" / "results"
FILES = {
    "e1": "e1_models.json",
    "e2": "e2_models.json",
    "e3": "e3_severity.json",
    "e4": "e4_ablation.json",
    "e5": "e5_merge.json",
    "e6": "e6_timing.json",
}
FIGURES = ["e3_confusion.png", "failure_grid.png", "samples_grid.png"]


def build(results: Path = RESULTS, out: Path = OUT) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    data: dict = {"generated_at": datetime.now(UTC).isoformat(), "figures": {}}
    for key, name in FILES.items():
        p = results / name
        data[key] = json.loads(p.read_text()) if p.exists() else None
    for fig in FIGURES:
        p = results / fig
        if p.exists():
            shutil.copy2(p, out / fig)
            data["figures"][fig.removesuffix(".png")] = f"/results/{fig}"
    (out / "results.json").write_text(json.dumps(data, indent=2))
    return data


def main() -> None:
    data = build()
    have = [k for k in FILES if data[k] is not None]
    print(f"results.json written with {', '.join(have) or 'no experiments yet'}")


if __name__ == "__main__":
    main()
