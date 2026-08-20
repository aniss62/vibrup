# i18n Static Site Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 18 hand-duplicated FR/EN/ES HTML files with one template per
page plus one translation-strings file per language, rendered by a small stdlib-only
Python generator (`equipment/build.py`), so structural drift between languages
becomes impossible by construction.

**Architecture:** See `docs/superpowers/specs/2026-08-20-i18n-static-site-generator-design.md`
for the approved design. Summary: `equipment/site_map.py` is the single registry of
page → per-language file path; `equipment/build.py` does `{{ dotted.key }}` string
substitution (stdlib `re`, no template engine) against `i18n/{fr,en,es}.py` dicts and
`templates/pages/*.html` + `templates/partials/*.html`; output is written directly to
the existing deployed file paths.

**Tech Stack:** Python 3.9 stdlib only (`re`, `pathlib`, `importlib`, `unittest`). No
new dependency, no npm, no pip package.

---

## Task 1: Package scaffolding + site_map registry

**Files:**
- Create: `equipment/__init__.py`
- Create: `equipment/site_map.py`
- Create: `i18n/__init__.py`

- [ ] **Step 1: Create the empty package markers**

`equipment/__init__.py` (empty file — makes `equipment` importable as
`equipment.site_map`, `equipment.build`):
```python
```

`i18n/__init__.py` (empty file — makes `i18n` importable as `i18n.fr`, `i18n.en`,
`i18n.es`):
```python
```

- [ ] **Step 2: Write the site map registry**

`equipment/site_map.py`:
```python
"""Shared registry: which logical page maps to which file, in which language.
Imported by equipment/build.py and equipment/check-i18n-parity.py — the only
place this mapping is defined.
"""

SITE_URL = "https://www.vibr-up.com"
LANGS = ("fr", "en", "es")

# nav_id says which main-nav item highlights as active when this page is
# rendered. None means no nav item is active on this page.
PAGES = {
    "home": {
        "template": "home.html", "nav_id": "home",
        "fr": "index.html", "en": "en/index.html", "es": "es/index.html",
    },
    "about": {
        "template": "about.html", "nav_id": None,
        "fr": "a-propos.html", "en": "en/about.html", "es": "es/acerca-de.html",
    },
    "article": {
        "template": "article.html", "nav_id": "resources",
        "fr": "article.html", "en": "en/article.html", "es": "es/articulo.html",
    },
    "contact": {
        "template": "contact.html", "nav_id": "contact",
        "fr": "contact.html", "en": "en/contact.html", "es": "es/contacto.html",
    },
    "guidance": {
        "template": "guidance.html", "nav_id": "guidance",
        "fr": "guidance.html", "en": "en/guidance.html", "es": "es/guidance.html",
    },
    "resources": {
        "template": "resources.html", "nav_id": "resources",
        "fr": "ressources.html", "en": "en/resources.html", "es": "es/recursos.html",
    },
}
```

- [ ] **Step 3: Commit**

```bash
git add equipment/__init__.py equipment/site_map.py i18n/__init__.py
git commit -m "Add site_map registry: single source of truth for page/language paths"
```

---

## Task 2: Template render engine (`resolve` / `render`) + tests

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_build.py`
- Create: `equipment/build.py` (engine only in this task; CLI added in Task 4)

- [ ] **Step 1: Write the failing tests**

`tests/__init__.py` (empty file).

`tests/test_build.py`:
```python
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from equipment.build import render, resolve  # noqa: E402


class TestResolve(unittest.TestCase):
    def test_resolves_nested_key(self):
        context = {"pages": {"home": {"hero": {"title": "Hello"}}}}
        self.assertEqual(resolve(context, "pages.home.hero.title"), "Hello")

    def test_resolves_top_level_key(self):
        context = {"_lang_html": "fr"}
        self.assertEqual(resolve(context, "_lang_html"), "fr")

    def test_missing_key_raises(self):
        context = {"pages": {"home": {}}}
        with self.assertRaises(KeyError):
            resolve(context, "pages.home.hero.title")

    def test_section_instead_of_string_raises(self):
        context = {"pages": {"home": {"hero": {"title": "Hello"}}}}
        with self.assertRaises(KeyError):
            resolve(context, "pages.home.hero")


