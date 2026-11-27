# Viva deck outline (W6)

About 15 slides for a 10–12 minute talk. One idea per slide, big visuals, few words; the speaker
notes are what to say. Keep the live demo between slides 9 and 10, with the demo video ready as a
backup.

| # | Slide | On the slide | Say |
|---|-------|--------------|-----|
| 1 | Title | RoadSense; your name, guide, college; one-line pitch | "RoadSense doesn't just detect potholes; it tells a city which one to fix first, and why." |
| 2 | The problem | 2,161 pothole deaths in 2023 (MoRTH); photo of a real pothole on your route | Complaint-driven repair; duplicates; no measure of danger. |
| 3 | Gap in existing work | Comparison table (detect / severity / merge / rank / deployed) | Research stops at detection; nobody ranks by risk with an explanation. |
| 4 | Objectives | 5 objectives from Chapter 1 | Each maps to an experiment later. |
| 5 | Architecture | Architecture diagram | One pipeline for photos, Drive mode and survey video; ONNX everywhere. |
| 6 | Processing pipeline | The 9 steps, with blur first | Privacy by design: an unblurred photo is never stored. |
| 7 | Severity score | Formula + one annotated photo showing A, D, T, P | Why each factor; depth is relative, never centimetres. |
| 8 | Merging and priority | Priority formula + an example defect's terms | Why the caps; why every term is shown. |
| 9 | Live demo | Phone + laptop | Report → result → dashboard → detail → status change. |
| 10 | Data | RDD2022 + local route map + labelling | Split by route segment to avoid leakage. |
| 11 | E1 + E2 | Model table; before/after local data | Accuracy vs speed; why small on server, nano in the browser. |
| 12 | E3 + E4 | Confusion matrix; ablation bars | Agreement with people; what depth really adds. |
| 13 | E5 + E6 | Merge sweep; timing table | GPS error sets the radius; meets the 5 s target or not. |
| 14 | Failure cases | Failure grid | Honest limits and what would fix them. |
| 15 | Conclusion and future | 3 contributions; future work | Buses as surveyors; monsoon prediction; portal integration. |

Design tips: the app's teal (#0f766e) for headings; severity colours only for severity; every
chart labelled; numbers rounded to 2 decimals; cite sources on the slide.
