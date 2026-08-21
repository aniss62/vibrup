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
        "fr": "accueil.html", "en": "en/home.html", "es": "es/inicio.html",
    },
    "about": {
        "template": "about.html", "nav_id": "about",
        "fr": "index.html", "en": "en/index.html", "es": "es/index.html",
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
    "meditations": {
        "template": "meditations.html", "nav_id": "resources",
        "fr": "meditations.html", "en": "en/meditations.html", "es": "es/meditaciones.html",
    },
    "checkin": {
        "template": "checkin.html", "nav_id": "home",
        "fr": "check-in.html", "en": "en/check-in.html", "es": "es/check-in.html",
    },
    "evolution": {
        "template": "evolution.html", "nav_id": "home",
        "fr": "evolution.html", "en": "en/evolution.html", "es": "es/evolucion.html",
    },
    "manifestation": {
        "template": "manifestation.html", "nav_id": "resources",
        "fr": "manifestation.html", "en": "en/manifestation.html", "es": "es/manifestacion.html",
    },
    "cycles": {
        "template": "cycles.html", "nav_id": "resources",
        "fr": "cycles.html", "en": "en/cycles.html", "es": "es/ciclos.html",
    },
    "grounding": {
        "template": "grounding.html", "nav_id": "resources",
        "fr": "ancrage.html", "en": "en/grounding.html", "es": "es/anclaje.html",
    },
    "resources": {
        "template": "resources.html", "nav_id": "resources",
        "fr": "ressources.html", "en": "en/resources.html", "es": "es/recursos.html",
    },
}
