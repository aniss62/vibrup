#!/usr/bin/env python3
"""Checks that FR/EN/ES versions of each page share the same HTML structure.

Usage: equipment/check-i18n-parity.py
Exit code 0 if every registered page has matching structure across all
languages it's translated into; 1 if any pair has diverged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Logical page -> {lang: path relative to repo root}. Add new pages here.
PAGES = {
    "home": {"fr": "index.html", "en": "en/index.html", "es": "es/index.html"},
    "about": {"fr": "a-propos.html", "en": "en/about.html", "es": "es/acerca-de.html"},
    "article": {"fr": "article.html", "en": "en/article.html", "es": "es/articulo.html"},
    "contact": {"fr": "contact.html", "en": "en/contact.html", "es": "es/contacto.html"},
    "guidance": {"fr": "guidance.html", "en": "en/guidance.html", "es": "es/guidance.html"},
    "resources": {"fr": "ressources.html", "en": "en/resources.html", "es": "es/recursos.html"},
}

TAG_RE = re.compile(r"<(/?)([a-zA-Z0-9]+)((?:\s+[a-zA-Z-]+(?:=(?:\"[^\"]*\"|'[^']*'))?)*)\s*/?>")
ATTR_NAME_RE = re.compile(r"([a-zA-Z-]+)(?:=(?:\"[^\"]*\"|'[^']*'))?")


def skeleton(html):
    """Reduce HTML to a list of (tag, sorted attribute names), text and
    attribute values (locale-specific by design) dropped."""
    out = []
    for closing, tag, attrs_str in TAG_RE.findall(html):
        if closing:
            continue
        attr_names = sorted(m.group(1).lower() for m in ATTR_NAME_RE.finditer(attrs_str) if m.group(1))
        out.append((tag.lower(), tuple(attr_names)))
    return out


def diff_report(base_lang, base_skel, lang, other_skel, limit=8):
    lines = [f"  structure mismatch: [{base_lang}] vs [{lang}]"]
    shown = 0
    for i in range(max(len(base_skel), len(other_skel))):
        a = base_skel[i] if i < len(base_skel) else None
        b = other_skel[i] if i < len(other_skel) else None
        if a != b:
            lines.append(f"    at tag #{i}: {base_lang}={a}  {lang}={b}")
            shown += 1
            if shown >= limit:
                lines.append("    ...")
                break
    return "\n".join(lines)


def check_page(variants):
    skeletons, missing = {}, []
    for lang in sorted(variants):
        path = ROOT / variants[lang]
        if not path.exists():
            missing.append(lang)
            continue
        skeletons[lang] = skeleton(path.read_text(encoding="utf-8"))

    present = sorted(skeletons)
    problems = []
    if present:
        base_lang = present[0]
        for lang in present[1:]:
            if skeletons[lang] != skeletons[base_lang]:
                problems.append((base_lang, lang))
    return skeletons, missing, problems


def main():
    exit_code = 0
    for name, variants in PAGES.items():
        skeletons, missing, problems = check_page(variants)
        if missing:
            print(f"[TODO]  {name}: no translation yet for {', '.join(missing)}")
        if problems:
            exit_code = 1
            print(f"[FAIL]  {name}: structural mismatch")
            for base_lang, lang in problems:
                print(diff_report(base_lang, skeletons[base_lang], lang, skeletons[lang]))
        elif not missing:
            print(f"[OK]    {name}: {', '.join(sorted(skeletons))} match")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
