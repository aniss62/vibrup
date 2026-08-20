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
