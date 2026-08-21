# Blueprint: Check FR/EN/ES structural parity

**Goal:** Confirm every localized page (FR at the root, EN under `en/`, ES under
`es/`) shares the exact same HTML structure — same tags, same attributes, same
nesting. Since every page is generated from a single template per page
(`templates/pages/*.html`) plus one translation-strings file per language
(`i18n/<lang>.py`), this is now guaranteed **by construction** — a mismatch can
only happen if someone hand-edits a generated file directly instead of its
template, or if a template change accidentally makes structure conditional on
language. This script is the regression guard for those two cases.

**Inputs needed:** none (python3, already required for local preview/build).

**Steps:**
1. Run `equipment/check-i18n-parity.py`.
2. Read the report:
   - `[OK]` — the page's translations match structurally.
   - `[TODO]` — a language is registered in `equipment/site_map.py` but its
     output file doesn't exist yet — run `equipment/build.py` first (it may
     just be stale) before treating this as a real gap.
   - `[FAIL]` — the page's rendered output diverges structurally between
     languages. Since structure comes from one shared template, this almost
     always means someone edited a generated HTML file by hand — restore it
     with `equipment/build.py` and make the real edit in `templates/` or
     `i18n/<lang>.py` instead.
3. To add a brand-new page: register it in `equipment/site_map.py`'s `PAGES`
   dict, add its template under `templates/pages/`, add its keys to all three
   `i18n/<lang>.py` files, run `equipment/build.py`, then re-run this check.

**Expected output:** Exit code 0 and all-`[OK]`/`[TODO]` (no `[FAIL]`).
