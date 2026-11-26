"""Shared helpers for experiment scripts: where results go and how tables are written."""

import json
from pathlib import Path

ML = Path(__file__).resolve().parents[1]
RESULTS = ML / "results"


def write_json(name: str, data: dict, out_dir: Path = RESULTS) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / name
    p.write_text(json.dumps(data, indent=2, default=float))
    return p


def markdown_table(headers: list[str], rows: list[list]) -> str:
    def cell(v):
        return f"{v:.3f}" if isinstance(v, float) else str(v)

    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"
