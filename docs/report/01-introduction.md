# Introduction

## Background

Roads in Indian cities deteriorate quickly, especially during the monsoon, and potholes are the
most visible and most dangerous form of damage. The Ministry of Road Transport and Highways
reported 2,161 deaths linked to potholes in 2023 [@morth2023]; government figures tabled in
Parliament put the total for 2020–2024 at more than 9,000 [[verify against the parliamentary
answer before submission]]. Two-wheeler riders are the most exposed, because a pothole that a car
absorbs can throw a rider.

Municipal road departments have limited repair budgets. Defects reach them through scattered
channels: complaint portals, phone calls and social media posts. The same pothole is reported
many times, often without an exact location, and the order of repair follows the order and
volume of complaints rather than the danger the damage poses.

Smartphones carry a camera, GPS and enough computing power to run a small neural network, and
public datasets of labelled road damage now exist [@arya2022rdd]. This makes it possible to
collect road damage data at very low cost, from citizens and from anyone riding a regular route.

## Problem statement

Design a low-cost system that detects road damage from ordinary phone video and citizen photos,
estimates the severity of each defect, removes duplicate reports, and ranks repairs by risk to
road users.

## Objectives

1. Detect four damage types (pothole, alligator crack, transverse and longitudinal cracks) in
   photos and video.
2. Score every defect Minor, Moderate or Dangerous, and show that the score is close to human
   judgement.
3. Merge duplicate detections and reports of the same defect into one map point.
4. Rank all defects into a repair list that an engineer can filter and understand.
5. Deliver a public, deployed web application and an open-source repository.

## Scope

In scope: a citizen reporting app, live detection while riding (Drive mode), survey video
processing, a municipal dashboard, a pilot route of 10–15 km in [[CITY]], and the experiments
needed to evaluate each part.

Out of scope for this version: integration with a government complaint portal, exact pothole
depth in centimetres (relative depth is used), native Android or iOS apps, and user accounts for
citizens.

## Contributions

- A **severity score** that combines size, relative monocular depth, damage type and position in
  the wheel path, validated against hand labels, with tuned weights and an ablation study.
- An **explainable repair priority** that adds road importance, report count, age and nearness to
  schools and hospitals, with every term shown to the engineer.
- **Duplicate merging** of reports from citizens, riders and survey videos into single defects,
  evaluated by riding the same route twice.
- **Edge detection in the browser**: a YOLO nano model running on the phone with ONNX Runtime Web.
- A **local labelled dataset** of [[RESULT: n]] frames from Indian roads, published with faces and
  number plates blurred.
- A complete, deployed system that runs at zero running cost.

## Organisation of the report

Chapter 2 reviews related work. Chapter 3 lists the requirements. Chapter 4 describes the system
design and the algorithms, Chapter 5 the implementation, and Chapter 6 the data and model
training. Chapter 7 covers testing, Chapter 8 presents the experiments and results, and
Chapter 9 concludes with limitations and future work.
