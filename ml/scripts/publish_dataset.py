"""W2: publish the local dataset on the Hugging Face Hub, blurred.

Every image is blurred again (faces and number plates) with the backend's privacy module and saved
without EXIF before upload, even if the frames were blurred earlier. Labels are copied unchanged.

Usage (from the repo root, with HF_TOKEN set):
    python ml/scripts/publish_dataset.py ml/data/local --repo YOUR-HF-USER/roadsense-local
    python ml/scripts/publish_dataset.py ml/data/local --dry-run   # build ml/data/publish only
"""

import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.privacy import anonymise  # noqa: E402

CLASS_NAMES = ["crack_along", "crack_across", "alligator_crack", "pothole"]


def stats_table(counts: dict[str, Counter], images: Counter) -> str:
    lines = [
        "| Split | Images | " + " | ".join(CLASS_NAMES) + " |",
        "|---|---|" + "---|" * len(CLASS_NAMES),
    ]
    for split in ("train", "val", "test"):
        c = counts.get(split, Counter())
        lines.append(
            f"| {split} | {images[split]} | " + " | ".join(str(c[i]) for i in range(4)) + " |"
        )
    return "\n".join(lines)


def build(src: Path, out: Path) -> tuple[int, int]:
    if out.exists():
        shutil.rmtree(out)
    counts: dict[str, Counter] = {}
    images: Counter = Counter()
    blurred_regions = 0
    for img_path in sorted((src / "images").rglob("*")):
        if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        split = img_path.parent.name
        rgb = np.asarray(Image.open(img_path).convert("RGB"))
        rgb, n = anonymise(rgb)
        blurred_regions += n
        dst = out / "images" / split / f"{img_path.stem}.jpg"
        dst.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgb).save(dst, format="JPEG", quality=92)  # no EXIF written
        label = src / "labels" / split / f"{img_path.stem}.txt"
        ldst = out / "labels" / split / f"{img_path.stem}.txt"
        ldst.parent.mkdir(parents=True, exist_ok=True)
        text = label.read_text() if label.exists() else ""
        ldst.write_text(text)
        counts.setdefault(split, Counter()).update(
            int(line.split()[0]) for line in text.splitlines() if line.strip()
        )
        images[split] += 1
    (out / "data.yaml").write_text(
        "path: .\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n"
        + "".join(f"  {i}: {n}\n" for i, n in enumerate(CLASS_NAMES))
    )
    card = (ROOT / "ml" / "hf" / "dataset_card.md").read_text()
    (out / "README.md").write_text(card.replace("{{STATS}}", stats_table(counts, images)))
    return sum(images.values()), blurred_regions


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path, help="output of scripts/split_local.py")
    ap.add_argument("--repo")
    ap.add_argument("--out", type=Path, default=ROOT / "ml" / "data" / "publish")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n, regions = build(a.src, a.out)
    print(f"{n} images prepared in {a.out} ({regions} face/plate regions blurred)")
    print("Look through a sample of images before publishing.")
    if a.dry_run or not a.repo:
        return
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(a.repo, repo_type="dataset", exist_ok=True)
    api.upload_folder(
        folder_path=str(a.out),
        repo_id=a.repo,
        repo_type="dataset",
        commit_message="RoadSense local dataset",
    )
    print(f"published https://huggingface.co/datasets/{a.repo}")


if __name__ == "__main__":
    main()
