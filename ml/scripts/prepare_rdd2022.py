"""M2: convert RDD2022 (Pascal VOC XML) to YOLO format with the 4 RoadSense classes.

RDD2022 layout:  <root>/<Country>/train/images/*.jpg  and  .../train/annotations/xmls/*.xml
Only the train folders have labels, so we make our own train/val/test split (70/15/15),
grouped by country and shuffled with a fixed seed so runs are reproducible.

Usage:
    python -m scripts.prepare_rdd2022 --src /kaggle/input/rdd2022/RDD2022 --out data/rdd_india \
        --countries India
    python -m scripts.prepare_rdd2022 --src ... --out data/rdd_all   # all countries
"""

import argparse
import json
import os
import random
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import yaml

CLASSES = ["D00", "D10", "D20", "D40"]  # index order == backend/app/services/classes.py
NAMES = ["crack_along", "crack_across", "alligator_crack", "pothole"]
SPLITS = {"train": 0.70, "val": 0.15, "test": 0.15}


def voc_to_yolo(xml_path: Path) -> tuple[list[str], Counter]:
    """Return YOLO label lines (class cx cy w h, normalised) and a count of kept classes."""
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    w = float(size.findtext("width"))  # type: ignore[union-attr, arg-type]
    h = float(size.findtext("height"))  # type: ignore[union-attr, arg-type]
    lines, counts = [], Counter()
    if w <= 0 or h <= 0:
        return lines, counts
    for obj in root.iter("object"):
        name = (obj.findtext("name") or "").strip()
        if name not in CLASSES:
            continue  # drops D43, D44, D50, Repair, Block crack, typos
        bb = obj.find("bndbox")
        x1, y1, x2, y2 = (float(bb.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax"))  # type: ignore[union-attr, arg-type]
        x1, x2 = max(0.0, min(x1, x2)), min(w, max(x1, x2))
        y1, y2 = max(0.0, min(y1, y2)), min(h, max(y1, y2))
        if x2 - x1 < 2 or y2 - y1 < 2:
            continue
        cls = CLASSES.index(name)
        lines.append(
            f"{cls} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} "
            f"{(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}"
        )
        counts[name] += 1
    return lines, counts


def split_names(names: list[str], seed: int) -> dict[str, list[str]]:
    names = sorted(names)
    random.Random(seed).shuffle(names)
    n = len(names)
    a = int(n * SPLITS["train"])
    b = a + int(n * SPLITS["val"])
    return {"train": names[:a], "val": names[a:b], "test": names[b:]}


def _place(src: Path, dst: Path, copy: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    if copy:
        shutil.copy2(src, dst)
    else:
        os.symlink(src.resolve(), dst)


def prepare(src: Path, out: Path, countries: list[str] | None, seed: int, copy: bool) -> dict:
    stats: dict = {"countries": {}, "class_counts": {}, "images": {}}
    total = Counter()
    for cdir in sorted(p for p in src.iterdir() if p.is_dir()):
        if countries and cdir.name not in countries:
            continue
        xml_dir = cdir / "train" / "annotations" / "xmls"
        img_dir = cdir / "train" / "images"
        if not xml_dir.exists():
            continue
        items = {}
        for xml in xml_dir.glob("*.xml"):
            img = img_dir / f"{xml.stem}.jpg"
            if img.exists():
                items[xml.stem] = (xml, img)
        for split, stems in split_names(list(items), seed).items():
            for stem in stems:
                xml, img = items[stem]
                lines, counts = voc_to_yolo(xml)
                total.update(counts)
                name = f"{cdir.name}_{stem}"
                _place(img, out / "images" / split / f"{name}.jpg", copy)
                lp = out / "labels" / split / f"{name}.txt"
                lp.parent.mkdir(parents=True, exist_ok=True)
                lp.write_text("\n".join(lines) + ("\n" if lines else ""))
                stats["images"][split] = stats["images"].get(split, 0) + 1
        stats["countries"][cdir.name] = len(items)

    stats["class_counts"] = {c: total.get(c, 0) for c in CLASSES}
    data_yaml = {
        "path": str(out.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": dict(enumerate(NAMES)),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.yaml").write_text(yaml.safe_dump(data_yaml, sort_keys=False))
    (out / "stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--countries", nargs="*", help="e.g. India Japan; default all")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--copy", action="store_true", help="copy images instead of symlinking")
    a = ap.parse_args()
    stats = prepare(a.src, a.out, a.countries, a.seed, a.copy)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
