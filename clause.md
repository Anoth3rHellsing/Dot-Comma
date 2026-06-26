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

10. **External integrations dropped (plan change 2026-06-26).** ✅ REMOVED
    Spotify, Google Workspace / Microsoft 365 (Gmail / Outlook), and Twitch / YouTube
    were removed from the plan. The **only** external service Dot & Comma talks to is the
    **DeepSeek** API (for Dot's responses). All references to the dropped services were
    struck from `clause.md` and the `JULES READ THIS` brief.

---

## ✅ Phase C — Visual identity (built 2026-06-26)

11. **A.N.O.T.H.E.R. corporate logo (CSS + SVG).** ✅ DONE
    Inline SVG logo in the main-menu header: a slowly-spinning **gear**, a **factory
    silhouette** with a sawtooth roof and rising **smoke**, the **A.N.O.T.H.E.R.**
    wordmark, and **trailing red/teal/gold stripes**. (Dot's pulsing cerulean dot is kept
    separately as her own avatar.)

12. **Typographic pixelated shadow.** ✅ DONE
    `h2` headings now carry a stepped/pixelated text-shadow on top of the phosphor glow,
    emulating low-res CRT text.
    *Note: screen curvature is still just `border-radius` — a true barrel/curve effect
    was left out to avoid breaking the flex layout.*

---

## 🧹 Polish / cleanup (nice-to-have, not blocking)

13. **`flask.log` was committed** even though it's listed in `.gitignore`. ✅ FIXED
    Untracked with `git rm --cached flask.log`.

14. **`debug=True` in `app.run(...)`** — fine for local dev, but should be off for any
    shared/production deployment (it exposes the Werkzeug debugger). *(left as-is — this
    is a local single-user app)*

15. **DeepSeek API key is stored in plaintext** in the SQLite DB. Acceptable for a
    local single-user app, but worth a note in the README.

16. **Unused import** `import sqlite3` in `init_db.py` and `app.py`. ✅ FIXED — removed.

17. **README says "AI Integration: DeepSeek API"** — consistent with code ✅, just
    confirming the README and `ai_provider.py` agree (they do).

---

## Current direction (2026-06-26)

External integrations (Spotify / Google / Microsoft / Twitch / YouTube) are **out** —
DeepSeek is the only outside service. Active focus:

1. **Jira / work-job organization** — integrate the JiraDashboard project so Dot can
   organize work-related jobs (approach TBD — see open question with the user).
2. **System (desktop) notifications** for routine reminders (water, breaks, etc.) —
   built via the browser Notification API. ✅ DONE
