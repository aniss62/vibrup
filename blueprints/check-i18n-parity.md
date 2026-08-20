# Blueprint: Check FR/EN/ES structural parity

**Goal:** Confirm every localized page (FR at the root, EN under `en/`, ES under
`es/`) shares the exact same HTML structure — same tags, same attributes, same
nesting — so a change made in one language doesn't silently drift from the others.
Only text content is expected to differ.

**Inputs needed:** none (python3, already required for local preview).

**Steps:**
1. Run `equipment/check-i18n-parity.py`.
2. Read the report:
   - `[OK]` — the page's translations match structurally.
   - `[TODO]` — a language is registered but the file doesn't exist yet (not a
     failure, just unfinished).
   - `[FAIL]` — the page exists in two+ languages but their structure diverges;
     the diff shows the first tag positions that differ.
3. If a page was intentionally restructured (e.g. a new section added), apply the
   same structural change to its other language versions, then re-run.
4. When adding a brand-new page, register it in the `PAGES` dict at the top of
   `equipment/check-i18n-parity.py` first (ask before editing this Blueprint if the
   workflow itself needs to change, but the `PAGES` registry is equipment config,
   not the Blueprint, so it's fine to update directly).

**Expected output:** Exit code 0 and all-`[OK]`/`[TODO]` (no `[FAIL]`) when the
three languages are in sync.
