"""M6: split the labelled local frames by ROUTE SEGMENT (70/15/15), never by frame, so near-
identical neighbouring frames can't leak from train into test.

Input: a Roboflow "YOLOv8/YOLO11" export (images/ + labels/ in any sub-folders) and the
frames.csv files written by extract_frames.py (file -> segment).

Usage:
    python -m scripts.split_local --roboflow data/roboflow_export --frames data/frames \
        --out data/local
"""

import argparse
import csv
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from scripts.prepare_rdd2022 import NAMES

SPLITS = (("train", 0.70), ("val", 0.15), ("test", 0.15))


def segment_map(frames_dir: Path) -> dict[str, str]:
    """Frame stem -> 'ride:segment' (Roboflow may rename files, so match on the stem prefix)."""
    seg = {}
    for csv_path in frames_dir.rglob("frames.csv"):
        ride = csv_path.parent.name
        with csv_path.open() as f:
            for row in csv.DictReader(f):
                seg[Path(row["file"]).stem] = f"{ride}:{row.get('segment') or 'nogps'}"
    return seg


def find_segment(stem: str, seg: dict[str, str]) -> str | None:
    if stem in seg:
        return seg[stem]
    # Roboflow exports look like "<original>_jpg.rf.<hash>"
    base = stem.split("_jpg.rf.")[0].split(".rf.")[0]
    return seg.get(base)


def assign(segments: list[str], seed: int) -> dict[str, str]:
    segments = sorted(segments)
    random.Random(seed).shuffle(segments)
    n = len(segments)
    cut1 = max(1, round(n * SPLITS[0][1]))
    cut2 = cut1 + max(1, round(n * SPLITS[1][1]))
    out = {}
    for i, s in enumerate(segments):
        out[s] = "train" if i < cut1 else "val" if i < cut2 else "test"
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--roboflow", type=Path, required=True)
    ap.add_argument("--frames", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    seg = segment_map(a.frames)
    images = [p for p in a.roboflow.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    by_segment: dict[str, list[Path]] = defaultdict(list)
    unmatched = 0
    for img in images:
        s = find_segment(img.stem, seg)
        if s is None:
            unmatched += 1
            s = "unmatched"
        by_segment[s].append(img)
    split_of = assign(list(by_segment), a.seed)

    counts: Counter = Counter()
    for s, imgs in by_segment.items():
        split = split_of[s]
        for img in imgs:
            label = next(img.parent.parent.glob(f"labels/{img.stem}.txt"), None)
            (a.out / "images" / split).mkdir(parents=True, exist_ok=True)
            (a.out / "labels" / split).mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, a.out / "images" / split / img.name)
            dst = a.out / "labels" / split / f"{img.stem}.txt"
            if label:
                shutil.copy2(label, dst)
            else:
                dst.write_text("")
            counts[split] += 1
    (a.out / "data.yaml").write_text(
        yaml.safe_dump(
            {
                "path": str(a.out.resolve()),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "names": dict(enumerate(NAMES)),
            },
            sort_keys=False,
        )
    )
    summary = {"images": dict(counts), "segments": len(by_segment), "unmatched": unmatched}
    (a.out / "split.json").write_text(json.dumps({**summary, "split_of": split_of}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
