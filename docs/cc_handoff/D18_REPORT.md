[D18 real-PDF title pattern expansion report]

Goal (per GPT): support real-world Figure/Table caption forms — especially ARM-style
no-colon captions — WITHOUT weakening the negative false-positive guards or
regressing RTM frozen. Anchor-coverage stage only (not a real-PDF correctness pass).

## 1. Summary
- title pattern changes: added no-colon caption support
  (`Figure 3-3 Read transfer with two wait states`) alongside the existing
  punctuated form (`Figure 3.4. Title` / `Table 1-7: Title`), with a
  reference-sentence guard so prose lines are still rejected.
- real PDF smoke: `dp_sample1.pdf` went **0/0 → 3 figures / 1 table**;
  `dp_sample.pdf` stayed **3 figures / 3 tables**.

## 2. Files changed
- `picker_cmc_v1/detector/title_patterns.py` — split caption matching into
  alias+index head, then a punctuated (`[.:]\s+`) branch and a no-colon
  (whitespace) branch; the no-colon branch applies `_looks_like_reference()`.
- `tests/test_detector_title_patterns_d18.py` (NEW, 27 cases incl. local smoke).
- Nothing else touched (no detector pipeline / region / common-region changes).

## 3. Commands run
- `python tools/run_detector_on_pdf.py --pdf ../pdf/dp_sample1.pdf --out artifacts/real_pdf_smoke/dp_sample1 --json`
- `python tools/run_detector_on_pdf.py --pdf ../pdf/dp_sample.pdf  --out artifacts/real_pdf_smoke/dp_sample  --json`
- RTM frozen regression runner; `python -m pytest tests picker_cmc_v1 -q` → **163 passed**

## 4. Pattern coverage
- colon captions: `Figure 1-1: DP Data Transport Channels`, `Table 1-7: …` — accepted
- no-colon captions: `Figure 3-3 Read transfer with two wait states`,
  `Table 3-1 Transfer type encoding` — accepted
- Fig./FIGURE aliases: `Fig. A.1 Example waveform timing`, `FIGURE 2-7 Example title` — accepted
- table captions: punctuated + no-colon both accepted
- index forms preserved: `3.4`, `12`, `2-7`, `A.1`, `3-3`

## 5. False-positive guards
- shows/lists/reference sentences: rejected — guard keys on the first title word.
  An all-lowercase first word (sentence continuation: `shows`, `lists`, `is`,
  `describes`, `summarizes`, `illustrates`, `in`, `on` …) → reject; an explicit
  reference-verb set rejects even a capitalised `Shows`/`Lists`/`Is`.
- `Figure of merit …`: no numeric index → never matches the head.
- `see Table above` / `In Figure 3-5:`: do not start with the alias → never match.
- Not over-blocked: capitalised positional titles survive — `Figure 5 On-chip
  memory map`, `Figure 6 Above-threshold detection` are accepted (locked by tests).

## 6. Metrics
- RTM frozen regression: cases 47/49, objects 100/100, missing 0, extra 0,
  regions 206/210 — **identical to D17 (no regression)**
- dp_sample.pdf: 3 figures / 3 tables (unchanged)
- dp_sample1.pdf: **3 figures / 1 table** (was 0 / 0) — meets target (figs≥3, tbls≥1)
- negative FP: **0** (RTM negative corpus + D18 reference-sentence corpus all None)

## 7. Did not touch
- rtm_frozen: unchanged
- truth schema: unchanged
- compare tolerance: unchanged
- RTM scenarios: unchanged
- common-region / body / context inference: unchanged (only title_patterns.py)

## 8. Known limitations
- no real PDF ground truth: anchor coverage verified by counts + visual review,
  not a correctness pass; body/context crops for the new no-colon captions are not
  guaranteed pixel-perfect (out of D18 scope).
- residual no-colon ambiguity: a prose line like "Figure 3-3 Read operations are
  described below" (capitalised non-blocklist first word) can still match; the
  guard targets the common reference forms GPT enumerated and is locked by tests.
- visual review still required for any real PDF.

## 9. Tests
- `tests/test_detector_title_patterns_d18.py` (27): no-colon accepts, reference
  rejects, punctuated preserved, negative-corpus zero-FP, capitalised-positional
  survival, and the dp_sample1 local smoke (≥3 figures / ≥1 table).
- full suite: **163 passed**.

Commit on `picker-cmc-d03`. Stopping after D18 report per instruction.
