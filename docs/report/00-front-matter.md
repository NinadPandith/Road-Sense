---
title: "RoadSense: Smart Pothole and Road Damage Detection with Severity Mapping"
subtitle: "Project report submitted in partial fulfilment of the requirements for the degree of Bachelor of Technology in [[BRANCH]]"
author: "Ninad Pandith M N ([[USN / ROLL NUMBER]])"
date: "[[MONTH YEAR]]"
---

**Under the guidance of** [[GUIDE NAME]], [[DESIGNATION]], Department of [[DEPARTMENT]],
[[COLLEGE NAME]], [[UNIVERSITY]].

# Certificate {.unnumbered}

[[Use the certificate page in your department's format.]]

# Declaration {.unnumbered}

I declare that this project report titled *RoadSense: Smart Pothole and Road Damage Detection
with Severity Mapping* is a record of work carried out by me under the guidance of
[[GUIDE NAME]], and that it has not been submitted elsewhere for any degree or diploma.
The software was built with the help of AI coding tools; the design decisions, data collection,
labelling, experiments and the analysis in this report are my own.

[[Signature, place, date]]

# Acknowledgement {.unnumbered}

[[Thank your guide, the head of department, any ward engineer who reviewed the dashboard, and
friends who reported potholes during testing.]]

# Abstract {.unnumbered}

Cities in India repair potholes in the order complaints arrive, not in the order of danger, while
potholes were linked to 2,161 road deaths in 2023 alone. Research on road damage mostly stops at
detecting damage in images. This project presents RoadSense, a low-cost system that detects road
damage in ordinary phone photos and video, estimates the severity of each defect, merges
duplicate reports of the same spot, and ranks repairs by their risk to road users.

A YOLO11 detector trained on the public RDD2022 dataset and fine-tuned on [[RESULT: n]] frames
from a local pilot route finds four damage types. Each detection receives a severity score from
its size, its relative depth estimated by Depth Anything V2, its damage type and its position in
the wheel path. Reports within 5 m are merged with PostGIS, and each defect's repair priority
combines severity, road importance from OpenStreetMap, the number of reports, the time open, and
nearness to schools and hospitals, with every term shown to the engineer. The system is a
deployed progressive web app with a citizen view, a live in-browser Drive mode and a municipal
dashboard, running entirely on free tiers.

On the RDD2022 India test images the detector reaches a pothole AP@0.5 of [[RESULT]], and local
data improves mAP@0.5 on the local test set by [[RESULT]] points. The severity score agrees with
200 hand labels with an accuracy of [[RESULT]] and a weighted kappa of [[RESULT]] on a held-out
half, and merging places [[RESULT]] of real potholes as a single map point when a route is ridden
twice. A photo report returns its result in [[RESULT]] seconds.

**Keywords:** road damage detection, pothole severity, monocular depth estimation, YOLO,
repair prioritisation, PostGIS, progressive web app.

# Abbreviations {.unnumbered}

| Term | Meaning |
|------|---------|
| AP / mAP | Average precision / mean average precision |
| API | Application programming interface |
| CPU / GPU | Central / graphics processing unit |
| DBSCAN | Density-based spatial clustering of applications with noise |
| EXIF | Exchangeable image file format (photo metadata) |
| GPS / GPX | Global positioning system / GPS exchange format |
| IoU | Intersection over union |
| JWT | JSON web token |
| MoRTH | Ministry of Road Transport and Highways |
| ONNX | Open neural network exchange |
| OSM | OpenStreetMap |
| PWA | Progressive web app |
| RDD2022 | Road Damage Dataset 2022 |
| RLS | Row level security |
| WCAG | Web content accessibility guidelines |
| YOLO | You only look once (object detector family) |
