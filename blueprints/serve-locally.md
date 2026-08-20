# Blueprint: Preview the site locally

**Goal:** Serve the static site on localhost so changes can be checked in a browser
before deploying.

**Inputs needed:** none.

**Steps:**
1. Run `equipment/serve.sh`.
2. Open http://localhost:4173 in a browser.
3. Navigate to the page you changed (root = French, `/en/` = English) and verify the
   change.
4. Stop the server with Ctrl+C when done.

**Expected output:** A local HTTP server on port 4173 serving the repo root, matching
the `vibrup-static` launch configuration in `.claude/launch.json`.
