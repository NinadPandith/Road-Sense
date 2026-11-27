# Demo video script (W5): 3 minutes

Story: **problem → citizen report → Drive mode → dashboard → results**. Record the phone screen
with the phone's built-in screen recorder and the laptop with OBS (free). Speak slowly; 3 minutes
is about 400 words. Upload to YouTube as unlisted and link it from the README.

| Time | Shot | Voice-over |
|------|------|------------|
| 0:00–0:20 | Phone footage riding past real potholes on your route; title card "RoadSense" | "Potholes were linked to more than two thousand deaths in India in 2023. Cities fix them in the order complaints arrive, not in the order of danger. RoadSense changes that." |
| 0:20–0:55 | Phone screen: Home → Report a pothole → take photo → pin → Submit → result card | "A citizen opens the link, takes one photo and submits. No sign-up. In a few seconds the AI says what it found, how sure it is, and how dangerous it is: here, Dangerous, because it's large, looks deep and is in the wheel path. Faces and number plates are blurred before anything is stored." |
| 0:55–1:10 | Result card shows "Added to an existing report (4 reports)"; tracking code; Track screen timeline | "If someone already reported this pothole, the report joins it instead of creating a duplicate. The citizen gets a tracking code and can see when an engineer acts on it." |
| 1:10–1:45 | Phone on the handlebar mount; Drive mode live view with boxes and the counter; ride summary with route map | "Drive mode turns any phone into a road surveyor. The AI runs inside the browser, on the phone, five times a second. It saves one photo per pothole and uploads in the background, even after a dead zone." |
| 1:45–2:25 | Laptop: dashboard map (clusters → heatmap) → Fix these first → repair list → defect detail: severity bars and priority terms → Assign repair | "Engineers see one ranked list. Each defect's rank is explained: severity, road importance from OpenStreetMap, a school nearby, how many people reported it, and how long it's been open. Every number in the formula is on the screen, and the engineer stays in control." |
| 2:25–2:45 | Surveys screen: upload a ride video → progress → "38 potholes found → 21 defects" → View on map | "A whole ride's video can be uploaded too. Frames are matched to GPS by time and duplicates are merged automatically." |
| 2:45–3:00 | Results page: E1 table, severity agreement, merge accuracy; end card with live link and GitHub | "We measured everything on images the model never saw: [[pothole AP]], severity agreement [[kappa]] with people, and [[merge accuracy]] of potholes merged correctly. RoadSense doesn't just detect potholes; it tells a city which one to fix first, and why." |

## Before recording

- Seed the live app with 30+ real defects from your own rides so the map isn't empty.
- Open the app 10 minutes early so the backend has loaded its models.
- Phone: Do Not Disturb on, brightness up, notifications hidden.
- Never film while riding and touching the phone. Film Drive mode with the phone mounted, or
  record the screen afterwards.
- Blur any faces or number plates in the B-roll footage too.

## After recording

- Add captions (YouTube auto-captions, then correct them).
- Export a 10–15 s GIF of the citizen report for the README (`docs/images/demo.gif`).
