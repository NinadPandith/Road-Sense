# Data and model training

## Datasets

| Dataset | What it gives | Use |
|---------|---------------|-----|
| RDD2022 [@arya2022rdd] | 47,420 road images from six countries, 4 damage classes | Base training; India subset reported separately |
| RoadSense local set | [[RESULT: n]] labelled frames from the [[RESULT: km]] km pilot route in [[CITY]] | Fine-tuning and a local test set |
| Severity set | 200 potholes hand-labelled Minor / Moderate / Dangerous | Validating and tuning the severity score |
| OpenStreetMap | Road types, schools, hospitals, ward boundaries | Priority score and map filters |

## Preparing RDD2022

RDD2022 annotations are in Pascal VOC XML. A conversion script keeps only the four classes used
here (D00, D10, D20, D40), drops other labels (such as D43, D44, D50 and "Repair"), clips boxes to
the image and writes YOLO label files. Only RDD2022's training folders have labels, so they are
split 70/15/15 into training, validation and test sets with a fixed seed, per country. Class
counts after conversion:

| Split | Images | Crack along | Crack across | Alligator crack | Pothole |
|-------|--------|-------------|--------------|-----------------|---------|
| Train | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] |
| Validation | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] |
| Test | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] | [[RESULT]] |

## Collecting local data

A phone mounted on a two-wheeler recorded the pilot route twice in daylight and once in the
evening, with a GPS logger app running at the same time. One frame per second was extracted;
frames that were blurry (variance of the Laplacian below a threshold) or near-duplicates of the
previous kept frame (difference hash within 6 bits) were dropped, and every frame was tagged with
its GPS position by interpolating the track at the frame's time.

The model trained on RDD2022 pre-labelled the frames in Roboflow and every box was then checked
and corrected by hand, following RDD2022's class definitions. The labelled frames were split by
**500 m route segment**, not by frame (70/15/15), so near-identical neighbouring frames never
appear in both training and test data.

The 200 severity labels were made by looking at each pothole photo before any severity score was
shown; the scores were exported to a separate file that was opened only after labelling.

## Training

Training ran on Kaggle's free GPU with Ultralytics YOLO11 at 640 px, using pretrained COCO
weights:

1. YOLO11s for 50 epochs on the India subset, as a sanity check.
2. YOLO11s and YOLO11n for 100 epochs on all of RDD2022 (early stopping patience 25).
3. Fine-tuning both on RDD2022 plus the local training frames for 30 epochs (learning rate 0.002),
   so the model adapts to local roads without forgetting RDD2022.
4. For experiment E1 only: YOLO11m and YOLOv8s trained the same way as step 2.

The best weights were exported to ONNX (opset 12, simplified) and uploaded to the Hugging Face Hub
with a model card. Depth Anything V2 Small is used as released, in ONNX form.

[[Add the training curves (results.png) from ml/results/baseline/ as a figure.]]
