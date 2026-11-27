# Launch checklist (from the implementation plan)

## Fill in the placeholders

```bash
grep -rn "\[\[" README.md docs/report ml/hf docs/launch | wc -l
```

```bash
grep -n "TBD" paper/main.tex | wc -l
```

```bash
grep -rln "YOUR-" README.md ml/hf ml/notebooks
```

## Definition of done

- [ ] All P0 and P1 requirements work on the live URL
- [ ] Pothole mAP@0.5 and severity agreement reported honestly, with test-set sizes
- [ ] Experiments E1–E6 complete, with tables in the report and on the results page
      (`cd ml && python -m scripts.build_results_json`, then commit `frontend/public/results/`)
- [ ] README, demo video, models and dataset public
- [ ] Report and paper drafts approved by your guide
- [ ] Viva notes cover every module (`docs/viva-notes.md`)

## Demo-day checklist

- [ ] Open the app 10 minutes early (wakes the backend and database)
- [ ] Log in to the demo account on the laptop; Drive mode tested on the phone that morning
- [ ] 30+ real defects on the map from your own rides
- [ ] Mobile hotspot ready in case college Wi-Fi blocks anything
- [ ] Backup: demo video downloaded offline
- [ ] Results page open in a tab
- [ ] One sentence ready: "RoadSense doesn't just detect potholes; it tells a city which one to
      fix first, and why."
