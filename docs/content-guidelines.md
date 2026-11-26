# RoadSense: Content Guidelines

Nov 27, 2026 · @Ninad Pandith M N

How every word in the RoadSense app should read: buttons, labels, messages and AI results. Based on Doc and the screens in Doc. English in v1, written so Hindi can be added later.

## Voice and tone

RoadSense sounds like a helpful, calm civic volunteer: clear, short and honest, never bureaucratic and never cute.

**Who we write for**

- **Citizens:** often on a two-wheeler, on a phone, in a hurry, sometimes in bright sun. English may be their second or third language.

- **Municipal engineers:** busy professionals who need facts, numbers and reasons, not friendliness.

- **Examiners and recruiters:** judge the product in minutes; clear words make the project look finished.

**Principles**

1.  **Clear first.** Use everyday words a Class 8 student understands. *"Take a photo of the pothole"*, not *"Capture road surface imagery"*.

2.  **Short.** One idea per sentence. Buttons are 1–3 words; messages are 1–2 sentences.

3.  **Honest.** Say what the AI found and how sure it is. Never promise a repair date or that the city will act.

4.  **Respectful.** Thank people for reporting; never blame them for a bad photo or a failed upload.

5.  **Calm about danger.** Say *Dangerous* when it is, without alarm words, capitals or exclamation marks.

6.  **Action-led.** Every message tells the user what to do next.

**Tone by situation**

| Situation         | Tone               | Example                                                            |
|-------------------|--------------------|--------------------------------------------------------------------|
| Onboarding, home  | Warm, inviting     | "Spotted a pothole? Report it in 30 seconds."                      |
| Report submitted  | Grateful, specific | "Thanks. Your report is on the map."                               |
| Dangerous result  | Calm, factual      | "Severity: Dangerous. This pothole is deep and in the wheel path." |
| Errors            | Helpful, no blame  | "We couldn't get your location. Drag the pin to the pothole."      |
| Drive mode safety | Firm, direct       | "Mount your phone before you ride. Don't touch it while moving."   |
| Admin dashboard   | Neutral, precise   | "24 open defects · 6 Dangerous"                                    |
| Results page      | Factual, modest    | "Pothole detection mAP@0.5: 0.63 on 412 test images."              |

## Writing rules

One consistent style everywhere makes the app feel finished; when in doubt, pick the shorter option.

| Topic          | Rule                                                                                   | Example                                                                   |
|----------------|----------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| Spelling       | Indian/British English                                                                 | colour, centre, analyse, kilometre                                        |
| Capitalisation | Sentence case for everything: titles, buttons, labels, menu items                      | "Report a pothole", not "Report A Pothole"                                |
| Buttons        | Verb first, 1–3 words, says what happens                                               | Submit report · Retake photo · Mark fixed                                 |
| Person         | Talk to the user as *you*; the app is *we*                                             | "We couldn't find road damage in your photo."                             |
| Voice          | Active voice                                                                           | "An engineer verified this pothole", not "This pothole has been verified" |
| Punctuation    | No exclamation marks except "Thanks!" once on success; no ALL CAPS                     |                                                                           |
| Numbers        | Digits always (3 reports, not three); comma every 3 digits; no lakh or crore in the UI | 3 reports · 1,240 defects                                                 |
| Distances      | m under 1 km, km with one decimal above                                                | 5 m · 4.2 km                                                              |
| Time ago       | Relative under 7 days, then a date                                                     | 2 h ago · Yesterday · 12 Nov 2026                                         |
| Dates          | Day Month Year, short month, no ordinal                                                | 27 Nov 2026                                                               |
| Times          | 12-hour with am/pm                                                                     | 6:30 pm                                                                   |
| Scores         | Severity and priority shown as labels first; numbers only where useful, to 2 decimals  | Dangerous (0.82)                                                          |
| Percentages    | Whole numbers in the UI                                                                | 87% sure                                                                  |
| Codes          | Tracking codes in caps with a hyphen, monospace font                                   | RS-7K2Q                                                                   |
| Abbreviations  | Avoid, except GPS, AI, PDF, CSV                                                        | "location" in citizen screens, "GPS" only where users expect it           |
| Emoji          | None in the UI                                                                         |                                                                           |

## Terminology

Use the same word for the same thing on every screen; citizens see plain words, engineers also see the technical ones.