class TestRender(unittest.TestCase):
    def test_substitutes_single_placeholder(self):
        context = {"nav": {"home": "Accueil"}}
        self.assertEqual(render("<a>{{ nav.home }}</a>", context), "<a>Accueil</a>")

    def test_substitutes_multiple_placeholders(self):
        context = {"a": "1", "b": "2"}
        self.assertEqual(render("{{a}}-{{b}}", context), "1-2")

    def test_missing_key_raises_with_key_name_in_message(self):
        with self.assertRaises(KeyError) as cm:
            render("{{ pages.home.missing }}", {"pages": {"home": {}}})
        self.assertIn("pages.home.missing", str(cm.exception))

    def test_leaves_non_placeholder_text_untouched(self):
        self.assertEqual(render("<p>plain text</p>", {}), "<p>plain text</p>")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_build -v`
Expected: `ModuleNotFoundError: No module named 'equipment.build'` (or similar import
failure) — `equipment/build.py` doesn't exist yet.

- [ ] **Step 3: Write the minimal engine**

`equipment/build.py`:
```python
#!/usr/bin/env python3
"""Regenerates every page in site_map.PAGES from templates/ + i18n/.

Usage: equipment/build.py
No arguments. Exit 0 on success. Exit 1 with a "page=.. lang=.." message on
the first missing translation key or template error — never writes a
partially-rendered file.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")


def resolve(context, dotted_path):
    value = context
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(dotted_path)
        value = value[part]
    if isinstance(value, dict):
        raise KeyError(f"{dotted_path} is a section, not a string")
    return value


def render(template_text, context):
    def _sub(match):
        try:
            return str(resolve(context, match.group(1)))
        except KeyError as e:
            raise KeyError(f"missing translation key: {e}") from None
    return PLACEHOLDER_RE.sub(_sub, template_text)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_build -v`
Expected: `OK` (8 tests pass).

- [ ] **Step 5: Commit**

```bash
git add tests/__init__.py tests/test_build.py equipment/build.py
git commit -m "Add template render engine (dotted-key substitution) with tests"
```

---

## Task 3: Per-page context computation (nav/asset/hreflang) + tests

**Files:**
- Create: `tests/test_build_context.py`
- Modify: `equipment/build.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_build_context.py`:
```python
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from equipment.build import (  # noqa: E402
    asset_prefix,
    build_hreflang_context,
    build_nav_context,
    nav_href,
)


class TestNavHref(unittest.TestCase):
    def test_fr_href_is_root_relative(self):
        self.assertEqual(nav_href("fr", "resources"), "ressources.html")

    def test_en_href_strips_lang_prefix(self):
        self.assertEqual(nav_href("en", "resources"), "resources.html")

    def test_es_href_strips_lang_prefix(self):
        self.assertEqual(nav_href("es", "resources"), "recursos.html")


class TestAssetPrefix(unittest.TestCase):
    def test_fr_has_no_prefix(self):
        self.assertEqual(asset_prefix("fr"), "")

    def test_en_and_es_go_up_one_level(self):
        self.assertEqual(asset_prefix("en"), "../")
        self.assertEqual(asset_prefix("es"), "../")


class TestBuildNavContext(unittest.TestCase):
    def test_marks_current_page_active(self):
        ctx = build_nav_context("resources", "fr")
        self.assertEqual(ctx["resources_active"], ' class="active"')
        self.assertEqual(ctx["home_active"], "")

    def test_article_page_activates_resources(self):
        ctx = build_nav_context("article", "fr")
        self.assertEqual(ctx["resources_active"], ' class="active"')

    def test_about_page_activates_nothing(self):
        ctx = build_nav_context("about", "fr")
        for key in ("home_active", "resources_active", "guidance_active", "contact_active"):
            self.assertEqual(ctx[key], "")

    def test_lang_switch_from_fr_targets_en_then_es(self):
        ctx = build_nav_context("home", "fr")
        self.assertEqual(ctx["lang1_href"], "en/index.html")
        self.assertEqual(ctx["lang1_label"], "EN")
        self.assertEqual(ctx["lang2_href"], "es/index.html")
        self.assertEqual(ctx["lang2_label"], "ES")

    def test_lang_switch_from_en_targets_fr_then_es(self):
        ctx = build_nav_context("home", "en")
        self.assertEqual(ctx["lang1_href"], "../index.html")
        self.assertEqual(ctx["lang1_label"], "FR")
        self.assertEqual(ctx["lang2_href"], "../es/index.html")
        self.assertEqual(ctx["lang2_label"], "ES")

    def test_lang_switch_from_es_targets_fr_then_en(self):
        ctx = build_nav_context("guidance", "es")
        self.assertEqual(ctx["lang1_href"], "../guidance.html")
        self.assertEqual(ctx["lang1_label"], "FR")
        self.assertEqual(ctx["lang2_href"], "../en/guidance.html")
        self.assertEqual(ctx["lang2_label"], "EN")


class TestBuildHreflangContext(unittest.TestCase):
    def test_builds_absolute_urls_for_all_langs(self):
        ctx = build_hreflang_context("home")
        self.assertEqual(ctx["fr"], "https://www.vibr-up.com/index.html")
        self.assertEqual(ctx["en"], "https://www.vibr-up.com/en/index.html")
        self.assertEqual(ctx["es"], "https://www.vibr-up.com/es/index.html")
        self.assertEqual(ctx["x_default"], "https://www.vibr-up.com/index.html")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_build_context -v`
Expected: `ImportError: cannot import name 'nav_href'` — these functions don't exist
in `equipment/build.py` yet.

- [ ] **Step 3: Add the context-computation functions**

Append to `equipment/build.py` (after the `render` function, before nothing else
exists yet):
```python
from equipment.site_map import LANGS, PAGES, SITE_URL  # noqa: E402


def nav_href(lang, page_id):
    """Same-language relative link to page_id, as used from a page already
    inside that language's folder (bare filename for fr, prefix-stripped
    filename for en/es)."""
    path = PAGES[page_id][lang]
    if lang == "fr":
        return path
    return path.removeprefix(f"{lang}/")


def asset_prefix(lang):
    """Path prefix to reach repo-root assets (styles.css, script.js, images/)
    from a page written in this language."""
    return "" if lang == "fr" else "../"


def build_nav_context(page_id, lang):
    active_id = PAGES[page_id]["nav_id"]
    ctx = {}
    for nav_id in ("resources", "guidance", "contact", "article"):
        ctx[f"{nav_id}_href"] = nav_href(lang, nav_id)
    for nav_id in ("home", "resources", "guidance", "contact"):
        ctx[f"{nav_id}_active"] = ' class="active"' if active_id == nav_id else ""

    labels = {"fr": "FR", "en": "EN", "es": "ES"}
    other_langs = [l for l in LANGS if l != lang]
    for i, other in enumerate(other_langs, start=1):
        target_path = PAGES[page_id][other]
        href = target_path if lang == "fr" else "../" + target_path
        ctx[f"lang{i}_href"] = href
        ctx[f"lang{i}_label"] = labels[other]
    return ctx


def build_hreflang_context(page_id):
    ctx = {lang: f"{SITE_URL}/{PAGES[page_id][lang]}" for lang in LANGS}
    ctx["x_default"] = f"{SITE_URL}/{PAGES[page_id]['fr']}"
    return ctx
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_build_context -v`
Expected: `OK` (12 tests pass).

- [ ] **Step 5: Commit**

```bash
git add tests/test_build_context.py equipment/build.py
git commit -m "Add nav/asset/hreflang context computation with tests"
```

---

## Task 4: Build CLI (load i18n, render partials + pages, write files)

**Files:**
- Modify: `equipment/build.py`

- [ ] **Step 1: Append the orchestration code**

Append to `equipment/build.py`:
```python
import importlib

TEMPLATES = ROOT / "templates"
GENERATED_HEADER = (
    "<!-- AUTO-GENERATED by equipment/build.py "
    "— edit templates/ and i18n/, not this file. -->\n"
)


class BuildError(Exception):
    pass


def load_strings(lang):
    return importlib.import_module(f"i18n.{lang}").STRINGS


def render_partial(name, context):
    text = (TEMPLATES / "partials" / name).read_text(encoding="utf-8")
    # rstrip: partial files end with a trailing newline like any text file: the
    # page template controls its own blank-line spacing around the {{ }} block,
    # so a newline baked into the partial's own file would double it up.
    return render(text, context).rstrip("\n")


def build_page(page_id, page_info):
    template_text = (TEMPLATES / "pages" / page_info["template"]).read_text(encoding="utf-8")
    for lang in LANGS:
        if lang not in page_info:
            continue
        strings = load_strings(lang)

        base_context = dict(strings)
        base_context["_nav"] = build_nav_context(page_id, lang)
        base_context["_footer"] = {
            "about_href": nav_href(lang, "about"),
            "contact_href": nav_href(lang, "contact"),
        }
        base_context["_hreflang"] = build_hreflang_context(page_id)
        base_context["_asset_prefix"] = asset_prefix(lang)
        base_context["_lang_html"] = lang

        try:
            page_context = dict(base_context)
            page_context["_nav_block"] = render_partial("nav.html", base_context)
            page_context["_footer_block"] = render_partial("footer.html", base_context)
            page_context["_whatsapp_block"] = render_partial("whatsapp-float.html", base_context)

            if page_id in ("home", "guidance"):
                hamann_context = dict(base_context)
                if page_id == "home":
                    hamann_context["_hamann_cta_href"] = nav_href(lang, "guidance")
                    hamann_context["_hamann_cta_label"] = resolve(
                        strings, "pages.home.guidance_teaser.cta"
                    )
                else:
                    hamann_context["_hamann_cta_href"] = nav_href(lang, "contact")
                    hamann_context["_hamann_cta_label"] = resolve(strings, "pages.guidance.cta")
                page_context["_hamann_bio_block"] = render_partial("hamann-bio.html", hamann_context)

            output = render(template_text, page_context)
        except KeyError as e:
            raise BuildError(f"page={page_id} lang={lang}: {e}") from None

        out_path = ROOT / page_info[lang]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(GENERATED_HEADER + output, encoding="utf-8")


def main():
    try:
        for page_id, page_info in PAGES.items():
            build_page(page_id, page_info)
    except BuildError as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] built {len(PAGES)} pages x up to {len(LANGS)} languages")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it fails cleanly with no templates/i18n yet**

Run: `python3 equipment/build.py`
Expected: exits non-zero — `ModuleNotFoundError: No module named 'i18n.fr'` (or a
`FileNotFoundError` for the template file, depending on which is hit first). This
is expected at this point in the plan: templates and i18n content are added in the
following tasks. This step only confirms `build.py` runs and fails at the right
place (missing content), not with a Python syntax/import error in `build.py` itself.

- [ ] **Step 3: Commit**

```bash
git add equipment/build.py
git commit -m "Add build.py CLI: render every page/language and write output files"
```

---

## Task 5: Shared partials

**Files:**
- Create: `templates/partials/nav.html`
- Create: `templates/partials/footer.html`
- Create: `templates/partials/whatsapp-float.html`
- Create: `templates/partials/hamann-bio.html`

- [ ] **Step 1: Write the four partial templates**

`templates/partials/nav.html`:
```html
<header>
  <div class="wrap nav">
    <a href="index.html" class="logo"><span class="dot"></span> Vibr'Up</a>
    <nav class="nav-links">
      <a href="index.html"{{ _nav.home_active }}>{{ nav.home }}</a>
      <a href="{{ _nav.resources_href }}"{{ _nav.resources_active }}>{{ nav.resources }}</a>
      <a href="{{ _nav.guidance_href }}"{{ _nav.guidance_active }}>{{ nav.guidance }}</a>
      <a href="index.html#tarifs">{{ nav.pricing }}</a>
      <a href="{{ _nav.contact_href }}"{{ _nav.contact_active }}>{{ nav.contact }}</a>
      <div class="lang-switch">
        <a href="{{ _nav.lang1_href }}" class="lang-link">{{ _nav.lang1_label }}</a>
        <a href="{{ _nav.lang2_href }}" class="lang-link">{{ _nav.lang2_label }}</a>
      </div>
    </nav>
    <div class="nav-right">
      <button class="cta-btn">{{ common.start_free_cta }}</button>
      <button class="menu-toggle" aria-label="{{ common.open_menu_aria }}"><span></span><span></span><span></span></button>
    </div>
  </div>
</header>
```

`templates/partials/footer.html`:
```html
<footer>
  <div class="wrap footer-row">
    <div class="muted">{{ footer.copyright }}</div>
    <div class="footer-links">
      <a href="{{ _footer.about_href }}">{{ footer.about }}</a>
      <a href="#">{{ footer.legal }}</a>
      <a href="#">{{ footer.terms }}</a>
      <a href="{{ _footer.contact_href }}">{{ footer.contact }}</a>
    </div>
  </div>
</footer>
```

`templates/partials/whatsapp-float.html`:
```html
<a class="whatsapp-float" href="https://wa.me/33773332104" target="_blank" rel="noopener" aria-label="{{ common.whatsapp_aria }}">
  <svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><path d="M16.004 3C9.377 3 4 8.373 4 15c0 2.34.687 4.518 1.872 6.35L4 29l7.86-1.833A11.94 11.94 0 0 0 16.004 27C22.63 27 28 21.627 28 15S22.63 3 16.004 3Zm6.98 16.66c-.29.815-1.44 1.5-2.36 1.694-.628.132-1.448.238-4.206-.9-3.53-1.46-5.804-5.037-5.98-5.27-.17-.233-1.43-1.9-1.43-3.622s.902-2.567 1.222-2.92c.29-.32.633-.4.844-.4.21 0 .422.002.606.012.194.01.454-.073.71.542.29.7.986 2.42 1.07 2.596.086.176.144.383.03.616-.114.234-.172.38-.34.585-.17.205-.356.457-.508.614-.17.176-.347.367-.15.72.198.352.878 1.45 1.885 2.35 1.294 1.155 2.386 1.513 2.738 1.684.352.17.558.146.762-.088.204-.234.876-1.02 1.11-1.37.234-.35.468-.29.79-.174.32.117 2.038.96 2.388 1.135.35.176.582.263.668.41.086.146.086.848-.204 1.663Z"/></svg>
</a>
```

`templates/partials/hamann-bio.html` — its call site in both `home.html` and
`guidance.html` is a line that is *only* 4 spaces of indent followed by
`{{ _hamann_bio_block }}`, and `render()` is a plain string substitution (it
does not re-indent a multi-line replacement per line). So this partial's first
line must have **no** leading spaces — the call site's 4-space prefix already
supplies that — while every following line carries its real, absolute target
indentation directly, as if this text had been typed straight into the page:
```html
<div class="guidance">
      <div class="avatar-orb"><img src="{{ _asset_prefix }}images/hamann.jpg" alt="Hamann" /></div>
      <div>
        <h3>Hamann</h3>
        <div class="tagline">{{ person.hamann.tagline }}</div>
        <p>{{ person.hamann.bio1 }}</p>
        <p>{{ person.hamann.bio2 }}</p>
        <div class="channels">
          <span class="channel-pill">{{ person.hamann.channel_phone }}</span>
          <span class="channel-pill">{{ person.hamann.channel_video }}</span>
          <a class="channel-pill" href="https://wa.me/33773332104" target="_blank" rel="noopener">💬 WhatsApp</a>
        </div>
        <div class="guidance-price">{{ person.hamann.price }}</div>
        <a href="{{ _hamann_cta_href }}" class="btn-primary">{{ _hamann_cta_label }}</a>
      </div>
    </div>
```

- [ ] **Step 2: Commit**

```bash
git add templates/partials/
git commit -m "Add nav/footer/whatsapp/hamann-bio partials"
```

---

## Task 6: Page template — home

**Files:**
- Create: `templates/pages/home.html`

- [ ] **Step 1: Write the template**

`templates/pages/home.html`:
```html
<!DOCTYPE html>
<html lang="{{ _lang_html }}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{{ pages.home.meta.title }}</title>
<meta name="description" content="{{ pages.home.meta.description }}" />
<link rel="alternate" hreflang="fr" href="{{ _hreflang.fr }}" />
<link rel="alternate" hreflang="en" href="{{ _hreflang.en }}" />
<link rel="alternate" hreflang="es" href="{{ _hreflang.es }}" />
<link rel="alternate" hreflang="x-default" href="{{ _hreflang.x_default }}" />
<link rel="stylesheet" href="{{ _asset_prefix }}styles.css" />
</head>
<body>

{{ _nav_block }}

<section class="hero">
  <div class="hero-bg" style="background-image:url('https://images.unsplash.com/photo-1527841430192-32adc8530984?auto=format&fit=crop&w=1800&q=80')"></div>
  <div class="wrap hero-grid">
    <div>
      <div class="eyebrow">{{ pages.home.hero.eyebrow }}</div>
      <h1>{{ pages.home.hero.title }}</h1>
      <p>{{ pages.home.hero.lead }}</p>
      <div class="hero-actions">
        <button class="btn-primary">{{ common.start_free_cta }}</button>
        <a href="{{ _nav.guidance_href }}" class="btn-ghost">{{ pages.home.hero.cta_ghost }}</a>
      </div>
    </div>
    <div class="orb-hero">
      <div class="orb-ring"></div>
      <div class="orb"></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="photo-band" style="background-image:url('https://images.unsplash.com/photo-1559586616-361e18714958?auto=format&fit=crop&w=1600&q=80')">
      <div class="photo-band-content">
        <div class="eyebrow">{{ pages.home.photo_rhythm.eyebrow }}</div>
        <p class="quote">{{ pages.home.photo_rhythm.quote }}</p>
        <div class="credit">{{ pages.home.photo_rhythm.credit }}</div>
      </div>
    </div>
  </div>
</section>

<section id="pratique">
  <div class="wrap">
    <div class="section-head">
      <div class="eyebrow">{{ pages.home.practice.eyebrow }}</div>
      <h2>{{ pages.home.practice.title }}</h2>
      <p>{{ pages.home.practice.lead }}</p>
    </div>
    <div class="features">
      <div class="feature-card">
        <div class="feature-icon">✦</div>
        <h3>{{ pages.home.practice.card1_title }}</h3>
        <p>{{ pages.home.practice.card1_body }}</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">〜</div>
        <h3>{{ pages.home.practice.card2_title }}</h3>
        <p>{{ pages.home.practice.card2_body }}</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">↝</div>
        <h3>{{ pages.home.practice.card3_title }}</h3>
        <p>{{ pages.home.practice.card3_body }}</p>
      </div>
    </div>
  </div>
</section>

<section id="guidance-teaser">
  <div class="wrap">
    <div class="section-head">
      <div class="eyebrow">{{ pages.home.guidance_teaser.eyebrow }}</div>
      <h2>{{ pages.home.guidance_teaser.title }}</h2>
      <p>{{ pages.home.guidance_teaser.lead }}</p>
    </div>
    {{ _hamann_bio_block }}
  </div>
</section>

<section id="ressources-teaser">
  <div class="wrap">
    <div class="section-head">
      <div class="eyebrow">{{ pages.home.resources_teaser.eyebrow }}</div>
      <h2>{{ pages.home.resources_teaser.title }}</h2>
      <p>{{ pages.home.resources_teaser.lead }}</p>
    </div>
    <div class="article-grid">
      <a class="article-card link" href="{{ _nav.article_href }}">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1622489968558-9bf6f30dcb2a?auto=format&fit=crop&w=800&q=80')"></div>
        <div class="body">
          <div class="tag">{{ pages.home.resources_teaser.featured_tag }}</div>
          <h3>{{ pages.home.resources_teaser.featured_title }}</h3>
          <p>{{ pages.home.resources_teaser.featured_desc }}</p>
          <div class="meta">{{ pages.home.resources_teaser.featured_meta }}</div>
        </div>
      </a>
      <div class="article-card soon">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1668689723080-c50f6e823de5?auto=format&fit=crop&w=800&q=80')"><span class="badge">{{ pages.home.resources_teaser.soon_badge }}</span></div>
        <div class="body">
          <div class="tag">{{ pages.home.resources_teaser.card2_tag }}</div>
          <h3>{{ pages.home.resources_teaser.card2_title }}</h3>
          <p>{{ pages.home.resources_teaser.card2_desc }}</p>
        </div>
      </div>
      <div class="article-card soon">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1689322366136-4740ee40d932?auto=format&fit=crop&w=800&q=80')"><span class="badge">{{ pages.home.resources_teaser.soon_badge }}</span></div>
        <div class="body">
          <div class="tag">{{ pages.home.resources_teaser.card3_tag }}</div>
          <h3>{{ pages.home.resources_teaser.card3_title }}</h3>
          <p>{{ pages.home.resources_teaser.card3_desc }}</p>
        </div>
      </div>
    </div>
    <div style="margin-top:28px; text-align:center;">
      <a href="{{ _nav.resources_href }}" class="btn-ghost">{{ pages.home.resources_teaser.see_all }}</a>
    </div>
  </div>
</section>

<section id="tarifs">
  <div class="wrap">
    <div class="section-head">
      <div class="eyebrow">{{ pages.home.pricing.eyebrow }}</div>
      <h2>{{ pages.home.pricing.title }}</h2>
    </div>
    <div class="pricing-grid">
      <div class="price-card">
        <div class="tier">{{ pages.home.pricing.free_tier }}</div>
        <div class="amount">{{ pages.home.pricing.free_amount }}</div>
        <ul>
          <li>{{ pages.home.pricing.free_item1 }}</li>
          <li>{{ pages.home.pricing.free_item2 }}</li>
          <li>{{ pages.home.pricing.free_item3 }}</li>
        </ul>
        <button class="btn-ghost">{{ pages.home.pricing.free_cta }}</button>
      </div>
      <div class="price-card highlight">
        <div class="tier">Vibr'Up+</div>
        <div class="amount">{{ pages.home.pricing.plus_amount }}</div>
        <ul>
          <li>{{ pages.home.pricing.plus_item1 }}</li>
          <li>{{ pages.home.pricing.plus_item2 }}</li>
          <li>{{ pages.home.pricing.plus_item3 }}</li>
          <li>{{ pages.home.pricing.plus_item4 }}</li>
        </ul>
        <button class="btn-primary">{{ pages.home.pricing.plus_cta }}</button>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="photo-band" style="background-image:url('https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?auto=format&fit=crop&w=1800&q=80')">
      <div class="photo-band-content">
        <div class="eyebrow">{{ pages.home.photo_earth.eyebrow }}</div>
        <p class="quote">{{ pages.home.photo_earth.quote }}</p>
        <div class="credit">{{ pages.home.photo_earth.credit }}</div>
      </div>
    </div>
  </div>
</section>

{{ _footer_block }}

{{ _whatsapp_block }}
<script src="{{ _asset_prefix }}script.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/pages/home.html
git commit -m "Add home page template"
```

---

## Task 7: Page template — about

**Files:**
- Create: `templates/pages/about.html`

- [ ] **Step 1: Write the template**

`templates/pages/about.html`:
```html
<!DOCTYPE html>
<html lang="{{ _lang_html }}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{{ pages.about.meta.title }}</title>
<meta name="description" content="{{ pages.about.meta.description }}" />
<link rel="alternate" hreflang="fr" href="{{ _hreflang.fr }}" />
<link rel="alternate" hreflang="en" href="{{ _hreflang.en }}" />
<link rel="alternate" hreflang="es" href="{{ _hreflang.es }}" />
<link rel="alternate" hreflang="x-default" href="{{ _hreflang.x_default }}" />
<link rel="stylesheet" href="{{ _asset_prefix }}styles.css" />
</head>
<body>

{{ _nav_block }}

<div class="wrap page-header">
  <div class="eyebrow">{{ pages.about.header.eyebrow }}</div>
  <h1>{{ pages.about.header.title }}</h1>
</div>

<section style="padding-top:20px;">
  <div class="wrap">
    <p class="about-lead">{{ pages.about.lead }}</p>
  </div>
</section>

<section style="padding-top:0;">
  <div class="wrap">
    <div class="photo-band" style="background-image:url('https://images.unsplash.com/photo-1550929834-9c4435d59a1f?auto=format&fit=crop&w=1800&q=80')">
      <div class="photo-band-content">
        <div class="eyebrow">{{ pages.about.photo.eyebrow }}</div>
        <p class="quote">{{ pages.about.photo.quote }}</p>
        <div class="credit">{{ pages.about.photo.credit }}</div>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="section-head">
      <div class="eyebrow">{{ pages.about.approach.eyebrow }}</div>
      <h2>{{ pages.about.approach.title }}</h2>
    </div>
    <div class="values-grid">
      <div class="value-card">
        <div class="num">01</div>
        <h3>{{ pages.about.value1.title }}</h3>
        <p>{{ pages.about.value1.body }}</p>
      </div>
      <div class="value-card">
        <div class="num">02</div>
        <h3>{{ pages.about.value2.title }}</h3>
        <p>{{ pages.about.value2.body }}</p>
      </div>
      <div class="value-card">
        <div class="num">03</div>
        <h3>{{ pages.about.value3.title }}</h3>
        <p>{{ pages.about.value3.body }}</p>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="section-head center">
      <div class="eyebrow">{{ pages.about.now.eyebrow }}</div>
      <h2>{{ pages.about.now.title }}</h2>
      <p>{{ pages.about.now.lead }}</p>
    </div>
    <div style="text-align:center;">
      <a href="index.html#pratique" class="btn-primary">{{ pages.about.now.cta }}</a>
    </div>
  </div>
</section>

{{ _footer_block }}

{{ _whatsapp_block }}
<script src="{{ _asset_prefix }}script.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/pages/about.html
git commit -m "Add about page template"
```

---

## Task 8: Page template — article

**Files:**
- Create: `templates/pages/article.html`

- [ ] **Step 1: Write the template**

`templates/pages/article.html`:
```html
<!DOCTYPE html>
<html lang="{{ _lang_html }}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{{ pages.article.meta.title }}</title>
<meta name="description" content="{{ pages.article.meta.description }}" />
<link rel="alternate" hreflang="fr" href="{{ _hreflang.fr }}" />
<link rel="alternate" hreflang="en" href="{{ _hreflang.en }}" />
<link rel="alternate" hreflang="es" href="{{ _hreflang.es }}" />
<link rel="alternate" hreflang="x-default" href="{{ _hreflang.x_default }}" />
<link rel="stylesheet" href="{{ _asset_prefix }}styles.css" />
</head>
<body>

{{ _nav_block }}

<div class="wrap article-header">
  <div class="eyebrow">{{ pages.article.header.tag }}</div>
  <h1>{{ pages.article.header.title }}</h1>
  <div class="meta-row">
    <span>{{ pages.article.header.author }}</span>
    <span>·</span>
    <span>{{ pages.article.header.read_time }}</span>
  </div>
</div>

<div class="wrap">
  <div class="article-hero-img" style="background-image:url('https://images.unsplash.com/photo-1622489968558-9bf6f30dcb2a?auto=format&fit=crop&w=1600&q=80')"></div>
</div>

<div class="article-body">
  <p>{{ pages.article.body.p1 }}</p>

  <p>{{ pages.article.body.p2 }}</p>

  <h2>{{ pages.article.section1.title }}</h2>
  <p>{{ pages.article.section1.p1 }}</p>
  <p>{{ pages.article.section1.p2 }}</p>

  <blockquote>{{ pages.article.quote }}</blockquote>

  <h2>{{ pages.article.section2.title }}</h2>
  <p>{{ pages.article.section2.lead }}</p>
  <ul>
    <li>{{ pages.article.section2.item1 }}</li>
    <li>{{ pages.article.section2.item2 }}</li>
    <li>{{ pages.article.section2.item3 }}</li>
  </ul>

  <h2>{{ pages.article.section3.title }}</h2>
  <p>{{ pages.article.section3.p1 }}</p>
  <p>{{ pages.article.section3.p2 }}</p>

  <h2>{{ pages.article.section4.title }}</h2>
  <ul>
    <li>{{ pages.article.section4.item1 }}</li>
    <li>{{ pages.article.section4.item2 }}</li>
    <li>{{ pages.article.section4.item3 }}</li>
    <li>{{ pages.article.section4.item4 }}</li>
  </ul>

  <p>{{ pages.article.closing }}</p>

  <div class="article-cta">
    <p>{{ pages.article.cta.lead }}</p>
    <a href="index.html#pratique" class="btn-primary">{{ pages.article.cta.button }}</a>
  </div>
</div>

{{ _footer_block }}

{{ _whatsapp_block }}
<script src="{{ _asset_prefix }}script.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/pages/article.html
git commit -m "Add article page template"
```

---

## Task 9: Page template — contact

**Files:**
- Create: `templates/pages/contact.html`

- [ ] **Step 1: Write the template**

`templates/pages/contact.html`:
```html
<!DOCTYPE html>
<html lang="{{ _lang_html }}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{{ pages.contact.meta.title }}</title>
<meta name="description" content="{{ pages.contact.meta.description }}" />
<link rel="alternate" hreflang="fr" href="{{ _hreflang.fr }}" />
<link rel="alternate" hreflang="en" href="{{ _hreflang.en }}" />
<link rel="alternate" hreflang="es" href="{{ _hreflang.es }}" />
<link rel="alternate" hreflang="x-default" href="{{ _hreflang.x_default }}" />
<link rel="stylesheet" href="{{ _asset_prefix }}styles.css" />
</head>
<body>

{{ _nav_block }}

<section>
  <div class="wrap">
    <div class="section-head center">
      <div class="eyebrow">{{ pages.contact.hero.eyebrow }}</div>
      <h2>{{ pages.contact.hero.title }}</h2>
      <p>{{ pages.contact.hero.lead }}</p>
    </div>

    <div class="contact-card">
      <form action="https://formspree.io/f/mgawyzjj" method="POST">
        <p class="contact-intro">{{ pages.contact.form.intro }}</p>

        <div class="field">
          <label for="ressenti">{{ pages.contact.form.feeling_label }}</label>
          <textarea id="ressenti" name="{{ pages.contact.form.feeling_field_name }}" rows="3" placeholder="{{ pages.contact.form.feeling_placeholder }}"></textarea>
        </div>

        <div class="field">
          <label for="ou-en-es-tu">{{ pages.contact.form.stage_label }}</label>
          <select id="ou-en-es-tu" name="{{ pages.contact.form.stage_field_name }}">
            <option value="">{{ pages.contact.form.stage_opt0 }}</option>
            <option>{{ pages.contact.form.stage_opt1 }}</option>
            <option>{{ pages.contact.form.stage_opt2 }}</option>
            <option>{{ pages.contact.form.stage_opt3 }}</option>
            <option>{{ pages.contact.form.stage_opt4 }}</option>
            <option>{{ pages.contact.form.stage_opt5 }}</option>
          </select>
        </div>

        <div class="field">
          <label for="message">{{ pages.contact.form.message_label }}</label>
          <textarea id="message" name="{{ pages.contact.form.message_field_name }}" rows="3" placeholder="{{ pages.contact.form.message_placeholder }}"></textarea>
        </div>

        <div class="row-2">
          <div class="field" style="margin-bottom:0;">
            <label for="prenom">{{ pages.contact.form.firstname_label }}</label>
            <input id="prenom" name="{{ pages.contact.form.firstname_field_name }}" type="text" placeholder="{{ pages.contact.form.firstname_placeholder }}" />
          </div>
          <div class="field" style="margin-bottom:0;">
            <label for="contact">{{ pages.contact.form.contact_label }}</label>
            <input id="contact" name="{{ pages.contact.form.contact_field_name }}" type="text" placeholder="{{ pages.contact.form.contact_placeholder }}" required />
          </div>
        </div>

        <button type="submit" class="btn-primary" style="width:100%; margin-top: 22px;">{{ pages.contact.form.submit }}</button>
        <p class="submit-note">{{ pages.contact.form.submit_note }}</p>
      </form>
    </div>
  </div>
</section>

{{ _footer_block }}

{{ _whatsapp_block }}
<script src="{{ _asset_prefix }}script.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/pages/contact.html
git commit -m "Add contact page template"
```

---

## Task 10: Page template — guidance

**Files:**
- Create: `templates/pages/guidance.html`

- [ ] **Step 1: Write the template**

`templates/pages/guidance.html`:
```html
<!DOCTYPE html>
<html lang="{{ _lang_html }}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{{ pages.guidance.meta.title }}</title>
<meta name="description" content="{{ pages.guidance.meta.description }}" />
<link rel="alternate" hreflang="fr" href="{{ _hreflang.fr }}" />
<link rel="alternate" hreflang="en" href="{{ _hreflang.en }}" />
<link rel="alternate" hreflang="es" href="{{ _hreflang.es }}" />
<link rel="alternate" hreflang="x-default" href="{{ _hreflang.x_default }}" />
<link rel="stylesheet" href="{{ _asset_prefix }}styles.css" />
</head>
<body>

{{ _nav_block }}

<div class="wrap page-header">
  <div class="eyebrow">{{ pages.guidance.header.eyebrow }}</div>
  <h1>{{ pages.guidance.header.title }}</h1>
  <p>{{ pages.guidance.header.lead }}</p>
</div>

<section>
  <div class="wrap">
    {{ _hamann_bio_block }}
  </div>
</section>

<section>
  <div class="wrap">
    <div class="photo-band" style="background-image:url('https://images.unsplash.com/photo-1769537145747-ff380b863f49?auto=format&fit=crop&w=1800&q=80')">
      <div class="photo-band-content">
        <div class="eyebrow">{{ pages.guidance.photo.eyebrow }}</div>
        <p class="quote">{{ pages.guidance.photo.quote }}</p>
        <div class="credit">{{ pages.guidance.photo.credit }}</div>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="section-head">
      <div class="eyebrow">{{ pages.guidance.how.eyebrow }}</div>
      <h2>{{ pages.guidance.how.title }}</h2>
    </div>
    <div class="values-grid">
      <div class="value-card">
        <div class="num">01</div>
        <h3>{{ pages.guidance.how.step1_title }}</h3>
        <p>{{ pages.guidance.how.step1_body }}</p>
      </div>
      <div class="value-card">
        <div class="num">02</div>
        <h3>{{ pages.guidance.how.step2_title }}</h3>
        <p>{{ pages.guidance.how.step2_body }}</p>
      </div>
      <div class="value-card">
        <div class="num">03</div>
        <h3>{{ pages.guidance.how.step3_title }}</h3>
        <p>{{ pages.guidance.how.step3_body }}</p>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="section-head">
      <div class="eyebrow">{{ pages.guidance.faq.eyebrow }}</div>
      <h2>{{ pages.guidance.faq.title }}</h2>
    </div>
    <div class="faq-item">
      <h3>{{ pages.guidance.faq.q1_title }}</h3>
      <p>{{ pages.guidance.faq.q1_body }}</p>
    </div>
    <div class="faq-item">
      <h3>{{ pages.guidance.faq.q2_title }}</h3>
      <p>{{ pages.guidance.faq.q2_body }}</p>
    </div>
    <div class="faq-item">
      <h3>{{ pages.guidance.faq.q3_title }}</h3>
      <p>{{ pages.guidance.faq.q3_body }}</p>
    </div>
    <div class="faq-item">
      <h3>{{ pages.guidance.faq.q4_title }}</h3>
      <p>{{ pages.guidance.faq.q4_body }}</p>
    </div>
  </div>
</section>

{{ _footer_block }}

{{ _whatsapp_block }}
<script src="{{ _asset_prefix }}script.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/pages/guidance.html
git commit -m "Add guidance page template"
```

---

## Task 11: Page template — resources

**Files:**
- Create: `templates/pages/resources.html`

- [ ] **Step 1: Write the template**

`templates/pages/resources.html`:
```html
<!DOCTYPE html>
<html lang="{{ _lang_html }}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{{ pages.resources.meta.title }}</title>
<meta name="description" content="{{ pages.resources.meta.description }}" />
<link rel="alternate" hreflang="fr" href="{{ _hreflang.fr }}" />
<link rel="alternate" hreflang="en" href="{{ _hreflang.en }}" />
<link rel="alternate" hreflang="es" href="{{ _hreflang.es }}" />
<link rel="alternate" hreflang="x-default" href="{{ _hreflang.x_default }}" />
<link rel="stylesheet" href="{{ _asset_prefix }}styles.css" />
</head>
<body>

{{ _nav_block }}

<section class="hero" style="padding-bottom:20px;">
  <div class="hero-bg" style="background-image:url('https://images.unsplash.com/photo-1550929834-9c4435d59a1f?auto=format&fit=crop&w=1800&q=80'); opacity:0.14;"></div>
  <div class="wrap page-header" style="padding-top:0;">
    <div class="eyebrow">{{ pages.resources.header.eyebrow }}</div>
    <h1>{{ pages.resources.header.title }}</h1>
    <p>{{ pages.resources.header.lead }}</p>
  </div>
</section>

<section style="padding-top:20px;">
  <div class="wrap">
    <div class="filters">
      <button class="filter-pill active" data-filter="toutes">{{ pages.resources.filters.all }}</button>
      <button class="filter-pill" data-filter="vibration">{{ pages.resources.filters.vibration }}</button>
      <button class="filter-pill" data-filter="meditations">{{ pages.resources.filters.meditations }}</button>
      <button class="filter-pill" data-filter="manifestation">{{ pages.resources.filters.manifestation }}</button>
      <button class="filter-pill" data-filter="ancrage">{{ pages.resources.filters.grounding }}</button>
      <button class="filter-pill" data-filter="cycles">{{ pages.resources.filters.cycles }}</button>
    </div>

    <div class="article-grid">
      <a class="article-card link" data-category="vibration" href="{{ _nav.article_href }}">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1622489968558-9bf6f30dcb2a?auto=format&fit=crop&w=800&q=80')"></div>
        <div class="body">
          <div class="tag">{{ pages.resources.featured.tag }}</div>
          <h3>{{ pages.resources.featured.title }}</h3>
          <p>{{ pages.resources.featured.desc }}</p>
          <div class="meta">{{ pages.resources.featured.meta }}</div>
        </div>
      </a>

      <div class="article-card soon" data-category="ancrage">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1668689723080-c50f6e823de5?auto=format&fit=crop&w=800&q=80')"><span class="badge">{{ pages.resources.soon_badge }}</span></div>
        <div class="body">
          <div class="tag">{{ pages.resources.article_grounding.tag }}</div>
          <h3>{{ pages.resources.article_grounding.title }}</h3>
          <p>{{ pages.resources.article_grounding.desc }}</p>
        </div>
      </div>

      <div class="article-card soon" data-category="manifestation">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1689322366136-4740ee40d932?auto=format&fit=crop&w=800&q=80')"><span class="badge">{{ pages.resources.soon_badge }}</span></div>
        <div class="body">
          <div class="tag">{{ pages.resources.article_manifestation.tag }}</div>
          <h3>{{ pages.resources.article_manifestation.title }}</h3>
          <p>{{ pages.resources.article_manifestation.desc }}</p>
        </div>
      </div>

      <div class="article-card soon" data-category="cycles">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1683138155815-d7edd806d8a3?auto=format&fit=crop&w=800&q=80')"><span class="badge">{{ pages.resources.soon_badge }}</span></div>
        <div class="body">
          <div class="tag">{{ pages.resources.article_cycles.tag }}</div>
          <h3>{{ pages.resources.article_cycles.title }}</h3>
          <p>{{ pages.resources.article_cycles.desc }}</p>
        </div>
      </div>

      <div class="article-card soon" data-category="meditations">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1762538190509-140fb21fea20?auto=format&fit=crop&w=800&q=80')"><span class="badge">{{ pages.resources.soon_badge }}</span></div>
        <div class="body">
          <div class="tag">{{ pages.resources.article_5min.tag }}</div>
          <h3>{{ pages.resources.article_5min.title }}</h3>
          <p>{{ pages.resources.article_5min.desc }}</p>
        </div>
      </div>

      <div class="article-card soon" data-category="vibration">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1762538190374-310cda4382dc?auto=format&fit=crop&w=800&q=80')"><span class="badge">{{ pages.resources.soon_badge }}</span></div>
        <div class="body">
          <div class="tag">{{ pages.resources.article_energy_drop.tag }}</div>
          <h3>{{ pages.resources.article_energy_drop.title }}</h3>
          <p>{{ pages.resources.article_energy_drop.desc }}</p>
        </div>
      </div>

      <div class="article-card soon" data-category="ancrage">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1769537145747-ff380b863f49?auto=format&fit=crop&w=800&q=80')"><span class="badge">{{ pages.resources.soon_badge }}</span></div>
        <div class="body">
          <div class="tag">{{ pages.resources.article_evening_ritual.tag }}</div>
          <h3>{{ pages.resources.article_evening_ritual.title }}</h3>
          <p>{{ pages.resources.article_evening_ritual.desc }}</p>
        </div>
      </div>

      <div class="article-card soon" data-category="manifestation">
        <div class="thumb" style="background-image:url('https://images.unsplash.com/photo-1516558500749-2f9096c53225?auto=format&fit=crop&w=800&q=80')"><span class="badge">{{ pages.resources.soon_badge }}</span></div>
        <div class="body">
          <div class="tag">{{ pages.resources.article_resonance.tag }}</div>
          <h3>{{ pages.resources.article_resonance.title }}</h3>
          <p>{{ pages.resources.article_resonance.desc }}</p>
        </div>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="newsletter">
      <div>
        <h3>{{ pages.resources.newsletter.title }}</h3>
        <p>{{ pages.resources.newsletter.lead }}</p>
      </div>
      <div>
        <form class="newsletter-form" onsubmit="return false;">
          <input type="email" placeholder="{{ pages.resources.newsletter.email_placeholder }}" required />
          <button type="submit" class="btn-primary">{{ pages.resources.newsletter.submit }}</button>
        </form>
        <div class="newsletter-note">{{ pages.resources.newsletter.note }}</div>
      </div>
    </div>
  </div>
</section>

{{ _footer_block }}

{{ _whatsapp_block }}
<script src="{{ _asset_prefix }}script.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/pages/resources.html
git commit -m "Add resources page template"
```

---

## Task 12: French translation strings (`i18n/fr.py`)

**Files:**
- Create: `i18n/fr.py`

- [ ] **Step 1: Write the file**

`i18n/fr.py`:
```python
"""French (source language) translation strings."""

STRINGS = {
    "nav": {
        "home": "Accueil",
        "resources": "Ressources",
        "guidance": "Guidance",
        "pricing": "Tarifs",
        "contact": "Contact",
    },
    "footer": {
        "about": "À propos",
        "legal": "Mentions légales",
        "terms": "CGV",
        "contact": "Contact",
        "copyright": "© 2026 Vibr'Up. Tous droits réservés.",
    },
    "common": {
        "start_free_cta": "Commencer gratuitement",
        "open_menu_aria": "Ouvrir le menu",
        "whatsapp_aria": "Contacter sur WhatsApp",
    },
    "person": {
        "hamann": {
            "tagline": "Retrouver votre énergie et enthousiasme par le simple retour à soi.",
            "bio1": "Spécialisé dans les troubles cognitifs et leurs répercussions sur les apprentissages, je partage ici une approche née de deux expériences d'unité avec le Tout — transmise intuitivement, autour de l'énergie, des sons, des vibrations, des fréquences et de l'impermanence qui composent notre voyage terrestre.",
            "bio2": "30 minutes rien que pour toi, pour explorer ton état énergétique en profondeur et repartir avec des pistes concrètes — par téléphone, en visio, ou sur WhatsApp, selon ce qui te met le plus à l'aise.",
            "channel_phone": "📞 Téléphone",
            "channel_video": "🎥 Visio",
            "price": "30€ · 30 minutes",
        },
    },
    "pages": {
        "home": {
            "meta": {
                "title": "Vibr'Up — élève ton énergie, jour après jour",
                "description": "Vibr'Up t'aide à observer, comprendre et élever ton état vibratoire — suivi quotidien, méditations guidées et guidance individuelle.",
            },
            "hero": {
                "eyebrow": "suivi vibratoire &amp; énergétique",
                "title": "Retrouve le fil de <em>ton</em> énergie, jour après jour.",
                "lead": "Vibr'Up t'aide à observer, comprendre et élever ton état vibratoire — avec un suivi quotidien, des méditations guidées, et un accompagnement personnalisé si tu en as besoin.",
                "cta_ghost": "Réserver une guidance",
            },
            "photo_rhythm": {
                "eyebrow": "le rythme avant la vitesse",
                "quote": "Comme une caravane qui avance dans le silence du désert, ton énergie suit son propre rythme — pas celui qu'on t'impose.",
                "credit": "Photo — désert du Sahara",
            },
            "practice": {
                "eyebrow": "la pratique",
                "title": "Trois gestes simples, chaque jour",
                "lead": "Pas besoin d'y passer une heure. Vibr'Up se glisse dans ta routine, quelques minutes suffisent pour observer et ajuster ton énergie.",
                "card1_title": "Check-in quotidien",
                "card1_body": "Note ton niveau vibratoire et ton ressenti du jour. Un geste simple qui, répété, révèle tes cycles d'énergie.",
                "card2_title": "Méditations guidées",
                "card2_body": "Ancrage, élévation vibratoire, alignement — des pratiques courtes pensées pour agir concrètement sur ton énergie.",
                "card3_title": "Évolution dans le temps",
                "card3_body": "Visualise tes tendances sur la durée pour identifier ce qui nourrit — ou draine — ton énergie.",
            },
            "guidance_teaser": {
                "eyebrow": "accompagnement",
                "title": "Une guidance individuelle, en direct",
                "lead": "Quand le check-in ne suffit plus, échange 30 minutes avec Hamann pour explorer ton état énergétique en profondeur.",
                "cta": "Découvrir la guidance",
            },
            "resources_teaser": {
                "eyebrow": "ressources",
                "title": "De quoi nourrir ta pratique",
                "lead": "Articles, affirmations et pistes de réflexion pour approfondir ton chemin, à ton rythme.",
                "featured_tag": "Vibration",
                "featured_title": "Les affirmations positives : comment et pourquoi les utiliser",
                "featured_desc": "Un guide simple pour reprogrammer ton dialogue intérieur, sans injonction ni pression.",
                "featured_meta": "7 min de lecture",
                "soon_badge": "Bientôt",
                "card2_tag": "Méditations",
                "card2_title": "L'ancrage : la première pierre de toute pratique énergétique",
                "card2_desc": "Pourquoi se reconnecter au sol est souvent l'étape la plus négligée — et la plus puissante.",
                "card3_tag": "Manifestation",
                "card3_title": "Manifester sans forcer : la nuance qui change tout",
                "card3_desc": "La différence entre désirer avec intensité et désirer avec tension — et pourquoi elle compte.",
                "see_all": "Voir toutes les ressources",
            },
            "pricing": {
                "eyebrow": "tarifs",
                "title": "Commence gratuitement, va plus loin quand tu es prêt·e",
                "free_tier": "Gratuit",
                "free_amount": "0€",
                "free_item1": "Check-in quotidien illimité",
                "free_item2": "7 derniers jours d'historique",
                "free_item3": "1 méditation guidée (Ancrage)",
                "free_cta": "Commencer",
                "plus_amount": "5€ <span>/ mois</span>",
                "plus_item1": "Tout le contenu gratuit",
                "plus_item2": "Historique et tendances illimités",
                "plus_item3": "Toutes les méditations guidées",
                "plus_item4": "Accès prioritaire aux nouveautés",
                "plus_cta": "S'abonner",
            },
            "photo_earth": {
                "eyebrow": "où que tu sois sur cette terre",
                "quote": "Ton énergie n'a pas de frontière. Où que tu commences aujourd'hui, Vibr'Up t'accompagne.",
                "credit": "Photo — la Terre vue de l'espace",
            },
        },
        "about": {
            "meta": {
                "title": "À propos — Vibr'Up",
                "description": "Pourquoi Vibr'Up existe : une philosophie du retour à soi, sans injonction ni dogme.",
            },
            "header": {
                "eyebrow": "à propos",
                "title": "Pourquoi Vibr'Up existe",
            },
            "lead": "On ne t'a jamais vraiment appris à écouter ton énergie — seulement à la subir, à l'ignorer, ou à la pousser plus loin qu'elle ne peut aller. Vibr'Up est né de l'idée simple qu'observer suffit souvent à changer les choses.",
            "photo": {
                "eyebrow": "une dune à la fois",
                "quote": "On n'élève pas son énergie d'un coup. On avance dune après dune, jour après jour.",
                "credit": "Photo — dunes du Sahara",
            },
            "approach": {
                "eyebrow": "notre approche",
                "title": "Trois convictions qui guident Vibr'Up",
            },
            "value1": {
                "title": "Observer avant de changer",
                "body": "On ne peut pas ajuster ce qu'on ne regarde pas. Le check-in quotidien n'est pas une performance à réussir, juste un miroir honnête.",
            },
            "value2": {
                "title": "La régularité plutôt que l'intensité",
                "body": "Trois minutes chaque jour transforment plus durablement qu'une heure une fois par mois. Vibr'Up est pensé pour tenir dans le temps.",
            },
            "value3": {
                "title": "Un accompagnement sans dogme",
                "body": "Pas de vérité unique à suivre. Des outils, des pistes, et un accompagnement humain pour celles et ceux qui veulent aller plus loin.",
            },
            "now": {
                "eyebrow": "et maintenant ?",
                "title": "Commence là où tu es, aujourd'hui",
                "lead": "Pas besoin d'être prêt·e ou certain·e de quoi que ce soit. Un premier check-in suffit pour démarrer.",
                "cta": "Découvrir la pratique",
            },
        },
        "article": {
            "meta": {
                "title": "Les affirmations positives : comment et pourquoi les utiliser — Vibr'Up",
                "description": "Un guide simple pour utiliser les affirmations positives sans injonction ni pression, et les intégrer à ta pratique vibratoire quotidienne.",
            },
            "header": {
                "tag": "Vibration",
                "title": "Les affirmations positives : comment et pourquoi les utiliser",
                "author": "Équipe Vibr'Up",
                "read_time": "7 min de lecture",
            },
            "body": {
                "p1": "Tu as sûrement déjà croisé une affirmation positive quelque part — une phrase courte, écrite au présent, censée transformer ta journée rien qu'en la répétant. Beaucoup de gens les essaient une fois, n'y croient qu'à moitié, et abandonnent. Ce n'est pas qu'elles ne fonctionnent pas : c'est souvent qu'on les utilise sans comprendre ce qu'elles font vraiment.",
                "p2": "Une affirmation n'est pas une formule magique. C'est un outil de reprogrammation douce, qui agit sur la manière dont tu te parles à toi-même — et donc, avec le temps, sur ton état vibratoire général.",
            },
            "section1": {
                "title": "Pourquoi le dialogue intérieur compte autant",
                "p1": "La plupart des pensées que tu as chaque jour sont automatiques. Elles se répètent, souvent sans que tu les choisisses consciemment. Si ce dialogue intérieur penche naturellement vers le doute ou l'autocritique, il finit par devenir le bruit de fond de ton énergie — celui qui te tire vers le bas avant même que la journée ait commencé.",
                "p2": "Les affirmations positives ne cherchent pas à faire taire ce bruit de force. Elles proposent une autre voix, plus posée, que tu répètes volontairement jusqu'à ce qu'elle devienne, elle aussi, familière.",
            },
            "quote": "Une affirmation répétée sans conviction reste une phrase. Répétée avec attention, elle devient une habitude de pensée.",
            "section2": {
                "title": "Comment formuler une affirmation qui te correspond",
                "lead": "Trois principes simples suffisent pour commencer :",
                "item1": "<strong>Le présent, toujours.</strong> \"Je suis en paix\" plutôt que \"je serai en paix\" — ton esprit répond mieux à l'instant présent qu'à une promesse lointaine.",
                "item2": "<strong>Une formulation qui reste crédible pour toi.</strong> Si \"je suis riche\" te semble trop loin de ta réalité, commence par \"j'apprends à accueillir l'abondance\" — la formulation doit t'accompagner, pas te confronter.",
                "item3": "<strong>Une intention précise plutôt qu'un vœu vague.</strong> \"Je respire calmement dans les moments de tension\" agit plus concrètement que \"je suis zen\".",
            },
            "section3": {
                "title": "Les intégrer sans que ça devienne une contrainte de plus",
                "p1": "Inutile d'ajouter un rituel de vingt minutes à une journée déjà pleine. Les affirmations fonctionnent mieux glissées dans des moments qui existent déjà : au réveil, avant d'ouvrir les yeux complètement ; pendant le café du matin ; ou juste avant de dormir, quand l'esprit est plus réceptif.",
                "p2": "C'est exactement l'esprit du check-in quotidien Vibr'Up : un geste bref, répété, qui n'exige rien de plus que quelques minutes d'attention sincère.",
            },
            "section4": {
                "title": "Quelques exemples pour démarrer",
                "item1": "« Je m'autorise à avancer à mon rythme. »",
                "item2": "« Mon énergie m'appartient, je choisis où je la place. »",
                "item3": "« Je peux ressentir du calme, même dans l'incertitude. »",
                "item4": "« Chaque jour, j'apprends un peu mieux à m'écouter. »",
            },
            "closing": "Choisis-en une seule pour commencer. Répète-la une semaine entière avant d'en changer. La régularité compte bien plus que la quantité.",
            "cta": {
                "lead": "Envie de suivre l'effet de ta pratique jour après jour ?",
                "button": "Découvrir le check-in Vibr'Up",
            },
        },
        "contact": {
            "meta": {
                "title": "Contact — Vibr'Up",
                "description": "Où en es-tu aujourd'hui ? Écris-nous quelques mots, à ton rythme.",
            },
            "hero": {
                "eyebrow": "échanger",
                "title": "Où en es-tu, aujourd'hui ?",
                "lead": "Pas besoin de tout expliquer. Quelques mots suffisent pour démarrer un échange, à ton rythme.",
            },
            "form": {
                "intro": "Ce formulaire n'a rien d'un questionnaire. Réponds seulement à ce qui te parle — tout est facultatif sauf un moyen de te recontacter.",
                "feeling_label": "Comment te sens-tu en ce moment ?",
                "feeling_field_name": "Ressenti actuel",
                "feeling_placeholder": "En quelques mots, ce qui est présent pour toi aujourd'hui…",
                "stage_label": "Où en es-tu dans ton cheminement ?",
                "stage_field_name": "Où en es-tu",
                "stage_opt0": "Préfère ne pas préciser",
                "stage_opt1": "Je découvre, tout juste",
                "stage_opt2": "Je cherche à comprendre ce qui se passe en moi",
                "stage_opt3": "Je suis en pleine transition",
                "stage_opt4": "Je veux simplement approfondir une pratique",
                "stage_opt5": "Je souhaite réserver une guidance",
                "message_label": "Un mot de plus, si tu en as besoin (facultatif)",
                "message_field_name": "Message",
                "message_placeholder": "Ce que tu as envie de partager, sans obligation…",
                "firstname_label": "Ton prénom",
                "firstname_field_name": "Prénom",
                "firstname_placeholder": "Facultatif",
                "contact_label": "Comment te recontacter ?",
                "contact_field_name": "Coordonnées",
                "contact_placeholder": "Email, téléphone ou WhatsApp",
                "submit": "Envoyer, en douceur",
                "submit_note": "Ce que tu écris ici reste entre nous.",
            },
        },
        "guidance": {
            "meta": {
                "title": "Guidance individuelle avec Hamann — Vibr'Up",
                "description": "30 minutes de guidance individuelle avec Hamann pour explorer ton état énergétique en profondeur — téléphone, visio ou WhatsApp.",
            },
            "header": {
                "eyebrow": "accompagnement",
                "title": "Une guidance individuelle, en direct",
                "lead": "Quand observer ton énergie seul·e ne suffit plus, 30 minutes avec Hamann pour explorer ce qui se joue en profondeur — et repartir avec des pistes concrètes.",
            },
            "photo": {
                "eyebrow": "un accompagnement, pas une prescription",
                "quote": "Il ne s'agit pas de te donner des réponses toutes faites, mais de t'aider à entendre celles que tu portes déjà.",
                "credit": "Photo — dunes du Sahara au crépuscule",
            },
            "how": {
                "eyebrow": "déroulé",
                "title": "Comment se passe une séance",
                "step1_title": "Tu prends contact",
                "step1_body": "Via le formulaire de contact, en quelques mots sur ce qui t'amène. Rien d'obligatoire, juste un point de départ.",
                "step2_title": "On choisit le format",
                "step2_body": "Téléphone, visio ou WhatsApp — selon ce qui te met le plus à l'aise, à l'heure qui vous convient à tous les deux.",
                "step3_title": "Tu repars avec des pistes",
                "step3_body": "Pas de discours tout fait : des observations et des pistes concrètes à explorer, à ton rythme.",
            },
            "faq": {
                "eyebrow": "questions fréquentes",
                "title": "Avant de réserver",
                "q1_title": "Est-ce que je dois déjà utiliser Vibr'Up pour réserver une guidance ?",
                "q1_body": "Non. La guidance est ouverte à tout le monde, que tu utilises l'application ou non.",
                "q2_title": "Comment se passe le paiement ?",
                "q2_body": "Les modalités te seront précisées directement par Hamann après ta prise de contact.",
                "q3_title": "Et si je ne sais pas quoi dire au début ?",
                "q3_body": "C'est très courant, et ce n'est pas un problème. La séance est justement pensée pour t'aider à y voir plus clair, pas l'inverse.",
                "q4_title": "Puis-je reprogrammer si besoin ?",
                "q4_body": "Oui, il suffit d'en faire la demande par le formulaire de contact, le plus tôt possible.",
            },
            "cta": "Réserver ma séance",
        },
        "resources": {
            "meta": {
                "title": "Ressources — Vibr'Up",
                "description": "Articles, affirmations et pistes de réflexion pour nourrir ta pratique vibratoire, à ton rythme.",
            },
            "header": {
                "eyebrow": "ressources",
                "title": "Un espace pour nourrir ta pratique",
                "lead": "Articles, affirmations et pistes de réflexion sur la vibration, l'ancrage et le retour à soi — écrits simplement, sans jargon.",
            },
            "filters": {
                "all": "Toutes",
                "vibration": "Vibration",
                "meditations": "Méditations",
                "manifestation": "Manifestation",
                "grounding": "Ancrage",
                "cycles": "Cycles énergétiques",
            },
            "featured": {
                "tag": "Vibration",
                "title": "Les affirmations positives : comment et pourquoi les utiliser",
                "desc": "Un guide simple pour reprogrammer ton dialogue intérieur, sans injonction ni pression.",
                "meta": "7 min de lecture",
            },
            "soon_badge": "Bientôt disponible",
            "article_grounding": {
                "tag": "Ancrage",
                "title": "L'ancrage : la première pierre de toute pratique énergétique",
                "desc": "Pourquoi se reconnecter au sol est souvent l'étape la plus négligée — et la plus puissante.",
            },
            "article_manifestation": {
                "tag": "Manifestation",
                "title": "Manifester sans forcer : la nuance qui change tout",
                "desc": "La différence entre désirer avec intensité et désirer avec tension — et pourquoi elle compte.",
            },
            "article_cycles": {
                "tag": "Cycles énergétiques",
                "title": "Comprendre tes cycles énergétiques sur un mois",
                "desc": "Ce que ton historique de check-in peut révéler quand tu prends le temps de le relire.",
            },
            "article_5min": {
                "tag": "Méditations",
                "title": "5 minutes pour recentrer ta journée",
                "desc": "Une pratique courte à glisser entre deux rendez-vous, quand tout s'accélère autour de toi.",
            },
            "article_energy_drop": {
                "tag": "Vibration",
                "title": "Pourquoi ton énergie baisse en fin de journée",
                "desc": "Trois causes fréquentes de fatigue vibratoire, et comment commencer à les repérer.",
            },
            "article_evening_ritual": {
                "tag": "Ancrage",
                "title": "Créer un rituel du soir simple et durable",
                "desc": "Pas besoin de bougies ni de trente minutes : trois gestes suffisent pour clore la journée.",
            },
            "article_resonance": {
                "tag": "Manifestation",
                "title": "La loi de résonance, expliquée simplement",
                "desc": "Une manière plus douce et plus juste de comprendre ce qu'on appelle parfois \"loi d'attraction\".",
            },
            "newsletter": {
                "title": "20 affirmations pour élever ta vibration",
                "lead": "Un guide gratuit à recevoir par email, à lire quand tu en as besoin — sans engagement, sans spam.",
                "email_placeholder": "Ton adresse email",
                "submit": "Recevoir le guide",
                "note": "Un email de temps en temps, jamais plus.",
            },
        },
    },
}
```

- [ ] **Step 2: Sanity-check the file parses**

Run: `python3 -c "import sys; sys.path.insert(0, '.'); import i18n.fr; print(len(str(i18n.fr.STRINGS)))"`
Expected: prints a character count (no `SyntaxError`/`IndentationError`).

- [ ] **Step 3: Commit**

```bash
git add i18n/fr.py
git commit -m "Add French translation strings"
```

---

## Task 13: English translation strings (`i18n/en.py`)

**Files:**
- Create: `i18n/en.py`

- [ ] **Step 1: Write the file**

`i18n/en.py` — same key structure as `i18n/fr.py` (Task 12), English values:
```python
"""English translation strings. Same key structure as i18n/fr.py."""

STRINGS = {
    "nav": {
        "home": "Home",
        "resources": "Resources",
        "guidance": "Guidance",
        "pricing": "Pricing",
        "contact": "Contact",
    },
    "footer": {
        "about": "About",
        "legal": "Legal notice",
        "terms": "Terms",
        "contact": "Contact",
        "copyright": "© 2026 Vibr'Up. All rights reserved.",
    },
    "common": {
        "start_free_cta": "Start for free",
        "open_menu_aria": "Open menu",
        "whatsapp_aria": "Contact on WhatsApp",
    },
    "person": {
        "hamann": {
            "tagline": "Rediscover your energy and enthusiasm through a simple return to yourself.",
            "bio1": "Specialized in cognitive difficulties and their impact on learning, I share here an approach born from two experiences of oneness with the Whole — passed on intuitively, around energy, sound, vibration, frequency, and the impermanence that shapes our earthly journey.",
            "bio2": "30 minutes just for you, to explore your energetic state in depth and walk away with concrete leads — by phone, video call, or WhatsApp, whichever puts you most at ease.",
            "channel_phone": "📞 Phone",
            "channel_video": "🎥 Video call",
            "price": "€30 · 30 minutes",
        },
    },
    "pages": {
        "home": {
            "meta": {
                "title": "Vibr'Up — raise your energy, day after day",
                "description": "Vibr'Up helps you observe, understand and raise your vibrational state — daily check-ins, guided meditations and one-on-one guidance.",
            },
            "hero": {
                "eyebrow": "vibrational &amp; energetic tracking",
                "title": "Find the thread of <em>your</em> energy, day after day.",
                "lead": "Vibr'Up helps you observe, understand and raise your vibrational state — with daily check-ins, guided meditations, and personalized guidance whenever you need it.",
                "cta_ghost": "Book a guidance session",
            },
            "photo_rhythm": {
                "eyebrow": "rhythm before speed",
                "quote": "Like a caravan moving through the silence of the desert, your energy follows its own rhythm — not the one imposed on you.",
                "credit": "Photo — Sahara desert",
            },
            "practice": {
                "eyebrow": "the practice",
                "title": "Three simple gestures, every day",
                "lead": "No need to spend an hour on it. Vibr'Up fits into your routine — a few minutes are enough to observe and adjust your energy.",
                "card1_title": "Daily check-in",
                "card1_body": "Note your vibrational level and how you feel today. A simple gesture that, repeated, reveals your energy cycles.",
                "card2_title": "Guided meditations",
                "card2_body": "Grounding, vibrational elevation, alignment — short practices designed to act concretely on your energy.",
                "card3_title": "Evolution over time",
                "card3_body": "Visualize your trends over time to identify what nourishes — or drains — your energy.",
            },
            "guidance_teaser": {
                "eyebrow": "guidance",
                "title": "One-on-one guidance, live",
                "lead": "When the check-in isn't enough anymore, spend 30 minutes with Hamann to explore your energetic state in depth.",
                "cta": "Discover guidance",
            },
            "resources_teaser": {
                "eyebrow": "resources",
                "title": "Food for your practice",
                "lead": "Articles, affirmations and food for thought to deepen your path, at your own pace.",
                "featured_tag": "Vibration",
                "featured_title": "Positive affirmations: how and why to use them",
                "featured_desc": "A simple guide to reprogramming your inner dialogue, without pressure or forced positivity.",
                "featured_meta": "7 min read",
                "soon_badge": "Coming soon",
                "card2_tag": "Meditations",
                "card2_title": "Grounding: the first stone of any energetic practice",
                "card2_desc": "Why reconnecting with the ground is often the most overlooked — and most powerful — step.",
                "card3_tag": "Manifestation",
                "card3_title": "Manifesting without forcing: the nuance that changes everything",
                "card3_desc": "The difference between desiring with intensity and desiring with tension — and why it matters.",
                "see_all": "See all resources",
            },
            "pricing": {
                "eyebrow": "pricing",
                "title": "Start for free, go further when you're ready",
                "free_tier": "Free",
                "free_amount": "€0",
                "free_item1": "Unlimited daily check-in",
                "free_item2": "Last 7 days of history",
                "free_item3": "1 guided meditation (Grounding)",
                "free_cta": "Get started",
                "plus_amount": "€5 <span>/ month</span>",
                "plus_item1": "All free content",
                "plus_item2": "Unlimited history and trends",
                "plus_item3": "All guided meditations",
                "plus_item4": "Priority access to new features",
                "plus_cta": "Subscribe",
            },
            "photo_earth": {
                "eyebrow": "wherever you are on this earth",
                "quote": "Your energy has no borders. Wherever you start today, Vibr'Up is with you.",
                "credit": "Photo — Earth seen from space",
            },
        },
        "about": {
            "meta": {
                "title": "About — Vibr'Up",
                "description": "Why Vibr'Up exists: a philosophy of returning to yourself, without injunctions or dogma.",
            },
            "header": {
                "eyebrow": "about",
                "title": "Why Vibr'Up exists",
            },
            "lead": "No one ever really taught you to listen to your energy — only to endure it, ignore it, or push it further than it can go. Vibr'Up was born from the simple idea that observing is often enough to change things.",
            "photo": {
                "eyebrow": "one dune at a time",
                "quote": "You don't raise your energy all at once. You move forward dune after dune, day after day.",
                "credit": "Photo — Sahara dunes",
            },
            "approach": {
                "eyebrow": "our approach",
                "title": "Three convictions that guide Vibr'Up",
            },
            "value1": {
                "title": "Observe before changing",
                "body": "You can't adjust what you don't look at. The daily check-in isn't a performance to nail, just an honest mirror.",
            },
            "value2": {
                "title": "Consistency over intensity",
                "body": "Three minutes every day transform more durably than one hour once a month. Vibr'Up is built to last over time.",
            },
            "value3": {
                "title": "Guidance without dogma",
                "body": "No single truth to follow. Tools, leads, and human guidance for those who want to go further.",
            },
            "now": {
                "eyebrow": "now what?",
                "title": "Start where you are, today",
                "lead": "No need to be ready or certain of anything. One first check-in is enough to get started.",
                "cta": "Discover the practice",
            },
        },
        "article": {
            "meta": {
                "title": "Positive affirmations: how and why to use them — Vibr'Up",
                "description": "A simple guide to using positive affirmations without pressure or forced positivity, and weaving them into your daily vibrational practice.",
            },
            "header": {
                "tag": "Vibration",
                "title": "Positive affirmations: how and why to use them",
                "author": "The Vibr'Up team",
                "read_time": "7 min read",
            },
            "body": {
                "p1": "You've probably come across a positive affirmation somewhere before — a short phrase, written in the present tense, supposed to transform your day just by repeating it. Many people try it once, half-believe it, and give up. It's not that affirmations don't work: it's often that we use them without understanding what they actually do.",
                "p2": "An affirmation isn't a magic formula. It's a tool for gentle reprogramming, one that shapes how you talk to yourself — and, over time, your overall vibrational state.",
            },
            "section1": {
                "title": "Why your inner dialogue matters so much",
                "p1": "Most of the thoughts you have each day are automatic. They repeat themselves, often without you consciously choosing them. If that inner dialogue naturally leans toward doubt or self-criticism, it ends up becoming the background noise of your energy — the one pulling you down before the day has even begun.",
                "p2": "Positive affirmations don't try to silence that noise by force. They offer another voice, calmer, that you repeat on purpose until it, too, becomes familiar.",
            },
            "quote": "An affirmation repeated without conviction stays a sentence. Repeated with attention, it becomes a habit of thought.",
            "section2": {
                "title": "How to phrase an affirmation that fits you",
                "lead": "Three simple principles are enough to get started:",
                "item1": "<strong>Always the present tense.</strong> \"I am at peace\" rather than \"I will be at peace\" — your mind responds better to the present moment than to a distant promise.",
                "item2": "<strong>A phrasing that stays believable to you.</strong> If \"I am wealthy\" feels too far from your reality, start with \"I am learning to welcome abundance\" — the phrasing should walk with you, not confront you.",
                "item3": "<strong>A precise intention rather than a vague wish.</strong> \"I breathe calmly in moments of tension\" works more concretely than \"I am zen.\"",
            },
            "section3": {
                "title": "Weaving them in without adding one more chore",
                "p1": "No need to add a twenty-minute ritual to an already full day. Affirmations work best slipped into moments that already exist: waking up, before fully opening your eyes; over morning coffee; or right before sleep, when the mind is more receptive.",
                "p2": "That's exactly the spirit of the daily Vibr'Up check-in: a brief, repeated gesture that asks for nothing more than a few minutes of sincere attention.",
            },
            "section4": {
                "title": "A few examples to get started",
                "item1": "\"I allow myself to move forward at my own pace.\"",
                "item2": "\"My energy belongs to me — I choose where I place it.\"",
                "item3": "\"I can feel calm, even in uncertainty.\"",
                "item4": "\"Every day, I learn a little better how to listen to myself.\"",
            },
            "closing": "Choose just one to start with. Repeat it for a full week before switching. Consistency matters far more than quantity.",
            "cta": {
                "lead": "Want to track the effect of your practice, day after day?",
                "button": "Discover the Vibr'Up check-in",
            },
        },
        "contact": {
            "meta": {
                "title": "Contact — Vibr'Up",
                "description": "Where are you today? Write us a few words, at your own pace.",
            },
            "hero": {
                "eyebrow": "let's talk",
                "title": "Where are you today?",
                "lead": "No need to explain everything. A few words are enough to start a conversation, at your own pace.",
            },
            "form": {
                "intro": "This form isn't a questionnaire. Answer only what speaks to you — everything is optional except a way to reach you back.",
                "feeling_label": "How are you feeling right now?",
                "feeling_field_name": "Current feeling",
                "feeling_placeholder": "In a few words, what's present for you today…",
                "stage_label": "Where are you in your journey?",
                "stage_field_name": "Where are you",
                "stage_opt0": "Prefer not to say",
                "stage_opt1": "I'm just discovering this",
                "stage_opt2": "I'm trying to understand what's going on inside me",
                "stage_opt3": "I'm going through a big transition",
                "stage_opt4": "I just want to deepen a practice",
                "stage_opt5": "I'd like to book a guidance session",
                "message_label": "One more thing, if you need to (optional)",
                "message_field_name": "Message",
                "message_placeholder": "Whatever you feel like sharing, no pressure…",
                "firstname_label": "Your first name",
                "firstname_field_name": "First name",
                "firstname_placeholder": "Optional",
                "contact_label": "How can we reach you?",
                "contact_field_name": "Contact details",
                "contact_placeholder": "Email, phone, or WhatsApp",
                "submit": "Send, gently",
                "submit_note": "What you write here stays between us.",
            },
        },
        "guidance": {
            "meta": {
                "title": "One-on-one guidance with Hamann — Vibr'Up",
                "description": "30 minutes of one-on-one guidance with Hamann to explore your energetic state in depth — phone, video call or WhatsApp.",
            },
            "header": {
                "eyebrow": "guidance",
                "title": "One-on-one guidance, live",
                "lead": "When observing your energy alone isn't enough anymore, spend 30 minutes with Hamann to explore what's really going on — and walk away with concrete leads.",
            },
            "photo": {
                "eyebrow": "guidance, not a prescription",
                "quote": "It's not about giving you ready-made answers, but helping you hear the ones you already carry.",
                "credit": "Photo — Sahara dunes at dusk",
            },
            "how": {
                "eyebrow": "how it works",
                "title": "What a session looks like",
                "step1_title": "You get in touch",
                "step1_body": "Via the contact form, with a few words about what brings you here. Nothing is required — it's just a starting point.",
                "step2_title": "You choose the format",
                "step2_body": "Phone, video call, or WhatsApp — whichever puts you most at ease, at a time that works for both of you.",
                "step3_title": "You leave with leads",
                "step3_body": "No pre-packaged speech: real observations and concrete leads to explore, at your own pace.",
            },
            "faq": {
                "eyebrow": "frequently asked questions",
                "title": "Before you book",
                "q1_title": "Do I need to already use Vibr'Up to book a guidance session?",
                "q1_body": "No. Guidance is open to everyone, whether or not you use the app.",
                "q2_title": "How does payment work?",
                "q2_body": "The details will be shared directly by Hamann once you've made contact.",
                "q3_title": "What if I don't know what to say at first?",
                "q3_body": "That's very common, and it's not a problem. The session is designed precisely to help you see things more clearly — not the other way around.",
                "q4_title": "Can I reschedule if needed?",
                "q4_body": "Yes, just make the request through the contact form as early as possible.",
            },
            "cta": "Book my session",
        },
        "resources": {
            "meta": {
                "title": "Resources — Vibr'Up",
                "description": "Articles, affirmations and food for thought to nourish your vibrational practice, at your own pace.",
            },
            "header": {
                "eyebrow": "resources",
                "title": "A space to nourish your practice",
                "lead": "Articles, affirmations and food for thought on vibration, grounding and returning to yourself — written simply, without jargon.",
            },
            "filters": {
                "all": "All",
                "vibration": "Vibration",
                "meditations": "Meditations",
                "manifestation": "Manifestation",
                "grounding": "Grounding",
                "cycles": "Energy cycles",
            },
            "featured": {
                "tag": "Vibration",
                "title": "Positive affirmations: how and why to use them",
                "desc": "A simple guide to reprogramming your inner dialogue, without pressure or forced positivity.",
                "meta": "7 min read",
            },
            "soon_badge": "Coming soon",
            "article_grounding": {
                "tag": "Grounding",
                "title": "Grounding: the first stone of any energetic practice",
                "desc": "Why reconnecting with the ground is often the most overlooked — and most powerful — step.",
            },
            "article_manifestation": {
                "tag": "Manifestation",
                "title": "Manifesting without forcing: the nuance that changes everything",
                "desc": "The difference between desiring with intensity and desiring with tension — and why it matters.",
            },
            "article_cycles": {
                "tag": "Energy cycles",
                "title": "Understanding your energy cycles over a month",
                "desc": "What your check-in history can reveal when you take the time to look back at it.",
            },
            "article_5min": {
                "tag": "Meditations",
                "title": "5 minutes to recenter your day",
                "desc": "A short practice to slip between two meetings, when everything around you speeds up.",
            },
            "article_energy_drop": {
                "tag": "Vibration",
                "title": "Why your energy drops by the end of the day",
                "desc": "Three common causes of vibrational fatigue, and how to start spotting them.",
            },
            "article_evening_ritual": {
                "tag": "Grounding",
                "title": "Creating a simple, lasting evening ritual",
                "desc": "No need for candles or thirty minutes: three gestures are enough to close the day.",
            },
            "article_resonance": {
                "tag": "Manifestation",
                "title": "The law of resonance, explained simply",
                "desc": "A gentler and more accurate way to understand what's sometimes called the \"law of attraction.\"",
            },
            "newsletter": {
                "title": "20 affirmations to raise your vibration",
                "lead": "A free guide delivered by email, to read whenever you need it — no commitment, no spam.",
                "email_placeholder": "Your email address",
                "submit": "Get the guide",
                "note": "One email now and then, never more.",
            },
        },
    },
}
```

- [ ] **Step 2: Sanity-check the file parses**

Run: `python3 -c "import sys; sys.path.insert(0, '.'); import i18n.en; print(len(str(i18n.en.STRINGS)))"`
Expected: prints a character count.

- [ ] **Step 3: Commit**

```bash
git add i18n/en.py
git commit -m "Add English translation strings"
```

---

## Task 14: Spanish translation strings (`i18n/es.py`)

**Files:**
- Create: `i18n/es.py`

- [ ] **Step 1: Write the file**

`i18n/es.py` — same key structure as `i18n/fr.py` (Task 12), Spanish values:
```python
"""Spanish translation strings. Same key structure as i18n/fr.py."""

STRINGS = {
    "nav": {
        "home": "Inicio",
        "resources": "Recursos",
        "guidance": "Guidance",
        "pricing": "Precios",
        "contact": "Contacto",
    },
    "footer": {
        "about": "Acerca de",
        "legal": "Aviso legal",
        "terms": "Condiciones",
        "contact": "Contacto",
        "copyright": "© 2026 Vibr'Up. Todos los derechos reservados.",
    },
    "common": {
        "start_free_cta": "Empezar gratis",
        "open_menu_aria": "Abrir el menú",
        "whatsapp_aria": "Contactar por WhatsApp",
    },
    "person": {
        "hamann": {
            "tagline": "Recuperar tu energía y entusiasmo a través del simple regreso a ti mismo.",
            "bio1": "Especializado en dificultades cognitivas y su impacto en el aprendizaje, comparto aquí un enfoque nacido de dos experiencias de unidad con el Todo — transmitido de forma intuitiva, en torno a la energía, los sonidos, las vibraciones, las frecuencias y la impermanencia que componen nuestro viaje terrenal.",
            "bio2": "30 minutos solo para ti, para explorar tu estado energético en profundidad y salir con pistas concretas — por teléfono, videollamada o WhatsApp, según lo que te resulte más cómodo.",
            "channel_phone": "📞 Teléfono",
            "channel_video": "🎥 Videollamada",
            "price": "30€ · 30 minutos",
        },
    },
    "pages": {
        "home": {
            "meta": {
                "title": "Vibr'Up — eleva tu energía, día tras día",
                "description": "Vibr'Up te ayuda a observar, comprender y elevar tu estado vibratorio — seguimiento diario, meditaciones guiadas y acompañamiento individual.",
            },
            "hero": {
                "eyebrow": "seguimiento vibratorio y energético",
                "title": "Reencuentra el hilo de <em>tu</em> energía, día tras día.",
                "lead": "Vibr'Up te ayuda a observar, comprender y elevar tu estado vibratorio — con un seguimiento diario, meditaciones guiadas y un acompañamiento personalizado cuando lo necesites.",
                "cta_ghost": "Reservar una guidance",
            },
            "photo_rhythm": {
                "eyebrow": "el ritmo antes que la velocidad",
                "quote": "Como una caravana que avanza en el silencio del desierto, tu energía sigue su propio ritmo — no el que te imponen.",
                "credit": "Foto — desierto del Sáhara",
            },
            "practice": {
                "eyebrow": "la práctica",
                "title": "Tres gestos simples, cada día",
                "lead": "No hace falta dedicarle una hora. Vibr'Up se integra en tu rutina, unos minutos bastan para observar y ajustar tu energía.",
                "card1_title": "Check-in diario",
                "card1_body": "Anota tu nivel vibratorio y cómo te sientes hoy. Un gesto simple que, repetido, revela tus ciclos de energía.",
                "card2_title": "Meditaciones guiadas",
                "card2_body": "Anclaje, elevación vibratoria, alineación — prácticas breves pensadas para actuar concretamente sobre tu energía.",
                "card3_title": "Evolución en el tiempo",
                "card3_body": "Visualiza tus tendencias a lo largo del tiempo para identificar lo que nutre — o drena — tu energía.",
            },
            "guidance_teaser": {
                "eyebrow": "acompañamiento",
                "title": "Una guidance individual, en directo",
                "lead": "Cuando el check-in ya no basta, comparte 30 minutos con Hamann para explorar tu estado energético en profundidad.",
                "cta": "Descubrir la guidance",
            },
            "resources_teaser": {
                "eyebrow": "recursos",
                "title": "Con qué nutrir tu práctica",
                "lead": "Artículos, afirmaciones y pistas de reflexión para profundizar tu camino, a tu ritmo.",
                "featured_tag": "Vibración",
                "featured_title": "Las afirmaciones positivas: cómo y por qué usarlas",
                "featured_desc": "Una guía simple para reprogramar tu diálogo interior, sin exigencias ni presión.",
                "featured_meta": "7 min de lectura",
                "soon_badge": "Próximamente",
                "card2_tag": "Meditaciones",
                "card2_title": "El anclaje: la primera piedra de toda práctica energética",
                "card2_desc": "Por qué reconectar con el suelo suele ser el paso más olvidado — y el más poderoso.",
                "card3_tag": "Manifestación",
                "card3_title": "Manifestar sin forzar: el matiz que lo cambia todo",
                "card3_desc": "La diferencia entre desear con intensidad y desear con tensión — y por qué importa.",
                "see_all": "Ver todos los recursos",
            },
            "pricing": {
                "eyebrow": "precios",
                "title": "Empieza gratis, ve más lejos cuando estés list@",
                "free_tier": "Gratis",
                "free_amount": "0€",
                "free_item1": "Check-in diario ilimitado",
                "free_item2": "7 últimos días de historial",
                "free_item3": "1 meditación guiada (Anclaje)",
                "free_cta": "Empezar",
                "plus_amount": "5€ <span>/ mes</span>",
                "plus_item1": "Todo el contenido gratuito",
                "plus_item2": "Historial y tendencias ilimitados",
                "plus_item3": "Todas las meditaciones guiadas",
                "plus_item4": "Acceso prioritario a las novedades",
                "plus_cta": "Suscribirse",
            },
            "photo_earth": {
                "eyebrow": "estés donde estés en esta tierra",
                "quote": "Tu energía no tiene fronteras. Empieces hoy donde empieces, Vibr'Up te acompaña.",
                "credit": "Foto — la Tierra vista desde el espacio",
            },
        },
        "about": {
            "meta": {
                "title": "Acerca de — Vibr'Up",
                "description": "Por qué existe Vibr'Up: una filosofía del regreso a uno mismo, sin exigencias ni dogmas.",
            },
            "header": {
                "eyebrow": "acerca de",
                "title": "Por qué existe Vibr'Up",
            },
            "lead": "Nunca te enseñaron realmente a escuchar tu energía — solo a soportarla, ignorarla, o llevarla más lejos de lo que puede llegar. Vibr'Up nació de la idea simple de que observar suele bastar para cambiar las cosas.",
            "photo": {
                "eyebrow": "una duna a la vez",
                "quote": "No se eleva la energía de golpe. Se avanza duna tras duna, día tras día.",
                "credit": "Foto — dunas del Sáhara",
            },
            "approach": {
                "eyebrow": "nuestro enfoque",
                "title": "Tres convicciones que guían a Vibr'Up",
            },
            "value1": {
                "title": "Observar antes de cambiar",
                "body": "No se puede ajustar lo que no se mira. El check-in diario no es una actuación que hay que lograr, solo un espejo honesto.",
            },
            "value2": {
                "title": "La constancia antes que la intensidad",
                "body": "Tres minutos cada día transforman de forma más duradera que una hora una vez al mes. Vibr'Up está pensado para durar en el tiempo.",
            },
            "value3": {
                "title": "Un acompañamiento sin dogma",
                "body": "Ninguna verdad única que seguir. Herramientas, pistas, y un acompañamiento humano para quienes quieran ir más lejos.",
            },
            "now": {
                "eyebrow": "¿y ahora qué?",
                "title": "Empieza donde estás, hoy",
                "lead": "No hace falta estar list@ ni seguro de nada. Un primer check-in basta para comenzar.",
                "cta": "Descubrir la práctica",
            },
        },
        "article": {
            "meta": {
                "title": "Las afirmaciones positivas: cómo y por qué usarlas — Vibr'Up",
                "description": "Una guía simple para usar las afirmaciones positivas sin presión ni positividad forzada, e integrarlas en tu práctica vibratoria diaria.",
            },
            "header": {
                "tag": "Vibración",
                "title": "Las afirmaciones positivas: cómo y por qué usarlas",
                "author": "Equipo Vibr'Up",
                "read_time": "7 min de lectura",
            },
            "body": {
                "p1": "Seguramente ya te has cruzado con una afirmación positiva en algún lugar — una frase corta, escrita en presente, que se supone transforma tu día con solo repetirla. Mucha gente las prueba una vez, cree en ellas solo a medias, y abandona. No es que no funcionen: a menudo es que las usamos sin entender lo que realmente hacen.",
                "p2": "Una afirmación no es una fórmula mágica. Es una herramienta de reprogramación suave, que actúa sobre la forma en que te hablas a ti mismo — y por tanto, con el tiempo, sobre tu estado vibratorio general.",
            },
            "section1": {
                "title": "Por qué el diálogo interior importa tanto",
                "p1": "La mayoría de los pensamientos que tienes cada día son automáticos. Se repiten, a menudo sin que los elijas conscientemente. Si ese diálogo interior tiende naturalmente hacia la duda o la autocrítica, termina convirtiéndose en el ruido de fondo de tu energía — el que te tira hacia abajo incluso antes de que empiece el día.",
                "p2": "Las afirmaciones positivas no buscan silenciar ese ruido a la fuerza. Proponen otra voz, más serena, que repites voluntariamente hasta que ella también se vuelve familiar.",
            },
            "quote": "Una afirmación repetida sin convicción sigue siendo una frase. Repetida con atención, se convierte en un hábito de pensamiento.",
            "section2": {
                "title": "Cómo formular una afirmación que te corresponda",
                "lead": "Bastan tres principios simples para empezar:",
                "item1": "<strong>El presente, siempre.</strong> \"Estoy en paz\" en lugar de \"estaré en paz\" — tu mente responde mejor al momento presente que a una promesa lejana.",
                "item2": "<strong>Una formulación que te siga siendo creíble.</strong> Si \"soy rico\" te parece demasiado lejos de tu realidad, empieza por \"estoy aprendiendo a acoger la abundancia\" — la formulación debe acompañarte, no confrontarte.",
                "item3": "<strong>Una intención precisa en lugar de un deseo vago.</strong> \"Respiro con calma en los momentos de tensión\" actúa de forma más concreta que \"soy zen\".",
            },
            "section3": {
                "title": "Integrarlas sin que se conviertan en una obligación más",
                "p1": "No hace falta añadir un ritual de veinte minutos a un día ya lleno. Las afirmaciones funcionan mejor cuando se deslizan en momentos que ya existen: al despertar, antes de abrir los ojos por completo; durante el café de la mañana; o justo antes de dormir, cuando la mente está más receptiva.",
                "p2": "Es exactamente el espíritu del check-in diario de Vibr'Up: un gesto breve, repetido, que no exige más que unos minutos de atención sincera.",
            },
            "section4": {
                "title": "Algunos ejemplos para empezar",
                "item1": "«Me permito avanzar a mi propio ritmo.»",
                "item2": "«Mi energía me pertenece, elijo dónde la coloco.»",
                "item3": "«Puedo sentir calma, incluso en la incertidumbre.»",
                "item4": "«Cada día aprendo un poco mejor a escucharme.»",
            },
            "closing": "Elige solo una para empezar. Repítela durante una semana entera antes de cambiarla. La constancia importa mucho más que la cantidad.",
            "cta": {
                "lead": "¿Quieres seguir el efecto de tu práctica día tras día?",
                "button": "Descubrir el check-in de Vibr'Up",
            },
        },
        "contact": {
            "meta": {
                "title": "Contacto — Vibr'Up",
                "description": "¿Cómo estás hoy? Escríbenos unas palabras, a tu ritmo.",
            },
            "hero": {
                "eyebrow": "hablemos",
                "title": "¿Cómo estás hoy?",
                "lead": "No hace falta explicarlo todo. Unas palabras bastan para empezar una conversación, a tu ritmo.",
            },
            "form": {
                "intro": "Este formulario no es un cuestionario. Responde solo a lo que te inspire — todo es opcional excepto una forma de volver a contactarte.",
                "feeling_label": "¿Cómo te sientes en este momento?",
                "feeling_field_name": "Sensación actual",
                "feeling_placeholder": "En pocas palabras, lo que está presente para ti hoy…",
                "stage_label": "¿En qué punto de tu camino estás?",
                "stage_field_name": "En qué punto estás",
                "stage_opt0": "Prefiero no decirlo",
                "stage_opt1": "Estoy recién descubriendo esto",
                "stage_opt2": "Estoy tratando de entender lo que pasa dentro de mí",
                "stage_opt3": "Estoy en plena transición",
                "stage_opt4": "Solo quiero profundizar una práctica",
                "stage_opt5": "Quiero reservar una guidance",
                "message_label": "Algo más, si lo necesitas (opcional)",
                "message_field_name": "Mensaje",
                "message_placeholder": "Lo que quieras compartir, sin obligación…",
                "firstname_label": "Tu nombre",
                "firstname_field_name": "Nombre",
                "firstname_placeholder": "Opcional",
                "contact_label": "¿Cómo podemos contactarte?",
                "contact_field_name": "Datos de contacto",
                "contact_placeholder": "Email, teléfono o WhatsApp",
                "submit": "Enviar, con calma",
                "submit_note": "Lo que escribes aquí queda entre nosotros.",
            },
        },
        "guidance": {
            "meta": {
                "title": "Guidance individual con Hamann — Vibr'Up",
                "description": "30 minutos de guidance individual con Hamann para explorar tu estado energético en profundidad — teléfono, videollamada o WhatsApp.",
            },
            "header": {
                "eyebrow": "acompañamiento",
                "title": "Una guidance individual, en directo",
                "lead": "Cuando observar tu energía en solitario ya no basta, 30 minutos con Hamann para explorar en profundidad lo que ocurre — y salir con pistas concretas.",
            },
            "photo": {
                "eyebrow": "un acompañamiento, no una prescripción",
                "quote": "No se trata de darte respuestas ya hechas, sino de ayudarte a escuchar las que ya llevas dentro.",
                "credit": "Foto — dunas del Sáhara al atardecer",
            },
            "how": {
                "eyebrow": "cómo funciona",
                "title": "Cómo transcurre una sesión",
                "step1_title": "Te pones en contacto",
                "step1_body": "A través del formulario de contacto, con unas palabras sobre lo que te trae aquí. Nada es obligatorio, solo un punto de partida.",
                "step2_title": "Eliges el formato",
                "step2_body": "Teléfono, videollamada o WhatsApp — según lo que te resulte más cómodo, a la hora que os convenga a ambos.",
                "step3_title": "Sales con pistas",
                "step3_body": "Nada de discursos prefabricados: observaciones reales y pistas concretas para explorar, a tu ritmo.",
            },
            "faq": {
                "eyebrow": "preguntas frecuentes",
                "title": "Antes de reservar",
                "q1_title": "¿Necesito usar ya Vibr'Up para reservar una guidance?",
                "q1_body": "No. La guidance está abierta a todo el mundo, uses la aplicación o no.",
                "q2_title": "¿Cómo funciona el pago?",
                "q2_body": "Los detalles te los indicará directamente Hamann tras tu toma de contacto.",
                "q3_title": "¿Y si no sé qué decir al principio?",
                "q3_body": "Es muy común, y no es un problema. La sesión está pensada justamente para ayudarte a ver las cosas con más claridad, no al revés.",
                "q4_title": "¿Puedo reprogramar si lo necesito?",
                "q4_body": "Sí, basta con solicitarlo a través del formulario de contacto lo antes posible.",
            },
            "cta": "Reservar mi sesión",
        },
        "resources": {
            "meta": {
                "title": "Recursos — Vibr'Up",
                "description": "Artículos, afirmaciones y pistas de reflexión para nutrir tu práctica vibratoria, a tu ritmo.",
            },
            "header": {
                "eyebrow": "recursos",
                "title": "Un espacio para nutrir tu práctica",
                "lead": "Artículos, afirmaciones y pistas de reflexión sobre la vibración, el anclaje y el regreso a uno mismo — escritos con sencillez, sin jerga.",
            },
            "filters": {
                "all": "Todos",
                "vibration": "Vibración",
                "meditations": "Meditaciones",
                "manifestation": "Manifestación",
                "grounding": "Anclaje",
                "cycles": "Ciclos energéticos",
            },
            "featured": {
                "tag": "Vibración",
                "title": "Las afirmaciones positivas: cómo y por qué usarlas",
                "desc": "Una guía simple para reprogramar tu diálogo interior, sin exigencias ni presión.",
                "meta": "7 min de lectura",
            },
            "soon_badge": "Próximamente",
            "article_grounding": {
                "tag": "Anclaje",
                "title": "El anclaje: la primera piedra de toda práctica energética",
                "desc": "Por qué reconectar con el suelo suele ser el paso más olvidado — y el más poderoso.",
            },
            "article_manifestation": {
                "tag": "Manifestación",
                "title": "Manifestar sin forzar: el matiz que lo cambia todo",
                "desc": "La diferencia entre desear con intensidad y desear con tensión — y por qué importa.",
            },
            "article_cycles": {
                "tag": "Ciclos energéticos",
                "title": "Comprender tus ciclos energéticos a lo largo de un mes",
                "desc": "Lo que tu historial de check-in puede revelar cuando te tomas el tiempo de releerlo.",
            },
            "article_5min": {
                "tag": "Meditaciones",
                "title": "5 minutos para recentrar tu día",
                "desc": "Una práctica breve para deslizar entre dos citas, cuando todo se acelera a tu alrededor.",
            },
            "article_energy_drop": {
                "tag": "Vibración",
                "title": "Por qué tu energía baja al final del día",
                "desc": "Tres causas frecuentes de fatiga vibratoria, y cómo empezar a detectarlas.",
            },
            "article_evening_ritual": {
                "tag": "Anclaje",
                "title": "Crear un ritual nocturno simple y duradero",
                "desc": "No hacen falta velas ni treinta minutos: tres gestos bastan para cerrar el día.",
            },
            "article_resonance": {
                "tag": "Manifestación",
                "title": "La ley de la resonancia, explicada de forma simple",
                "desc": "Una manera más suave y más justa de entender lo que a veces se llama \"ley de atracción\".",
            },
            "newsletter": {
                "title": "20 afirmaciones para elevar tu vibración",
                "lead": "Una guía gratuita para recibir por email, para leer cuando la necesites — sin compromiso, sin spam.",
                "email_placeholder": "Tu dirección de email",
                "submit": "Recibir la guía",
                "note": "Un email de vez en cuando, nunca más.",
            },
        },
    },
}
```

- [ ] **Step 2: Sanity-check the file parses**

Run: `python3 -c "import sys; sys.path.insert(0, '.'); import i18n.es; print(len(str(i18n.es.STRINGS)))"`
Expected: prints a character count.

- [ ] **Step 3: Commit**

```bash
git add i18n/es.py
git commit -m "Add Spanish translation strings"
```

---

## Task 15: Run the build and verify migration fidelity

**Files:**
- Modify (regenerated by the build, not hand-edited): `index.html`, `a-propos.html`,
  `article.html`, `contact.html`, `guidance.html`, `ressources.html`,
  `en/index.html`, `en/about.html`, `en/article.html`, `en/contact.html`,
  `en/guidance.html`, `en/resources.html`, `es/index.html`, `es/acerca-de.html`,
  `es/articulo.html`, `es/contacto.html`, `es/guidance.html`, `es/recursos.html`

- [ ] **Step 1: Run the unit tests one more time**

Run: `python3 -m unittest discover tests -v`
Expected: `OK` — all tests from Tasks 2–3 still pass (nothing in Tasks 5–14 touched
`equipment/build.py`'s tested functions).

- [ ] **Step 2: Run the build**

Run: `python3 equipment/build.py`
Expected: `[OK] built 6 pages x up to 3 languages`. If it fails instead, the error
names the exact `page=`, `lang=`, and missing/unexpected key — cross-check the
failing template against the matching key in `i18n/<lang>.py` (a typo in either
file is the most likely cause) and rerun.

- [ ] **Step 3: Diff against the previously hand-authored files**

Run: `git diff --stat` then `git diff index.html en/index.html es/index.html`
(repeat per page as needed).
Expected: the only difference on every file is the new leading
`<!-- AUTO-GENERATED ... -->` comment line. Any other diff — a missing/extra
space, a dropped `&amp;`, a swapped `€`/`$` position, a wrong nav href — is a
migration bug: fix the template or the `i18n/<lang>.py` entry it points at (not
the generated file), rerun `python3 equipment/build.py`, and re-diff until clean.

- [ ] **Step 4: Run the existing parity checker against the freshly built output**

Run: `python3 equipment/check-i18n-parity.py`
Expected: all six `[OK]` lines (this still uses the old inline `PAGES` dict at
this point in the plan — Task 16 points it at the shared registry, but the check
itself is language-structure-only so it passes regardless).

- [ ] **Step 5: Commit the regenerated output**

```bash
git add index.html a-propos.html article.html contact.html guidance.html ressources.html \
        en/index.html en/about.html en/article.html en/contact.html en/guidance.html en/resources.html \
        es/index.html es/acerca-de.html es/articulo.html es/contacto.html es/guidance.html es/recursos.html
git commit -m "Regenerate all 18 pages from templates/i18n (migration to generator)"
```

---

## Task 16: Point the parity checker at the shared registry

**Files:**
- Modify: `equipment/check-i18n-parity.py`

- [ ] **Step 1: Replace the inline PAGES dict with the shared registry**

In `equipment/check-i18n-parity.py`, replace:
```python
# Logical page -> {lang: path relative to repo root}. Every language present
# for a page is checked pairwise against the others.
PAGES = {
    "home": {"fr": "index.html", "en": "en/index.html", "es": "es/index.html"},
    "about": {"fr": "a-propos.html", "en": "en/about.html", "es": "es/acerca-de.html"},
    "article": {"fr": "article.html", "en": "en/article.html", "es": "es/articulo.html"},
    "contact": {"fr": "contact.html", "en": "en/contact.html", "es": "es/contacto.html"},
    "guidance": {"fr": "guidance.html", "en": "en/guidance.html", "es": "es/guidance.html"},
    "resources": {"fr": "ressources.html", "en": "en/resources.html", "es": "es/recursos.html"},
}
```
with:
```python
sys.path.insert(0, str(ROOT))
from equipment.site_map import LANGS, PAGES  # noqa: E402
```
(add this import near the top of the file, right after `ROOT = ...` is defined,
and remove the now-redundant inline dict entirely).

- [ ] **Step 2: Iterate over the registered languages, not the PAGES dict's keys**

`PAGES` entries now also carry `"template"` and `"nav_id"` keys (not languages) —
`check_page()`'s `for lang in sorted(variants):` would treat those as bogus
"languages" and crash on `Path` construction. Change:
```python
def check_page(name, variants):
    langs = sorted(variants)
    skeletons = {}
    missing = []
    for lang in langs:
```
to:
```python
def check_page(name, variants):
    skeletons = {}
    missing = []
    for lang in LANGS:
```

- [ ] **Step 3: Run it**

Run: `python3 equipment/check-i18n-parity.py`
Expected: same six `[OK]` lines as Task 15 Step 4, exit code 0 — now sourced from
the shared registry instead of a duplicated dict.

- [ ] **Step 4: Commit**

```bash
git add equipment/check-i18n-parity.py
git commit -m "Point check-i18n-parity.py at the shared site_map registry"
```

---

## Task 17: Wire build.py into serve/deploy

**Files:**
- Modify: `equipment/serve.sh`
- Modify: `equipment/deploy.sh`

- [ ] **Step 1: Update serve.sh**

`equipment/serve.sh` (full file):
```bash
#!/usr/bin/env bash
# Rebuilds the site from templates/+i18n/, then serves it on localhost:4173.
# No inputs. Runs until Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 equipment/build.py
exec python3 -m http.server 4173
```

- [ ] **Step 2: Update deploy.sh**

`equipment/deploy.sh` (full file):
```bash
#!/usr/bin/env bash
# Rebuilds the site from templates/+i18n/, then deploys to Vercel production.
# No inputs beyond an authenticated `vercel` CLI session. Prints the
# production deployment URL.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 equipment/build.py
exec vercel --prod
```

- [ ] **Step 3: Verify serve.sh still works**

Run: `equipment/serve.sh &` then `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:4173/index.html`,
then stop the background server (`kill %1`).
Expected: prints `200`.

- [ ] **Step 4: Commit**

```bash
git add equipment/serve.sh equipment/deploy.sh
git commit -m "Run build.py before serving or deploying"
```

---

## Task 18: Update the parity-checker Blueprint

**Files:**
- Modify: `blueprints/check-i18n-parity.md`

- [ ] **Step 1: Replace the file's content**

`blueprints/check-i18n-parity.md` (full file):
```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add blueprints/check-i18n-parity.md
git commit -m "Update parity-checker blueprint for the templated build"
```

---

## Task 19: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Full clean rebuild**

Run: `python3 equipment/build.py && python3 equipment/check-i18n-parity.py && python3 -m unittest discover tests -v`
Expected: build reports `[OK]`, parity checker reports six `[OK]` lines with exit
0, unit tests report `OK`.

- [ ] **Step 2: Local smoke test across all three languages**

Run:
```bash
equipment/serve.sh &
sleep 1
for p in index.html a-propos.html article.html contact.html guidance.html ressources.html \
         en/index.html en/about.html en/article.html en/contact.html en/guidance.html en/resources.html \
         es/index.html es/acerca-de.html es/articulo.html es/contacto.html es/guidance.html es/recursos.html; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:4173/$p")
  echo "$code  $p"
done
kill %1
```
Expected: `200` for all 18 paths.

- [ ] **Step 3: Confirm git status is clean**

Run: `git status --short`
Expected: no output (everything from Tasks 1–18 has already been committed
task-by-task; this step only catches anything left over, e.g. a stray diff from
re-running the build in Step 1 above — if `git diff` shows one, it means Step 1's
rebuild produced different output than what's committed, which means a template
or i18n edit slipped in after Task 15's commit without being re-verified; diff it
and commit if intentional, or investigate if not).
