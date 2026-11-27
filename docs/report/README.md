# Project report (W3)

One Markdown file per chapter. Build a Word document (for your guide and your college template):

```bash
docs/report/build.sh
```

The output is `docs/report/build/RoadSense-report.docx` (git-ignored). Use your college's Word
template with `--reference-doc=template.docx` in `build.sh`.

Before submission:

1. Fill every `[[...]]` placeholder: real numbers from `ml/results/`, your details, your city.
   `build.sh` prints how many are left.
2. Replace the interim UI screenshots in `figures/` (taken with test data) with real ones.
3. Rewrite any paragraph you can't explain in your own words; the viva will test it.
