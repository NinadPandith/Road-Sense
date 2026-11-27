"""M4: export trained YOLO weights to ONNX and upload them (plus the depth model) to the
Hugging Face Hub repo the backend downloads from.

Usage (on Kaggle, after training):
    python -m scripts.export_and_upload --small runs/detect/small/weights/best.pt \
        --nano runs/detect/nano/weights/best.pt --repo <hf-user>/roadsense-models --version v1
Needs HF_TOKEN in the environment (a Kaggle secret).
"""

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

DEPTH_SOURCE = ("onnx-community/depth-anything-v2-small", "onnx/model.onnx")


def export(weights: Path, imgsz: int, out: Path) -> Path:
    from ultralytics import YOLO

    path = Path(YOLO(str(weights)).export(format="onnx", opset=12, imgsz=imgsz, simplify=True))
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--small", type=Path, required=True)
    ap.add_argument("--nano", type=Path, required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--version", required=True, help="e.g. v1, v2-local")
    ap.add_argument("--out", type=Path, default=Path("export"))
    a = ap.parse_args()

    files = {
        "yolo-small.onnx": export(a.small, 640, a.out / "yolo-small.onnx"),
        "yolo-nano.onnx": export(a.nano, 640, a.out / "yolo-nano.onnx"),
    }
    depth = hf_hub_download(*DEPTH_SOURCE)
    files["depth-anything-v2-small.onnx"] = Path(
        shutil.copy2(depth, a.out / "depth-anything-v2-small.onnx")
    )
    meta = {
        "version": a.version,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "classes": ["crack_along", "crack_across", "alligator_crack", "pothole"],
        "sizes_mb": {k: round(v.stat().st_size / 1e6, 1) for k, v in files.items()},
    }
    (a.out / "model_info.json").write_text(json.dumps(meta, indent=2))
    card = Path(__file__).resolve().parents[1] / "hf" / "model_card.md"
    if card.exists():  # the repo's README on the Hub is the model card
        shutil.copy2(card, a.out / "README.md")
    print(json.dumps(meta, indent=2))

    api = HfApi()
    api.create_repo(a.repo, repo_type="model", exist_ok=True)
    api.upload_folder(folder_path=str(a.out), repo_id=a.repo, commit_message=f"models {a.version}")
    print(f"uploaded to https://huggingface.co/{a.repo}; set MODEL_VERSION={a.version}")


if __name__ == "__main__":
    main()
