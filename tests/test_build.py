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

    def test_missing_key_message_has_no_stray_quotes(self):
        with self.assertRaises(KeyError) as cm:
            render("{{ pages.home.missing }}", {"pages": {"home": {}}})
        # KeyError.__str__ always reprs args[0] (a CPython quirk unique to
        # KeyError), so a single layer of quoting around the whole message
        # is expected. The bug fixed here was a *second*, compounding layer
        # of quoting (an inner "'...'" baked into the message text) caused
        # by interpolating the inner KeyError via `{e}` (-> str(e), which
        # reprs) instead of `{e.args[0]}` (the raw path). Pin the exact text
        # so that regression is caught.
        self.assertEqual(
            str(cm.exception),
            "'missing translation key: pages.home.missing'",
        )


if __name__ == "__main__":
    unittest.main()
