"""M10 + M7: experiments E1 (which model is best?) and E2 (does local data help?).

Validates each YOLO weights file on a dataset split with Ultralytics, then times its ONNX export
on the CPU with ONNX Runtime (the same runtime the server uses) and records the file size.

Usage (Kaggle, GPU for validation):
    python -m scripts.compare_models --data data/rdd_india/data.yaml --tag e1 \
        --model yolo11n=runs/nano_all/weights/best.pt \
        --model yolo11s=runs/small_all/weights/best.pt \
        --model yolo11m=runs/medium_all/weights/best.pt \
        --model yolov8s=runs/v8s_all/weights/best.pt
    python -m scripts.compare_models --data data/local/data.yaml --tag e2 \
        --model rdd_only=runs/small_all/weights/best.pt \
        --model rdd_plus_local=runs/local_ft/weights/best.pt
"""

import argparse
import time
from pathlib import Path

import numpy as np

from scripts.common import RESULTS, markdown_table, write_json


def onnx_cpu_fps(onnx_path: Path, runs: int = 30, size: int = 640) -> float:
    """Frames per second of one ONNX model on the CPU (batch 1, after 3 warm-up runs)."""
    import onnxruntime as ort

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name
    x = np.random.default_rng(0).random((1, 3, size, size), dtype=np.float32)
    for _ in range(3):
        sess.run(None, {name: x})
    t0 = time.perf_counter()
    for _ in range(runs):
        sess.run(None, {name: x})
    return runs / (time.perf_counter() - t0)


def evaluate(name: str, weights: Path, data: Path, split: str) -> dict:
    from ultralytics import YOLO

    model = YOLO(str(weights))
    m = model.val(data=str(data), split=split, imgsz=640, plots=False, verbose=False)
    onnx = Path(model.export(format="onnx", opset=12, imgsz=640, simplify=True))
    per_class = {
        m.names[i]: {
            "precision": float(m.box.p[k]),
            "recall": float(m.box.r[k]),
            "map50": float(m.box.ap50[k]),
        }
        for k, i in enumerate(m.box.ap_class_index)
    }
    return {
        "model": name,
        "map50": float(m.box.map50),
        "map50_95": float(m.box.map),
        "per_class": per_class,
        "gpu_ms_per_image": float(m.speed.get("inference", 0.0)),
        "cpu_fps_onnx": onnx_cpu_fps(onnx),
        "size_mb": round(onnx.stat().st_size / 1e6, 1),
        "test_images": int(getattr(m, "seen", 0) or 0),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--model", action="append", required=True, help="name=path/to/best.pt")
    ap.add_argument("--split", default="test")
    ap.add_argument("--tag", default="e1", help="e1 (model comparison) or e2 (local data)")
    ap.add_argument("--out", type=Path, default=RESULTS)
    a = ap.parse_args()
    rows = [evaluate(*m.split("=", 1), a.data, a.split) for m in a.model]  # type: ignore[call-arg]
    result = {"dataset": str(a.data), "split": a.split, "models": rows}
    write_json(f"{a.tag}_models.json", result, a.out)
    (a.out / f"{a.tag}_models.md").write_text(
        markdown_table(
            ["Model", "mAP@0.5", "mAP@0.5:0.95", "Pothole AP@0.5", "CPU FPS (ONNX)", "Size (MB)"],
            [
                [
                    r["model"],
                    r["map50"],
                    r["map50_95"],
                    r["per_class"].get("pothole", {}).get("map50", 0.0),
                    round(r["cpu_fps_onnx"], 1),
                    r["size_mb"],
                ]
                for r in rows
            ],
        )
    )
    for r in rows:
        print(r["model"], round(r["map50"], 3), round(r["cpu_fps_onnx"], 1), "FPS")


if __name__ == "__main__":
    main()
