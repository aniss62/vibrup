# Vibr'Up — Operating Model

This repo runs on the **Three-Engine Model (ABE)**: Architect, Blueprints, Equipment.

```
blueprints/    → Markdown instructions for every workflow. Each file states the goal,
                 inputs needed, steps to follow, and expected output.
equipment/     → Scripts that each do one job. Same input, same output, every time.
                 All credentials live in .env, never in scripts.
.tmp/          → Temporary and disposable files. Everything here can be deleted and
                 regenerated.
.env           → API keys and credentials. The only place they live. Ever.
```

## The Three Engines

**A — Architect (Claude)**
Decision-maker. Before doing anything, read the relevant Blueprint. Pick the right
Equipment. Run it in order. When something breaks, fix it and update the Blueprint so
it never breaks the same way twice. Never execute tasks directly when a script in
`equipment/` can do it instead.

**B — Blueprints (`blueprints/`)**
Plain-language markdown files that tell the Architect exactly what to do. Never create
or overwrite a Blueprint without asking first.

**C — Equipment (`equipment/`)**
One script per task. You don't need to know how a script works internally — just what
it does, what it needs, and what it returns.

## When something breaks

1. Read the full error before touching anything.
2. Fix the script properly — no workarounds.
3. Run it again and confirm the output.
4. Update the Blueprint with what you learned.
5. Keep going. The system just got stronger.

## About this site

Static HTML/CSS/JS site (no build step, no package manager) for Vibr'Up, deployed on
Vercel. `index.html` (site root) is the "À propos" / manifesto page — it's the main
entry point. French pages live at the root (`index.html`, `accueil.html`, `article.html`,
`contact.html`, `guidance.html`, `ressources.html`); English translations mirror them
under `en/`, Spanish under `es/` (`index.html`, `home.html`/`inicio.html`, `article.html`/
`articulo.html`, `contact.html`/`contacto.html`, `guidance.html`, `resources.html`/
`recursos.html`). Shared assets: `styles.css`, `script.js`, `images/`. The three
languages must stay structurally identical (same tags/attributes, only text differs) —
see `blueprints/check-i18n-parity.md`.

Pages are generated from `templates/pages/*.html` + `templates/partials/*.html` +
`i18n/{fr,en,es}.py`, driven by `equipment/site_map.py` (the page-id → file-path
registry) and rendered by `equipment/build.py`. Never hand-edit a generated HTML file —
edit its template/i18n source and run `equipment/build.py`.

See `blueprints/` for the current documented workflows (local preview, deploy,
i18n parity check). Ask before adding new Blueprints/Equipment for workflows not yet
covered.
