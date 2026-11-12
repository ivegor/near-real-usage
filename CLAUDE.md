# Project context for Claude Code

NEAR HACKATHON (Nov 2026), track **Investment Thesis**. Deadline: **2026-11-14 23:59 UTC**.
Submission = public GitHub repo (with LICENSE) + public demo post on X tagging @NEARProtocol and #NEARHackathon
+ form with a NEAR wallet address for the prize. Rules: https://nearhackathon.com/HACKATHON.md

The owner writes Python and Rust.

## State (2026-11-12, late evening UTC)

* `python -m pytest -q` passes (18 tests); `python -m thesis build` and `--offline` work on live data through 2026-11-11.
* The thesis was rewritten around a full-chain account census from BigQuery (`sql/account_age.sql`, result in
  `data/bq/account_age.csv`, code in `thesis/population.py`). It refuted the first draft's claim that returning
  accounts grew 37%: core accounts active two months running fell 73%. THESIS.md says so openly.
* The BigQuery query was run once in the owner's personal sandbox project through the browser console. It costs
  482.64 GB of the free 1 TB a month, so there is no second full run in November 2026. Never query the `accounts`
  table (1.03 TB). Always read the dry-run estimate first.
* `thesis/census.py` is an optional keyless check (random blocks + account ages over public FastNEAR endpoints). Its
  long background runs may still be going or finished; outputs land in `data/raw/census_*` and the cache in
  `data/census_cache/` (gitignored). When `data/raw/census_sample.csv` exists the build adds a "signer census" chart.
  It is not referenced in THESIS.md yet; add it as an independent cross-check once the files are complete.
* Git: local repository on `main`, author `ivegor` (GitHub noreply address in the repo-local config), commit messages
  without attribution trailers. Nothing pushed, no GitHub repo yet.

## Next steps

1. If the census run finished: compare its transaction shares by account age with BigQuery for the same months,
   add one paragraph and the chart reference to THESIS.md, commit `data/raw/census_*`.
2. Create the public GitHub repo (ask the owner first), push, enable GitHub Pages (source: GitHub Actions),
   check the first workflow run and the live dashboard.
3. X post: draft is in `POST_DRAFT.md` (gitignored); it needs the real links and a screenshot of the first chart.
   The owner posts it; the post must say the project was built at NEAR HACKATHON.
4. Fill the submission form with the owner (needs their NEAR wallet address). One submission only, after the repo
   and the post are public.

## Thesis in one line

Accounts acting on NEAR fell 97% in a year (43.6M to 1.38M a month) and 97% of the loss is two reward and wallet apps;
outside them the base also fell 66%, the only growing group is 71K named `.near` accounts (+13%) that now send 48% of
all transactions, Intents volume is up 223%, and usage does not lead price.
