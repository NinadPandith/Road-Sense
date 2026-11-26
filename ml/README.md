# RoadSense ML

Training, export and evaluation for the RoadSense detector. Training runs on Kaggle's free GPU;
everything else runs on a laptop CPU.

| Task | What | How |
|------|------|-----|
| M1 | Record the pilot route (2 daylight + 1 evening ride) with a GPX logger | Phone on the handlebar/dashboard |
| M2 | RDD2022 → YOLO format, 4 classes | `scripts/prepare_rdd2022.py` (run inside the notebook) |
| M3 | Train baseline YOLO small | `notebooks/01_train_detector.ipynb` on Kaggle |
| M4 | Export small + nano to ONNX, upload to Hugging Face | `scripts/export_and_upload.py`; check with `scripts/predict.py` |
| M5 | 1 frame/s from ride videos, drop blurry + duplicate frames, tag with GPS | `scripts/extract_frames.py` |

```bash
cd ml && uv sync && uv run pytest
```

```bash
uv run python -m scripts.extract_frames ride1.mp4 --gpx ride1.gpx --out data/frames/ride1 --start 2026-11-30T07:42:10+05:30
```

```bash
uv run python scripts/predict.py photo.jpg --model ../backend/models/yolo-small.onnx --save out.jpg
```

Class order everywhere: `0 crack_along (D00), 1 crack_across (D10), 2 alligator_crack (D20), 3 pothole (D40)`,
matching `backend/app/services/classes.py`.

`data/` (datasets, frames) and model files are git-ignored; models live on the Hugging Face Hub and
metrics/plots for the report go in `results/`.
