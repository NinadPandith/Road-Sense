# Literature survey

## Road damage detection with deep learning

Maeda et al. [@maeda2018] built one of the first large smartphone road damage datasets: 9,053
images from a smartphone mounted in a car in Japan, with 15,435 labelled instances of eight damage
types, and showed that a convolutional object detector could run on the phone itself. Their
labelling scheme (D00 longitudinal crack, D10 transverse crack, D20 alligator crack, D40 pothole)
became the standard for later datasets.

RDD2022 [@arya2022rdd], released for the Crowdsensing-based Road Damage Detection Challenge 2022,
extends this to 47,420 images from six countries (Japan, India, the Czech Republic, Norway, the
United States and China) with more than 55,000 instances of the four main damage types. The best
challenge entries reached an F1 score of 76.9% across all countries. RDD2022 includes an Indian
subset, which matters here because Indian roads, lighting and traffic differ markedly from the
other countries.

Single-stage detectors of the YOLO family [@redmon2016yolo] dominate this task because they are
fast enough for video and small enough for phones. This project uses Ultralytics YOLO11
[@jocher2024yolo11], comparing its nano, small and medium sizes and an older YOLOv8 model.

## From detection to severity

Detection alone tells a city *where* damage is, not *how bad* it is. Several works add a measure
of severity:

- Iqbal et al. [@iqbal2022v2] add a risk estimation module on top of a road damage detector that
  converts detections into real-world measurements using image processing and monocular depth
  estimation, to help prioritise repairs.
- Baroudi et al. [@baroudi2025] combine pothole segmentation with a depth map to extract depth
  information for each pothole, and note the lack of an open dataset or model for pothole depth.
- Aburaddaha et al. [@aburaddaha2026] assess already-detected potholes with geometric features
  and a vision-language model, and report that general-purpose monocular depth models tend to
  smooth over pothole depressions and treat them as flat road.

Monocular depth estimation has improved rapidly. MiDaS [@ranftl2022midas] showed that training on
mixed datasets gives robust *relative* depth from a single image, and Depth Anything V2
[@yang2024dav2] produces finer and more robust predictions, with a Small model (about 25M
parameters, Apache-2.0) suitable for CPU inference. Because absolute depth from one phone photo is
unreliable, this project uses only *relative* depth: how much further the inside of a box is than
the road around it. The finding of Aburaddaha et al. motivates the ablation experiment (E4), which
measures how much depth actually adds.

## Prioritisation and crowdsourcing

Municipal and civic apps let citizens report potholes, but they treat each report as a complaint
to be closed, without measuring severity, merging duplicates objectively or ranking by risk.
Spatial clustering methods such as DBSCAN [@ester1996dbscan] group nearby points without fixing
the number of clusters in advance, which suits duplicate reports of the same pothole.

## Evaluation methods

Object detectors are compared with average precision at an IoU of 0.5 (mAP@0.5) and averaged over
IoU 0.5–0.95, following PASCAL VOC and COCO practice [@everingham2010voc]. Agreement between an
ordinal severity label and human judgement is better measured with weighted Cohen's kappa
[@cohen1968kappa] than with accuracy alone, because it corrects for chance agreement and penalises
"Dangerous called Minor" more than "Dangerous called Moderate".

## Research gap

| Work | Detects | Severity | Merges duplicates | Ranks repairs | Explains rank | Deployed app |
|------|---------|----------|-------------------|---------------|---------------|--------------|
| Maeda et al. 2018 | Yes | No | No | No | No | Phone app |
| RDD2022 challenge entries | Yes | No | No | No | No | No |
| Iqbal et al. 2022 | Yes | Risk score | No | Partly | No | Not public |
| Baroudi et al. 2025 | Yes | Depth | No | No | No | No |
| Aburaddaha et al. 2026 | Given | Risk class | No | No | Text warning | No |
| **RoadSense** | Yes | Yes, validated | Yes, evaluated | Yes | Yes, every term | Yes, public |

No reviewed work combines detection, a validated severity score, duplicate merging and an
explainable repair ranking in one system that a city could use today. RoadSense addresses that
gap.
