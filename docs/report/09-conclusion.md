# Conclusion and future work

## Conclusion

RoadSense shows that a city can find, measure and rank road damage with ordinary phones and free
infrastructure. Citizens report a pothole in three taps without an account; riders survey a route
by mounting a phone; engineers get one ranked list in which every defect's position is explained
by its severity, its road, nearby schools or hospitals, how many people reported it and how long
it has been open.

[[Summarise the measured results in two or three sentences: detection accuracy, severity
agreement, merge accuracy and speed.]]

The main lessons were that a simple, explainable formula can be validated and tuned like a model;
that a detector trained on a public dataset needs local data to work well on a new city's roads;
and that privacy (blurring before storage) and accessibility (checked automatically on every
change) are much easier to build in from the start than to add later.

## Limitations

- Depth is relative and estimated from one image; it cannot give centimetres, and monocular depth
  models can smooth over shallow potholes.
- The detector was trained on RDD2022 and one city's roads; accuracy will differ elsewhere.
- Phone GPS error of 5–15 m limits how finely nearby potholes can be separated.
- The privacy blur uses classical detectors that can miss small or angled faces.
- The pilot was small: one route and one city ward, with [[RESULT]] real defects.

## Future work

- Cameras on city buses or garbage trucks for automatic daily surveys of the whole city.
- Predicting where potholes will form before the monsoon, from repair history and rainfall.
- Integration with municipal complaint portals and repair work orders.
- Exact depth with stereo cameras or phones with depth sensors, and a learned severity model once
  enough labelled severity data exists.
- A repair cost estimate per defect, Hindi and other Indian languages (the interface text is
  already in one translatable file), and ward-level access for engineers.
