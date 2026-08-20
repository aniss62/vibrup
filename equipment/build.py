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
