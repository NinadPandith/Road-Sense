#!/usr/bin/env bash
# Build the report as a Word document (and HTML for a quick look) with pandoc + citeproc.
#   docs/report/build.sh            -> docs/report/build/RoadSense-report.docx
# Requires pandoc >= 2.11. To use your college's Word template, add: --reference-doc=template.docx
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
CHAPTERS=(00-front-matter.md 01-introduction.md 02-literature.md 03-requirements.md 04-design.md
  05-implementation.md 06-data-training.md 07-testing.md 08-results.md 09-conclusion.md
  10-references.md 11-appendix.md)
COMMON=(--citeproc --bibliography=references.bib --number-sections --toc --toc-depth=2
  --resource-path=.:figures:../images:../../ml/results --metadata link-citations=true)
pandoc "${CHAPTERS[@]}" "${COMMON[@]}" -o build/RoadSense-report.docx
pandoc "${CHAPTERS[@]}" "${COMMON[@]}" --standalone --embed-resources -o build/RoadSense-report.html 2>/dev/null || true
echo "Built build/RoadSense-report.docx"
echo "Placeholders left to fill: $(grep -o '\[\[[^]]*\]\]' "${CHAPTERS[@]}" | wc -l)"
