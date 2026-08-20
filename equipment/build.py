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
            raise KeyError(f"missing translation key: {e.args[0]}") from None
    return PLACEHOLDER_RE.sub(_sub, template_text)


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
