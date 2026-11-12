# Project context for Claude Code

NEAR HACKATHON (Nov 2026), track **Investment Thesis**. Deadline: **2026-11-14 23:59 UTC**.
Submission = public GitHub repo (with LICENSE) + public demo post on X tagging @NEARProtocol and #NEARHackathon
+ form with a NEAR wallet address for the prize. Rules: https://nearhackathon.com/HACKATHON.md

The owner writes Python and Rust. Answer in Russian.

## State (2026-11-12, after the first live build)

* `.venv` recreated on Python 3.12; `python -m pytest -q` passes (8 tests); `python -m thesis build` ran on live data
  through 2026-11-11. `data/raw/`, `data/daily.csv` and `docs/` are committed outputs of that run.
* `Makefile` and `.github/workflows/build.yml` recreated.
* The YoY table in THESIS.md matched the Python build exactly. Fixed after the build: the lead-lag details
  (9 of 85 lag tests are outside the noise band, see `lead_vs_price.*.outside_band` in `docs/summary.json`) and the
  "525,011" figure (it is the same 90-day window of 2024, not a 2024 average).
* Added to the code and the docs: medians, fees in NEAR terms, a quarter-on-quarter table (`qoq_90d`) and `checks`.
* Known weak point, stated in THESIS.md "Evidence against": `returning = active − new` is only a lower bound
  (new > active on 7 of 90 days in the year-earlier window), so "+37% returning" is the favourable end of the range.
  The owner has not yet decided whether to keep claim 1 as "Supported, size uncertain" or reframe it.
* Git: local repository on `main`, committed. Nothing pushed, no GitHub repo yet.

## Next steps

1. Owner decisions: name for LICENSE (still "NEAR Real Usage authors"), GitHub repo name, framing of claim 1.
2. Create the public GitHub repo (ask the owner first), push, enable GitHub Pages (source: GitHub Actions),
   check the first workflow run and the live dashboard.
3. X post: draft is in `POST_DRAFT.md`; put the real dashboard + repo links in, show it to the owner before posting.
4. Fill the submission form with the owner (needs their NEAR wallet address).

## Thesis in one line

Headline NEAR activity fell ~75% YoY, but returning accounts (active − new, a lower bound) grew ~37% (+11% by medians),
fees per account ~+120% in USD (+43% in NEAR), tx per account ~−30%, Intents volume ~+223%; usage does NOT lead price
(returning accounts and Intents: nothing outside the noise band at any lag; fees co-move with price in the same week).
