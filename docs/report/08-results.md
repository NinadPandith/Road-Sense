# Results and discussion

All numbers are measured on data that was never used for training or tuning. [[Replace every
RESULT placeholder from ml/results/; run `grep -rn "\[\[" docs/report` to find them.]]

## E1: Which model is best?

| Model | mAP@0.5 | mAP@0.5:0.95 | Pothole AP@0.5 | CPU FPS (ONNX) | Size (MB) |
|-------|---------|--------------|----------------|----------------|-----------|
| YOLO11n | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] |
| YOLO11s | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] |
| YOLO11m | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] |
| YOLOv8s | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] |

Test set: RDD2022 India, [[RESULT]] images. [[Discuss the accuracy–speed trade-off and why the
small model was chosen for the server and the nano model for the browser. Per-class results show
which classes are hardest; cracks are usually weaker than potholes.]]

## E2: Does local data help?

| Training data | mAP@0.5 (local test) | Pothole AP@0.5 |
|---------------|----------------------|----------------|
| RDD2022 only | [[RESULT]] | [[RESULT]] |
| RDD2022 + local | [[RESULT]] | [[RESULT]] |

Local test set: [[RESULT]] images from route segments not used for training. [[Target: +10 points
or more. Discuss the domain gap between RDD2022 and the pilot route.]]

## E3: Does the severity score work?

| Weights | Test potholes | Accuracy | Weighted kappa (linear) |
|---------|---------------|----------|-------------------------|
| Original (0.35, 0.35, 0.20, 0.10) | [[RESULT]] | [[RESULT]] | [[RESULT]] |
| Tuned on the other half | [[RESULT]] | [[RESULT]] | [[RESULT]] |

Tuned weights: A = [[RESULT]], D = [[RESULT]], T = [[RESULT]], P = [[RESULT]] (grid search in
steps of 0.05, maximising weighted kappa on the tuning half).

![Confusion matrix of the formula against hand labels.](../../ml/results/e3_confusion.png){width=50%}

[[Target: accuracy ≥ 75%, kappa ≥ 0.6. Discuss which mistakes happen (usually Moderate vs
Dangerous) and whether the tuned weights were adopted as settings version 2.]]

## E4: Does depth matter?

| Variant | Weighted kappa | Change |
|---------|----------------|--------|
| All factors | [[RESULT]] | – |
| Without size | [[RESULT]] | [[RESULT]] |
| Without depth | [[RESULT]] | [[RESULT]] |
| Without type | [[RESULT]] | [[RESULT]] |
| Without position | [[RESULT]] | [[RESULT]] |

[[Discuss honestly. If removing depth changes little, say so: monocular depth models are known
to smooth over pothole depressions [@aburaddaha2026], and size + type may carry most of the
signal. That is a useful finding, not a failure.]]

## E5: Does merging work?

The pilot route was ridden twice, giving [[RESULT]] reports of [[RESULT]] real potholes
(identified by hand from the photos).

| Merge radius | Map points | Merge accuracy | Duplicates left | Wrongly merged |
|--------------|------------|----------------|-----------------|----------------|
| 2 m | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] |
| 5 m | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] |
| 10 m | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] |

[[Target: ≥ 90% at 5 m. Small radii leave duplicates because phone GPS is accurate to 5–15 m;
large radii merge neighbouring potholes. Discuss the chosen radius.]]

## E6: Is it fast enough?

| Where | Photo result (median) | Detector FPS | Video FPS |
|-------|-----------------------|--------------|-----------|
| Laptop CPU | [[RESULT]] s | [[RESULT]] | [[RESULT]] |
| Azure (1 vCPU) | [[RESULT]] s | [[RESULT]] | [[RESULT]] |
| Phone 1 browser ([[MODEL]]) | – | [[RESULT]] (Drive mode) | – |
| Phone 2 browser ([[MODEL]]) | – | [[RESULT]] (Drive mode) | – |

[[Targets: photo result < 5 s, ≥ 15 FPS on a laptop GPU, ≥ 5 FPS in a mid-range phone browser.
Note the cold-start time after the server scales to zero.]]

## Failure analysis

![Examples where the detector fails: speed breakers, wet patches, shadows and water-filled potholes.](../../ml/results/failure_grid.png){width=95%}

[[Describe 10–15 examples: false positives (speed breakers, wet patches, patched asphalt,
manhole covers, shadows), misses (water-filled potholes, potholes in deep shadow, damage far from
the camera), and severity mistakes. Suggest what would fix each.]]

## Comparison with the targets

| Metric | Target | Achieved |
|--------|--------|----------|
| Pothole mAP@0.5 | ≥ 0.60 | [[RESULT]] |
| Overall mAP@0.5 | ≥ 0.50 | [[RESULT]] |
| Gain from local data | ≥ +10 points | [[RESULT]] |
| Severity agreement | ≥ 75%, kappa ≥ 0.6 | [[RESULT]] |
| Duplicate merge accuracy | ≥ 90% | [[RESULT]] |
| Photo result | < 5 s | [[RESULT]] |
| Live detection on a phone | ≥ 5 FPS | [[RESULT]] |
