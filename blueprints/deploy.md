# Blueprint: Deploy to production

**Goal:** Publish the current state of the site to the live Vercel deployment.

**Inputs needed:** Vercel CLI authenticated on this machine (`vercel login`, one-time
setup, not tracked in this repo).

**Steps:**
1. Confirm the working tree is in the state you want live (check `git status`, commit
   or stash anything unintended).
2. Run `equipment/deploy.sh`.
3. Open the production URL the script prints and verify the change.

**Expected output:** A new production deployment on Vercel for the `vibrup` project
(see `.vercel/project.json`), with the deployment URL printed to stdout.
