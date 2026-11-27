---
license: cc-by-4.0
task_categories:
  - object-detection
tags:
  - road-damage
  - pothole
  - india
  - yolo
pretty_name: RoadSense local road damage set
size_categories:
  - n<1K
---

# RoadSense local road damage set

Road images from a pilot route in [[CITY]], India, labelled with the same four damage classes and
rules as RDD2022. Made for the [RoadSense](https://github.com/NinadPandith/Road-Sense) project to
measure (and reduce) the gap between a public dataset and one city's roads.

## Contents

{{STATS}}

- Format: YOLO (one `.txt` per image: `class cx cy w h`, normalised).
- Classes: `0 crack_along (D00)`, `1 crack_across (D10)`, `2 alligator_crack (D20)`, `3 pothole (D40)`.
- `data.yaml` for Ultralytics.

## How it was made

- A phone mounted on a two-wheeler recorded the route ([[KM]] km, main roads and residential
  lanes) in daylight and one evening ride, with a GPS logger running.
- 1 frame per second was extracted; blurry and near-duplicate frames were removed.
- Frames were pre-labelled by a model trained on RDD2022 and every box was then checked and
  corrected by hand in Roboflow.
- **Split by route segment (500 m), not by frame**, 70/15/15, so near-identical neighbouring
  frames never appear in both training and test.

## Privacy

Faces and number plates were detected and blurred in every image before publishing, and all
EXIF metadata (including GPS) was removed. If you find an identifiable person or plate, open an
issue on the GitHub repository and the image will be removed.

## Limitations

One city, one phone, mostly daylight; the label set inherits RDD2022's definitions and their
ambiguities (for example between alligator cracks and patched areas).

## Licence and citation

CC BY 4.0. Please cite the RoadSense repository and RDD2022 (Arya et al., 2022).
