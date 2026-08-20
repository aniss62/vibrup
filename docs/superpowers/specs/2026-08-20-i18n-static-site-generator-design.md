# i18n Static Site Generator — Design

## Goal

Replace the current "one hand-maintained HTML file per page per language" setup
(18 files: 6 pages × FR/EN/ES) with a single template per page plus one
translation-strings file per language. Structural drift between languages
becomes impossible by construction (one template renders all three languages),
instead of being caught after the fact by a parity checker. Public URLs, file
paths, and the Vercel deploy (static files, no build command on Vercel's side)
stay unchanged — this is a change to how the *source* is authored, not to what
gets served.

## Non-goals

- No new runtime dependency (no npm, no pip package). Python 3.9 stdlib only,
  matching what's already required for `equipment/serve.sh`.
- No client-side i18n / JS language switching. Pages stay fully static HTML
  with the correct `lang` and `hreflang` baked in at build time (SEO
  requirement already in place today).
- No template loops or conditionals. Repeated blocks (FAQ items, resource
  cards) are fixed-count and written once per page template with one
  translation key per block — not generated from a data loop.
- No change to `styles.css`, `script.js`, or `images/` — untouched, hand-authored
  as today.

## Directory layout

```
templates/
  pages/
    home.html
    about.html
    article.html
    contact.html
    guidance.html
    resources.html
  partials/
    nav.html
    footer.html
    whatsapp-float.html
i18n/
  fr.py
  en.py
  es.py
equipment/
  site_map.py          (new — shared registry, see below)
  build.py              (new — the generator)
  check-i18n-parity.py  (existing — role changes, see "Parity checker" below)
  serve.sh               (modified — runs build.py first)
  deploy.sh              (modified — runs build.py first)
```

## `equipment/site_map.py` — the shared registry

A single source of truth for "which logical page maps to which file, in which
language", replacing the `PAGES` dict that's currently duplicated inline in
`check-i18n-parity.py`. Both `build.py` and `check-i18n-parity.py` import it.

```python
# equipment/site_map.py
SITE_URL = "https://www.vibr-up.com"
LANGS = ("fr", "en", "es")

# nav_id is None for pages not linked from the main nav (about, article).
PAGES = {
    "home":      {"template": "home.html",     "nav_id": "home",
                  "fr": "index.html",       "en": "en/index.html",     "es": "es/index.html"},
    "about":     {"template": "about.html",    "nav_id": None,
                  "fr": "a-propos.html",    "en": "en/about.html",     "es": "es/acerca-de.html"},
    "article":   {"template": "article.html",  "nav_id": None,
                  "fr": "article.html",     "en": "en/article.html",   "es": "es/articulo.html"},
    "contact":   {"template": "contact.html",  "nav_id": "contact",
                  "fr": "contact.html",     "en": "en/contact.html",   "es": "es/contacto.html"},
    "guidance":  {"template": "guidance.html", "nav_id": "guidance",
                  "fr": "guidance.html",    "en": "en/guidance.html",  "es": "es/guidance.html"},
    "resources": {"template": "resources.html","nav_id": "resources",
                  "fr": "ressources.html",  "en": "en/resources.html","es": "es/recursos.html"},
}

# Order + labels (label text comes from i18n nav.*, this just fixes the order
# and which pages appear in the nav bar).
NAV_ORDER = ["home", "resources", "guidance", "contact"]
```

(`pricing` is a same-page anchor — `index.html#tarifs` — not a separate page, handled
directly in the nav partial.)

## Templating mechanics

**Placeholder syntax:** `{{ dotted.path }}`, resolved against the current
language's `STRINGS` dict. Implemented with one `re.sub` call using a resolver
function — no external template engine.

```python
PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")

def resolve(strings: dict, dotted_path: str) -> str:
    value = strings
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(dotted_path)
        value = value[part]
    if isinstance(value, dict):
        raise KeyError(f"{dotted_path} is a section, not a string")
    return value

def render(template_text: str, strings: dict) -> str:
    def _sub(m):
        try:
            return resolve(strings, m.group(1))
        except KeyError as e:
            raise KeyError(f"missing translation key: {e}") from None
    return PLACEHOLDER_RE.sub(_sub, template_text)
```

A missing key is a hard error (`build.py` exits non-zero with the page,
language, and key name) — never a silently blank string or a leftover
`{{ }}` in shipped HTML.

**What's a translation key vs. what's hardcoded in the template:** anything
identical across all three languages today — icons (`✦`, `〜`, `↝`), card
numbers (`01`/`02`/`03`), image URLs, `data-category` values, the WhatsApp
`href`, element `id`s — stays as a literal in the template. Only text that
actually differs per language becomes a `{{ key }}`.

**Key naming convention:**
- `nav.*` — shared nav labels (`home`, `resources`, `guidance`, `pricing`, `contact`)
- `footer.*` — shared footer (`about`, `legal`, `terms`, `contact`, `copyright`)
- `common.*` — strings reused verbatim across pages (`start_free_cta`,
  `open_menu_aria`, `whatsapp_aria`)
- `pages.<page_id>.*` — everything specific to one page, nested to mirror the
  page's own structure, e.g. `pages.home.hero.title`,
  `pages.home.pricing.free.item2`, `pages.resources.articles.grounding.title`.
  Repeated fixed-count blocks (FAQ entries, resource cards) get one key per
  block (`pages.guidance.faq.reschedule.question`), not a loop.

**Partials:** `nav.html`, `footer.html`, `whatsapp-float.html` are rendered
with the same `render()` function, called from `build.py` with a context that
includes both the language's `STRINGS` and page-specific values computed by
`build.py` (which nav item is active, the two other-language URLs for the lang
switch, the current page's hreflang alternates). These computed values are
injected as extra keys (e.g. `_active_home`, `_lang_switch`) merged onto a
shallow copy of `STRINGS` before rendering the partial — `build.py` code, not
template logic.

## `equipment/build.py` — behavior

```
Usage: equipment/build.py
No arguments. Regenerates every file listed in site_map.PAGES, for every
language present for that page, writing directly to its registered path
(e.g. index.html, en/index.html, es/index.html) — the same paths the site
already deploys from. Every generated file starts with:
  <!-- AUTO-GENERATED by equipment/build.py — edit templates/ and i18n/, not this file. -->
Exit code 0 on success. Exit 1 with a clear "page X / lang Y / key Z" message
on the first missing translation key or template error — it does not partially
write a broken file.
```

It touches only the files registered in `site_map.PAGES`. `styles.css`,
`script.js`, `images/`, and any non-generated file are never written.

## `serve.sh` / `deploy.sh` changes

Both scripts run `equipment/build.py` as their first step (fail the whole
script if the build fails), so what's previewed or deployed always reflects
the current templates + i18n content, never stale generated output.

## Parity checker's new role

`check-i18n-parity.py` is kept, refactored to import `PAGES` from
`equipment/site_map.py` instead of duplicating it. Its job changes from "the
only defense against FR/EN/ES drift" to a regression guard for two specific
failure modes the build can't catch by construction: (1) someone hand-edits a
generated HTML file directly instead of the template, (2) a future template
change accidentally makes structure conditional on language (e.g. an `{{#if}}`
grafted on later). `blueprints/check-i18n-parity.md` gets a short update
explaining the new role; the workflow (run it, read the report) doesn't change.

## Migration plan (source of the 18 existing files → templates + i18n)

1. Build `i18n/fr.py`, `i18n/en.py`, `i18n/es.py` by transcribing the current
   FR/EN/ES text (already fully translated and live) into the key structure
   above — no new translation work, this is a restructuring of existing copy.
2. Build the 6 page templates and 3 partials from the current FR HTML
   structure (already confirmed structurally identical across languages by
   the existing parity checker), replacing translated text with `{{ }}`
   placeholders and computed nav/footer/hreflang with partial includes.
3. Run `equipment/build.py`.
4. Verify fidelity: `git diff` the 18 regenerated files against the versions
   currently in the repo. Expected diff: only the new auto-generated-file
   comment header. Any other diff is a migration bug — fix the template or
   i18n entry, rebuild, re-diff, until clean.
5. Run `equipment/check-i18n-parity.py` — expect all `[OK]`.
6. Commit templates/, i18n/, equipment/site_map.py, equipment/build.py, the
   modified serve.sh/deploy.sh/check-i18n-parity.py, and the (now
   auto-generated, likely near-identical) 18 HTML files together.

## Testing

- `build.py` is deterministic pure-function-style code (render + resolve) —
  straightforward to unit test with small in-memory templates/dicts (missing
  key raises, nested key resolves, partial context merge works) without
  touching the filesystem.
- End-to-end confidence comes from the migration fidelity diff (step 4 above)
  plus the existing local-preview blueprint (serve the rebuilt site, click
  through it) and the parity checker.

## Open items for the implementation plan

None — this spec fixes the syntax, the file layout, the registry shape, and
the migration/verification method. The implementation plan's job is to: write
`site_map.py` and `build.py` with tests, migrate the 6 pages' content into
templates + the 3 i18n files (mechanical transcription of already-approved
copy), wire up `serve.sh`/`deploy.sh`, update the parity checker and its
blueprint, and run the migration-fidelity diff to close it out.
