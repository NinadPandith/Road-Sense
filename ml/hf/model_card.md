---
license: agpl-3.0
library_name: ultralytics
pipeline_tag: object-detection
tags:
  - road-damage
  - pothole-detection
  - yolo11
  - onnx
datasets:
  - YOUR-HF-USER/roadsense-local
---

# RoadSense road damage detectors

ONNX models used by [RoadSense](https://github.com/NinadPandith/Road-Sense), a system that detects
road damage in phone photos and video, scores its severity and ranks repairs.

| File | What | Used by |
|------|------|---------|
| `yolo-small.onnx` | Ultralytics YOLO11s, 640×640 input | Server (FastAPI + ONNX Runtime, CPU) |
| `yolo-nano.onnx` | Ultralytics YOLO11n, 640×640 input | Phone browser (ONNX Runtime Web), Drive mode |
| `depth-anything-v2-small.onnx` | Depth Anything V2 Small (Apache-2.0), re-hosted unchanged | Relative depth for the severity score |
| `model_info.json` | Version, export date, class order, file sizes | |

## Classes

Index order matches RDD2022: `0 crack_along (D00)`, `1 crack_across (D10)`,
`2 alligator_crack (D20)`, `3 pothole (D40)`.

## Training

- Base: RDD2022 (Arya et al., 2022; 47,420 images from six countries), 4 classes, 70/15/15 split
  of the labelled training images, seed 42.
- Fine-tuning (version `v2-local`): RDD2022 + [[RESULT: number]] frames from the RoadSense pilot
  route, split by route segment so near-identical frames never cross splits.
- Kaggle GPU, 640 px, YOLO11 defaults otherwise. Notebooks: `ml/notebooks/` in the repository.

## Evaluation

Held-out test sets that were never used for tuning.

| Model | Test set | mAP@0.5 | Pothole AP@0.5 | CPU FPS (ONNX) | Size |
|-------|----------|---------|----------------|----------------|------|
| yolo-small | RDD2022 India test ([[RESULT: n]] images) | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] MB |
| yolo-nano | RDD2022 India test | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] MB |
| yolo-small v2-local | RoadSense local test ([[RESULT: n]] images) | [[RESULT]] | [[RESULT]] | – | – |

## Limitations

- Trained on RDD2022 and one Indian city's roads; expect lower accuracy on other roads,
  cameras and weather.
- Common false positives: speed breakers, wet patches, shadows, manhole covers.
- Not a safety system. Detections are suggestions for a person to review.

## Licence

AGPL-3.0 (Ultralytics YOLO). Depth Anything V2 Small is Apache-2.0.

## Citation

```bibtex
@misc{roadsense2027,
  author = {Ninad Pandith M N},
  title  = {RoadSense: Smart Pothole and Road Damage Detection with Severity Mapping},
  year   = {2027},
  url    = {https://github.com/NinadPandith/Road-Sense}
}
```
