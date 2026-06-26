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

## ❌ Missing spec features (designed but not built)

5. **Daily Scrum 15-minute structured stand-up is not implemented.**
   The spec requires a daily session answering the 3 Scrum questions
   (yesterday / today / impediments). Right now there's only a sprint progress number
   and an auto-created "Daily Scrum" calendar event — no guided Q&A flow.

6. **Sprint motivational graph + "issues overcome" reminder is missing.**
   Spec asks for a progress graph, an estimated % completion, and a reminder that the
   user "overcame X issues and made it." Currently it's just a numeric input field.

7. **Focus-mode "motivational message every 15 minutes" is not implemented.**
   Spec: while focusing on a task, Dot should auto-send a motivational nudge every
   15 minutes. There's a chronometer but no recurring nudge.

8. **Medium-task "Deconstruct the Goal" (3–5 micro-tasks) is missing.**
   No sub-task breakdown, no sticky-note view, no 2–4h time-blocking. The task is
   stored as a single title + description only.

9. **Tamagotchi stats never decay and the "self-care / can't die" logic is missing.**
   - Stats only ever go **up** (completing a routine), they never decrease over time,
     so the pet/user-health parallel doesn't really work.
   - Spec: pet cannot die; if Dot suspects low self-care/depression, the pet should
     start self-caring and motivate the user. Not implemented.
   - "Pet is always a cat, colors may vary" — color variation not implemented.
   - "User can add medications/routines" — only generic routine titles supported.

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