| Use                                                           | Meaning                                             | Avoid                                        | Notes                                                                        |
|---------------------------------------------------------------|-----------------------------------------------------|----------------------------------------------|------------------------------------------------------------------------------|
| report                                                        | One photo or Drive-mode capture sent by one person  | complaint, ticket, submission                | Citizens *report*; they don't *file complaints*                              |
| pothole                                                       | Citizen-facing word for any road damage             | defect (on citizen screens)                  | Citizens say pothole even for cracks; keep it                                |
| defect                                                        | One damaged spot on the road, after merging reports | issue, incident, problem                     | Admin screens only                                                           |
| road damage                                                   | Umbrella term in explanations                       | anomaly, distress (except in the paper)      | "We couldn't find road damage"                                               |
| Pothole, Alligator crack, Crack across road, Crack along road | The 4 damage types                                  | D40, D20, D10, D00, transverse, longitudinal | Codes and technical names appear only in the Results page and admin tooltips |
| severity                                                      | How dangerous one defect is                         | risk level, rating                           | Values: Minor, Moderate, Dangerous                                           |
| priority                                                      | Order in which to fix defects                       | urgency, score                               | Shown as rank (#1, \#2) to engineers only                                    |
| tracking code                                                 | The RS-XXXX code given to a citizen                 | ticket ID, reference number                  |                                                                              |
| merged                                                        | This report joined an existing defect               | duplicate, rejected                          | Citizens see "Added to an existing report"                                   |
| location                                                      | Where the pothole is                                | coordinates, lat/long, geotag                | Admin detail may show coordinates                                            |
| Drive mode                                                    | Live detection while riding                         | scan mode, auto mode, survey mode            | Always capitalised D as a feature name                                       |
| survey                                                        | An uploaded video + GPS track                       | upload, batch                                | Admin only                                                                   |
| ward                                                          | City area used for filters                          | zone, sector, division                       | Use the city's own word if it differs                                        |
| engineer                                                      | Municipality user                                   | admin, officer, authority                    | Code may say admin; the UI says engineer                                     |
| AI                                                            | The detection and scoring system                    | model, algorithm, neural network             | Model names only on the Results page                                         |

## Severity, status and priority wording

Every label pairs a word with a colour and an icon, so it is never understood by colour alone.

**Severity**

| Label     | Score          | Colour | Icon           | One-line explanation (citizen)                                 | Explanation (engineer)                                  |
|-----------|----------------|--------|----------------|----------------------------------------------------------------|---------------------------------------------------------|
| Minor     | below 0.40     | Green  | Circle         | "Small damage. Worth fixing, not urgent."                      | Small area, shallow, or off the wheel path              |
| Moderate  | 0.40–0.69      | Amber  | Triangle       | "Noticeable damage. Can hurt tyres and slow traffic."          | Medium size or depth, or a crack type that worsens fast |
| Dangerous | 0.70 and above | Red    | Diamond with ! | "Deep or large damage in the wheel path. Ride carefully here." | Large, deep pothole in the lane centre                  |

The breakdown bars use these labels: **Size**, **Depth**, **Damage type**, **Position on road**. Each bar shows Low / Medium / High, not raw numbers, for citizens; engineers also see the number.

**Status**

| Status       | Citizen wording on the tracking page                     | Engineer action label |
|--------------|----------------------------------------------------------|-----------------------|
| Reported     | "Reported on 27 Nov. Waiting for an engineer to check."  | —                     |
| Needs review | "Our AI wasn't sure. An engineer will check your photo." | Accept / Not a defect |
| Verified     | "An engineer confirmed this pothole."                    | Verify                |
| Assigned     | "A repair has been planned."                             | Assign repair         |
| Fixed        | "Marked fixed on 3 Dec. Thanks for reporting."           | Mark fixed            |
| Rejected     | "An engineer found no road damage at this spot."         | Not a defect          |

Never say *"will be fixed"* or give a date; say what has happened, not what will.

**Priority (engineers only)**

- Show as rank: **\#1**, **\#2**. The score appears in the detail view only.

- Always show the reason in plain words, built from the formula terms in this order: severity · road type · nearby school/hospital · report count · age. Example: *"Dangerous · main road · near school · 6 reports · 12 days open"*.

## Screen-by-screen copy

These are the exact words for the main screens; the AI coding tool should use them as written. Screen IDs match the App Flow.

| Screen             | Element       | Copy                                                                                  |
|--------------------|---------------|---------------------------------------------------------------------------------------|
| P1 Home            | Headline      | Spotted a pothole?                                                                    |
| P1 Home            | Subtext       | Report it in 30 seconds. No sign-up needed.                                           |
| P1 Home            | Buttons       | Report a pothole · Track my report · Drive mode                                       |
| P1 Home            | Footer link   | See all reported potholes on the map                                                  |
| P2 Capture         | Instruction   | Point your camera at the pothole. Stand 1–2 m away.                                   |
| P2 Capture         | Buttons       | Take photo · Choose from gallery                                                      |
| P3 Review          | Title         | Check your report                                                                     |
| P3 Review          | Pin hint      | Is the pin on the pothole? Drag it if not.                                            |
| P3 Review          | Note field    | Add a note (optional) — placeholder: "e.g. near the bus stop"                         |
| P3 Review          | Button        | Submit report                                                                         |
| P3 Review          | Privacy line  | We blur faces and number plates. We don't collect your name or number.                |
| P4 Uploading       | Progress      | Checking your photo…                                                                  |
| P4 Result (new)    | Title         | Thanks! Your report is on the map.                                                    |
| P4 Result (merged) | Title         | Thanks! Added to an existing report.                                                  |
| P4 Result (merged) | Detail        | 4 people have reported this spot. More reports help it get fixed sooner.              |
| P4 Result          | Code          | Your tracking code: **RS-7K2Q** · buttons: Copy · Share                               |
| P4 Result          | Buttons       | Done · Track this report                                                              |
| P5 Track           | Title         | Track a report                                                                        |
| P5 Track           | Field         | Enter your tracking code — placeholder "RS-7K2Q"                                      |
| P5 Track           | My reports    | Reports from this phone                                                               |
| P6 Drive mode      | Safety screen | Mount your phone before you ride. Don't touch it while moving. — button: I understand |
| P6 Drive mode      | Setup         | Point the camera at the road, about 5–10 m ahead.                                     |
| P6 Drive mode      | Buttons       | Start · Stop                                                                          |
| P6 Drive mode      | Counter       | 12 found · 9 sent · 4.2 km                                                            |
| P6 Drive mode      | Summary       | Ride complete. 12 potholes found over 4.2 km.                                         |
| P7 Public map      | Title         | Reported potholes                                                                     |
| P7 Public map      | Legend        | Minor · Moderate · Dangerous · Fixed (last 30 days)                                   |
| A1 Login           | Title         | Engineer sign in                                                                      |
| A1 Login           | Demo button   | Try the demo account (read only)                                                      |
| A2 Dashboard       | KPI cards     | Open defects · Dangerous, open · New this week · Fixed this week                      |
| A2 Dashboard       | Side panel    | Fix these first                                                                       |
| A2 Dashboard       | Banner        | 3 photos need your review                                                             |
| A3 Repair list     | Bulk actions  | Mark assigned · Mark fixed · Export CSV · Export PDF                                  |
| A4 Defect detail   | Sections      | Photos · Why this severity · Why this priority · Reports on map · History             |
| A5 Surveys         | Done card     | 38 potholes found → 21 defects (9 new, 12 added to existing)                          |
| P8 Results         | Intro         | How well RoadSense works, measured on road images it never saw during training.       |

## Error, empty and permission messages

Every message follows one pattern: what happened, in plain words, then what to do, with a button for the fix.

**Pattern:** *\[What happened.\] \[What to do.\]* + button. No error codes, no "Oops", no "Something went wrong" without a next step.

| Situation                   | Message                                                                                         | Button(s)                  |
|-----------------------------|-------------------------------------------------------------------------------------------------|----------------------------|
| Camera blocked              | Camera access is off. Turn it on in your browser settings, or choose a photo from your gallery. | Choose from gallery        |
| Location blocked            | We can't see your location. Drag the pin to where the pothole is.                               | —                          |
| Weak GPS (\> 30 m)          | Your location is approximate. Please check the pin.                                             | —                          |
| No damage found             | We couldn't find road damage in this photo. Try a closer photo in good light.                   | Retake photo · Send anyway |
| Too dark / blurry           | This photo is too dark or blurry to check.                                                      | Retake photo               |
| Offline                     | You're offline. We'll send your report when you're back online.                                 | OK                         |
| Slow server (\> 10 s)       | Still checking… We've saved your report and will finish it shortly.                             | Show my code               |
| Upload failed               | Your report didn't send. Check your connection and try again.                                   | Try again                  |
| Outside pilot area          | RoadSense works only in \[pilot area\] right now.                                               | OK                         |
| Rate limit                  | Too many reports from this network. Please try again in an hour.                                | OK                         |
| Wrong tracking code         | No report found with this code. Check it and try again.                                         | —                          |
| Drive mode: phone too slow  | Live detection is slow on this phone. We'll check a photo every 2 seconds instead.              | Continue                   |
| Drive mode: no GPS          | Drive mode needs your location. Turn on location to start.                                      | Open settings              |
| Admin: wrong password       | Email or password is incorrect.                                                                 | —                          |
| Admin: locked               | Too many attempts. Try again in 10 minutes.                                                     | —                          |
| Admin: session expired      | Please sign in again to continue.                                                               | Sign in                    |
| Survey failed               | We couldn't process this video: \[reason\].                                                     | Retry                      |
| Empty map                   | No potholes reported yet. Be the first.                                                         | Report a pothole           |
| Empty repair list (filters) | No defects match these filters.                                                                 | Clear filters              |
| Empty my reports            | You haven't reported anything from this phone yet.                                              | Report a pothole           |

**Permission prompts:** explain *before* the browser asks. *"RoadSense needs your camera to photograph the pothole and your location to put it on the map."* Button: *Allow camera and location*.

## Explaining AI results honestly

The AI can be wrong, so the app always says what it found, how sure it is, and why, and lets a person overrule it.

1.  **Say "AI" once, clearly.** "Our AI found a pothole" on the result card; after that, just state the result.

2.  **Show confidence in words.** Map the detector confidence to: *Very likely* (≥ 0.80), *Likely* (0.50–0.79), *Possible* (0.35–0.49). Example: "Pothole · Very likely".

3.  **Explain severity in one sentence** built from the strongest factors: "Dangerous because it is large, deep and in the wheel path." Never just a number.

4.  **Be clear that depth is estimated.** Use "looks deep", not "is 8 cm deep". The app never shows centimetres.

5.  **Never overclaim.** Avoid *accurate*, *guaranteed*, *detects all potholes*, *real-time city monitoring*. Use *helps find*, *estimates*, *ranks*.

6.  **A person decides.** Engineers see "AI suggestion" next to severity and can change status or mark *Not a defect*. Citizens can *Send anyway* when the AI disagrees.

7.  **Results page:** report real numbers with the test set size and include failure examples: "It sometimes mistakes speed breakers and wet patches for potholes."

## Accessibility and translation-ready writing

Writing simply now makes the app usable outdoors and makes the Hindi version in P2 a translation job, not a rewrite.

**Accessibility**

- Never rely on colour alone: severity always has a word and an icon.

- Every button and icon has a text label or aria-label ("Copy tracking code", not "Copy").

- Every image has alt text: "Photo of reported pothole, Dangerous".

- Body text at least 16 px; buttons at least 44 px tall; strong contrast (WCAG AA) because people use the app in sunlight.

- Messages that appear after an action (upload done, error) are announced to screen readers (aria-live).

- Don't put instructions only inside placeholders; they disappear when typing.

**Translation-ready (English now, Hindi later)**

- Put every UI string in one file from day one: frontend/src/locales/en.json, using i18next keys like report.submit. Never hard-code text in components.

- Write full sentences as one string with placeholders: "{{count}} people have reported this spot", not pieces joined in code.

- Handle plurals with i18next plural keys (1 report / 3 reports).

- Avoid idioms and slang ("heads up", "good to go").

- Leave 40% extra space in buttons and cards; Hindi text is often longer.

- Format dates and numbers with Intl APIs using the locale, never by string building.

- Keep tracking codes, "AI" and "GPS" unchanged in every language.

- When Hindi is added: use simple everyday Hindi (not formal Sanskritised terms) and get one native speaker to review.

## Rules for the AI coding tool and review checklist

Paste the rules below into CLAUDE.md (or your Cursor rules) so every generated screen follows this guide without reminders.

```markdown
## Content rules (from docs/content-guidelines.md)
- All UI text lives in frontend/src/locales/en.json (i18next). Never hard-code strings.
- Use copy from the "Screen-by-screen copy" table exactly when it exists.
- Sentence case everywhere. Buttons: verb first, 1-3 words.
- Indian/British spelling (colour, centre). Dates like 27 Nov 2026. Times like 6:30 pm.
- Citizen screens say "pothole" and "report"; admin screens say "defect".
- Damage types: Pothole, Alligator crack, Crack across road, Crack along road.
- Severity labels: Minor (green, circle), Moderate (amber, triangle), Dangerous (red, diamond).
- Errors: what happened + what to do + a button. No "Oops", no error codes.
- No exclamation marks except "Thanks!" on success. No emoji. No ALL CAPS.
- Never promise repairs or dates. Never claim the AI is always right.
- Every icon button has an aria-label; every image has alt text.
```

**Review checklist before each commit**

- [ ] No hard-coded strings; all text in en.json

- [ ] Copy matches the Screen-by-screen table where one exists

- [ ] Terms match the Terminology table (no "complaint", "ticket", "issue")

- [ ] Every error tells the user what to do next

- [ ] Severity shown with word + colour + icon

- [ ] No promises about repairs; AI wording is honest

- [ ] Alt text and aria-labels present

- [ ] Read every new string out loud: if it sounds like a government form, rewrite it
