# LinkedIn post (W7)

Post after the live demo, the video and the repository are public. Attach the 3-minute video
(native upload gets more reach than a link) and put the links in the post. Replace every
[[placeholder]].

---

Potholes were linked to 2,161 deaths in India in 2023. Most cities still fix them in the order
complaints arrive, not in the order of danger.

For my final-year project I built RoadSense, which tells a city which pothole to fix first, and why.

📱 Citizens report a pothole in 3 taps, no sign-up. The AI finds the damage and scores how
dangerous it is from its size, depth, type and position in the wheel path.
🛵 Drive mode turns a phone on the handlebar into a road surveyor: the model runs inside the
browser, on the phone.
🗺️ Duplicate reports merge into one map point, and engineers get a ranked repair list where every
part of the ranking is explained.

What I measured on images the model never saw:
• Pothole detection AP@0.5: [[result]]
• Severity agreement with human judgement: [[kappa]] weighted kappa
• Duplicate merging: [[merge accuracy]] correct when the same route was ridden twice
• Upload to result: [[seconds]] s

It runs entirely on free tiers (Vercel, Azure for Students, Supabase, Kaggle, Hugging Face).

Stack: YOLO11, Depth Anything V2, ONNX Runtime (server and browser), FastAPI, PostGIS, React.

🔗 Live demo: [[link]]
💻 Code: https://github.com/NinadPandith/Road-Sense
📊 Models and a blurred local dataset: [[Hugging Face link]]

Thanks to [[guide name]] for guidance, and to everyone who reported potholes during testing.

#ComputerVision #MachineLearning #SmartCities #RoadSafety #OpenSource #FinalYearProject

---

Note: the content guidelines' no-emoji rule is for the app's interface; a LinkedIn post can use
a few. Remove them if you prefer.
