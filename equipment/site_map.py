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
