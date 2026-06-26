# Dot & Comma — Code Review vs. "JULES READ THIS" Spec

> Review date: 2026-06-26
> Reviewed against the original design brief in the `JULES READ THIS` file.
> Legend: ✅ done · ⚠️ partial / buggy · ❌ missing

This file is the to-do / improvement list. Items are grouped as **Bugs to fix**,
**Missing spec features**, and **Polish / cleanup**. Within each group they are
roughly ordered by importance.

---

## ✅ What is already done (confirmed)

- **CRT boot sequence** — DOS-style sequential boot text animation. ✅
- **Numeric directory navigation** `[1]…[7]` (mouse click works). ✅
- **Sprint module** — create sprint, update progress %, Dot gives snarky feedback. ⚠️ (see bugs)
- **Medium Tasks** — Outlook-style list (left) + details (right), Focus mode with
  minimizing list, per-task chat, and a chronometer showing only mm:ss. ✅
- **Routine tasks + Tamagotchi cat** — add routines, check them off, cat stats rise. ⚠️ (see below)
- **Talk with Dot** — persistent chat saved to DB, permanent memory, "Do you remember?",
  archive chats, configurable context size. ✅
- **Economy & Finance** — log spent/won, HTML/CSS bar graph, Dot scolds/advises. ✅
- **Calendar + notifications** — events, 15-min & 5-min overlay warnings, auto Daily Scrum event. ✅
- **Onboarding** — collects user name, persisted and used by Dot. ✅
- **Dot personality** — system prompt matches the brief (productive friction, sarcasm, puns). ✅
- **CRT aesthetic basics** — scanlines, flicker, phosphor glow, vignette, black background. ✅

---

## ✅ Bugs fixed (2026-06-26)

1. **Keyboard navigation to the Sprint menu was broken.** ✅ FIXED
   `static/script.js` mapped `key === '1'` → `navigate('scrum')`, but there is no
   `scrum-section` (the section is `sprints-section`), so pressing **1** threw a
   null-reference error. Changed to `navigate('sprints')`.

2. **The Active Sprints list never loaded when opening the Sprint screen.** ✅ FIXED
   `navigate()` had no `else if (section === 'sprints') loadSprints();` branch, so
   sprints only appeared after you created/updated one. Added the missing call.

3. **Database connection leak in `/api/calendar`.** ✅ FIXED
   Every branch (`GET`/`POST`/`DELETE`) returned before the trailing `conn.close()`,
   so the connection was never closed. Wrapped the body in `try/finally`.

4. **Calendar screen had no BACK button.** ✅ FIXED
   Every other section has `BACK [0]`; the calendar section did not. Added it.

*Verified by smoke test: app boots, `/api/dashboard`, `/api/sprints`, and the
calendar GET/POST round-trip all return 200.*

---

## ✅ Phase A — Core Scrum/productivity (built 2026-06-26)

5. **Daily Scrum 15-minute structured stand-up.** ✅ DONE
   New `scrum_entries` table, `/api/scrum` endpoint, and a Daily Scrum panel in the
   Sprint screen with the 3 questions (yesterday / today / impediments). Dot reviews
   each stand-up and gives tailored feedback referencing the linked sprint.

6. **Sprint motivational graph + "issues overcome" reminder.** ✅ DONE
   Active sprints now render a CSS progress bar each. Impediments reported in the
   stand-up are logged to an `impediments` table; the user can mark them RESOLVED, and
   a gold banner reminds them "You've overcome X impediments… you made it through every
   one." (`/api/impediments/resolve`).

7. **Focus-mode "motivational message every 15 minutes".** ✅ DONE
   Entering Focus mode starts a 15-min interval that calls `/api/focus/nudge`; Dot's
   nudge is appended to the focus chat. Cleared on exit.

8. **Medium-task "Deconstruct the Goal" (3–5 micro-tasks).** ✅ DONE
   New `subtasks` table + `/api/tasks/subtasks` and `/api/tasks/deconstruct`. A
   DECONSTRUCT button asks Dot to break the task into 3–5 micro-steps, parsed into
   checkable sub-steps. Graceful fallback if no API key is configured.
   *Note: sticky-note view and 2–4h time-blocking from the spec are still not built.*

---

## ✅ Phase B — Tamagotchi soul (built 2026-06-26)

9. **Tamagotchi decay + "self-care / can't die" logic.** ✅ DONE
   - Stats now **decay per hour** (`last_update` timestamp drives it: health −2/hr,
     happiness −3/hr, cleanliness −4/hr), applied on each dashboard/routines read.
   - **The cat can't die:** stats floor at 20 (`TAMA_LOW`). When it bottoms out, the
     cat "self-cares" and Dot shows a *gentle, non-clinical* encouraging message
     ("it can't fall apart — and neither can you"). No diagnosing.
   - **Color variation:** `color` column + `/api/tamagotchi/color` "NEW LOOK" button
     cycles the cat through 6 CRT colors. Mood also changes its ASCII face
     (happy / okay / struggling).
   - **Medications:** routines now have a `category` ('routine' | 'medication'); meds
     are tagged with 💊 and shown in magenta.

10. **No external integrations at all** (all spec'd, none built):
    - **Google Workspace / Microsoft 365** (Gmail, Outlook send/connect).
    - **Spotify** daily playlist based on task load (lofi vs. "Pitbull-like").
    - **Twitch / YouTube** connectors for content-creator performance.

11. **Corporate visual identity (A.N.O.T.H.E.R. logo) is incomplete.**
    Spec wants the logo "meticulously recreated using CSS and SVG" with **gear + factory
    silhouettes** and **trailing red/teal/gold stripes.** Currently there's only a single
    pulsing cerulean dot. The color variables exist but the logo art does not.

12. **Typographic dotted/pixelated shadow not implemented.**
    Phosphor glow exists, but the spec's "dotted or pixelated shadow emulating screen
    resolution" on the main text is not there. Screen curvature is only a `border-radius`,
    not a true curved/barrel effect.

---

## 🧹 Polish / cleanup (nice-to-have, not blocking)

13. **`flask.log` is committed to the repo** even though it's listed in `.gitignore`.
    It was committed before being ignored. → `git rm --cached flask.log`.

14. **`debug=True` in `app.run(...)`** — fine for local dev, but should be off for any
    shared/production deployment (it exposes the Werkzeug debugger).

15. **DeepSeek API key is stored in plaintext** in the SQLite DB. Acceptable for a
    local single-user app, but worth a note in the README.

16. **Unused import** `import sqlite3` in `init_db.py` (and in `app.py`) — `db_utils`
    handles connections. Minor.

17. **README says "AI Integration: DeepSeek API"** — consistent with code ✅, just
    confirming the README and `ai_provider.py` agree (they do).

---

## Suggested priority order

1. Fix the two Sprint bugs (#1, #2) — they make a whole menu effectively unusable.
2. Fix the calendar connection leak (#3) and add the BACK button (#4).
3. Decide which of the bigger spec features (#5–#12) are actually in scope for this
   release vs. a later phase — the integrations (#10) especially are large efforts.
