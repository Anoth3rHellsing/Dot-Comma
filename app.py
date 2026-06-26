import os
import re
import datetime
from flask import Flask, render_template, request, jsonify
import db_utils
from ai_provider import generate_ai_response
from init_db import init_db

app = Flask(__name__)

def get_db_connection():
    return db_utils.get_db_connection()


# --- Tamagotchi (virtual cat) tuning ---
TAMA_DECAY_PER_HOUR = {'health': 2, 'happiness': 3, 'cleanliness': 4}
TAMA_LOW = 20      # self-care floor: the cat can't drop below this, so it never dies
TAMA_MAX = 100
TAMA_COLORS = ['gold', 'cyan', 'magenta', 'green', 'red', 'blue']


def apply_tamagotchi_decay(conn):
    """Decay the cat's stats by whole elapsed hours. The cat self-cares before it can
    die, so no stat ever falls below TAMA_LOW. Returns the (possibly updated) row."""
    tama = conn.execute('SELECT * FROM tamagotchi WHERE id = 1').fetchone()
    if not tama:
        return None

    now = datetime.datetime.now()
    last_str = tama['last_update']
    try:
        last = datetime.datetime.fromisoformat(last_str) if last_str else now
    except (ValueError, TypeError):
        last = now

    elapsed_hours = int((now - last).total_seconds() // 3600)
    if elapsed_hours < 1:
        return tama  # not yet another full hour; keep the leftover minutes

    new_stats = {}
    for stat, rate in TAMA_DECAY_PER_HOUR.items():
        decayed = tama[stat] - rate * elapsed_hours
        new_stats[stat] = max(TAMA_LOW, min(TAMA_MAX, decayed))

    # advance the clock only by the whole hours we consumed
    new_last = last + datetime.timedelta(hours=elapsed_hours)

    conn.execute('''UPDATE tamagotchi
                    SET health = ?, happiness = ?, cleanliness = ?, last_update = ?
                    WHERE id = 1''',
                 (new_stats['health'], new_stats['happiness'], new_stats['cleanliness'],
                  new_last.isoformat(sep=' ', timespec='seconds')))
    conn.commit()
    return conn.execute('SELECT * FROM tamagotchi WHERE id = 1').fetchone()


def tamagotchi_state(tama):
    """Mood + a gentle, encouraging message based on the cat's stats."""
    if not tama:
        return {'mood': 'unknown', 'message': '', 'avg': 0}

    avg = (tama['health'] + tama['happiness'] + tama['cleanliness']) / 3
    struggling = min(tama['health'], tama['happiness'], tama['cleanliness']) <= TAMA_LOW

    if struggling:
        mood = 'struggling'
        message = ("Your cat is quietly grooming itself and keeping going, even while it's running low. "
                   "It can't fall apart — and neither can you. Tick off a little self-care and you'll both feel better.")
    elif avg >= 70:
        mood = 'happy'
        message = "Your cat is thriving. Keep it up — both of you."
    else:
        mood = 'okay'
        message = "Your cat is doing alright, but could use some care. A routine or two would help."

    return {'mood': mood, 'message': message, 'avg': round(avg)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sprints', methods=['GET', 'POST', 'PUT'])
def api_sprints():
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        conn.execute('''
            INSERT INTO sprints (objective, start_date, end_date, progress, status)
            VALUES (?, ?, ?, ?, 'active')
        ''', (data.get('objective'), data.get('start_date'), data.get('end_date'), data.get('progress', 0)))
        conn.commit()

        # Get AI Feedback
        prompt = f"The user just created a new sprint. Objective: {data.get('objective')}. Start: {data.get('start_date')}. End: {data.get('end_date')}. Provide a short snarky, yet motivating response as Dot regarding this new sprint."
        ai_feedback = generate_ai_response(prompt)

        conn.close()
        return jsonify({'status': 'success', 'feedback': ai_feedback})
    elif request.method == 'PUT':
        data = request.json
        sprint_id = data.get('id')
        new_progress = data.get('progress')

        conn.execute('UPDATE sprints SET progress = ? WHERE id = ?', (new_progress, sprint_id))
        conn.commit()

        # Get AI Feedback
        prompt = f"The user just updated their sprint progress to {new_progress}%. Provide a short snarky, yet motivating response as Dot."
        ai_feedback = generate_ai_response(prompt)

        conn.close()
        return jsonify({'status': 'success', 'feedback': ai_feedback})
    else:
        entries = conn.execute('SELECT * FROM sprints ORDER BY id DESC').fetchall()
        conn.close()
        return jsonify([dict(entry) for entry in entries])

@app.route('/api/tasks', methods=['GET', 'POST', 'PUT'])
def api_tasks():
    conn = get_db_connection()
    if request.method == 'GET':
        tasks = conn.execute('SELECT * FROM medium_tasks').fetchall()
        conn.close()
        return jsonify([dict(t) for t in tasks])
    elif request.method == 'POST':
        data = request.json
        title = data.get('title')
        desc = data.get('description', '')

        # Optionally get Dot's opinion on the task
        prompt = f"The user just added a new task: '{title}'. Description: '{desc}'. Give a one sentence sarcastic but slightly motivating response."
        ai_msg = generate_ai_response(prompt)

        conn.execute('INSERT INTO chat_history (sender, message) VALUES (?, ?)', ('Dot', ai_msg))
        conn.execute('INSERT INTO medium_tasks (title, description) VALUES (?, ?)', (title, desc))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'dot_message': ai_msg})
    elif request.method == 'PUT':
        data = request.json
        task_id = data.get('id')
        status = data.get('status', 'done')
        conn.execute('UPDATE medium_tasks SET status = ? WHERE id = ?', (status, task_id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})

@app.route('/api/routines', methods=['GET', 'POST', 'PUT'])
def api_routines():
    conn = get_db_connection()
    if request.method == 'GET':
        tama = apply_tamagotchi_decay(conn)
        routines = conn.execute('SELECT * FROM routine_tasks').fetchall()
        conn.close()
        return jsonify({
            'routines': [dict(r) for r in routines],
            'tamagotchi': dict(tama) if tama else {},
            'pet_state': tamagotchi_state(tama)
        })
    elif request.method == 'POST':
        data = request.json
        category = data.get('category', 'routine')
        conn.execute('INSERT INTO routine_tasks (title, description, done_today, category) VALUES (?, ?, 0, ?)',
                     (data.get('title'), data.get('description', ''), category))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    elif request.method == 'PUT':
        # Mark routine as done, then boost the cat's stats (decay first so the boost is on top of current state)
        data = request.json
        routine_id = data.get('id')

        apply_tamagotchi_decay(conn)
        conn.execute('UPDATE routine_tasks SET done_today = 1 WHERE id = ?', (routine_id,))
        conn.execute('''
            UPDATE tamagotchi
            SET health = MIN(100, health + 10),
                happiness = MIN(100, happiness + 10),
                cleanliness = MIN(100, cleanliness + 10)
            WHERE id = 1
        ''')
        conn.commit()

        tama = conn.execute('SELECT * FROM tamagotchi WHERE id = 1').fetchone()

        msg = generate_ai_response("The user just completed a routine task and cared for their virtual cat. Give a very short, begrudgingly proud response as Dot.")
        conn.execute('INSERT INTO chat_history (sender, message) VALUES (?, ?)', ('Dot', msg))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'dot_message': msg, 'pet_state': tamagotchi_state(tama)})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    user_msg = data.get('message')
    context = data.get('context', '')

    prompt = f"Context: The user is currently focusing on this task: {context}. The user says: {user_msg}. Respond as Dot. If they are talking about something unrelated to the task, urge them to focus on the task so they can finish it."

    response = generate_ai_response(prompt)
    return jsonify({'response': response})

@app.route('/api/general_chat', methods=['GET', 'POST'])
def api_general_chat():
    conn = get_db_connection()
    if request.method == 'GET':
        history = conn.execute('SELECT * FROM chat_history WHERE archived = 0 ORDER BY id ASC').fetchall()
        conn.close()
        return jsonify([dict(h) for h in history])
    elif request.method == 'POST':
        data = request.json
        user_msg = data.get('message')
        conn.execute('INSERT INTO chat_history (sender, message, archived) VALUES (?, ?, 0)', ('User', user_msg))

        # Get memory contexts
        settings = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
        context_size = settings['context_size'] if settings and settings['context_size'] else 10

        memories = conn.execute('SELECT memory_text FROM permanent_memory').fetchall()
        mem_text = "\n".join([m['memory_text'] for m in memories])

        sprints = conn.execute('SELECT * FROM sprints WHERE status = "active"').fetchall()
        sprint_text = "\n".join([f"Sprint: {s['objective']} (Progress: {s['progress']}%)" for s in sprints])

        # Unarchived Chat History for context
        history = conn.execute('SELECT * FROM chat_history WHERE archived = 0 ORDER BY id DESC LIMIT ?', (context_size,)).fetchall()
        history.reverse()
        history_text = "\n".join([f"{h['sender']}: {h['message']}" for h in history if h['message'] != user_msg])

        system_context = f"PERMANENT MEMORY:\n{mem_text}\n\nACTIVE SPRINTS:\n{sprint_text}\n\nRECENT CHAT HISTORY:\n{history_text}\n\n"

        prompt = f"The user says: {user_msg}. Respond as Dot, taking into account the context provided."
        ai_msg = generate_ai_response(prompt, system_context)

        conn.execute('INSERT INTO chat_history (sender, message, archived) VALUES (?, ?, 0)', ('Dot', ai_msg))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'response': ai_msg})

@app.route('/api/remember', methods=['POST'])
def api_remember():
    conn = get_db_connection()
    data = request.json
    user_msg = data.get('message')
    conn.execute('INSERT INTO chat_history (sender, message, archived) VALUES (?, ?, 0)', ('User', user_msg))

    # Send all history (including archived) as context to remember
    all_history = conn.execute('SELECT * FROM chat_history ORDER BY id ASC').fetchall()
    history_text = "\n".join([f"{h['sender']}: {h['message']}" for h in all_history if h['message'] != user_msg])

    system_context = f"ENTIRE CHAT HISTORY:\n{history_text}\n\n"

    prompt = f"The user is asking: {user_msg}. Look through the ENTIRE CHAT HISTORY to find the answer. Respond as Dot, your abrasive but affectionate AI assistant personality."
    ai_msg = generate_ai_response(prompt, system_context)

    conn.execute('INSERT INTO chat_history (sender, message, archived) VALUES (?, ?, 0)', ('Dot', ai_msg))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'response': ai_msg})

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        conn.execute('''
            UPDATE settings
            SET deepseek_key = ?, context_size = ?
            WHERE id = 1
        ''', (data.get('deepseek_key'), data.get('context_size', 10)))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    else:
        settings = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
        conn.close()
        if settings:
            return jsonify(dict(settings))
        return jsonify({})

@app.route('/api/memory', methods=['GET', 'POST', 'DELETE'])
def api_memory():
    conn = get_db_connection()
    if request.method == 'GET':
        memories = conn.execute('SELECT * FROM permanent_memory').fetchall()
        conn.close()
        return jsonify([dict(m) for m in memories])
    elif request.method == 'POST':
        data = request.json
        conn.execute('INSERT INTO permanent_memory (memory_text) VALUES (?)', (data.get('memory_text'),))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    elif request.method == 'DELETE':
        data = request.json
        conn.execute('DELETE FROM permanent_memory WHERE id = ?', (data.get('id'),))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})

@app.route('/api/archive_chats', methods=['POST'])
def api_archive_chats():
    conn = get_db_connection()
    conn.execute('UPDATE chat_history SET archived = 1')
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/finish_intro', methods=['POST'])
def api_finish_intro():
    data = request.json or {}
    user_name = data.get('user_name', 'User')
    conn = get_db_connection()
    conn.execute('UPDATE settings SET first_run = 0, user_name = ? WHERE id = 1', (user_name,))

    # Auto-generate daily scrum event at 10:00 AM for today
    now = datetime.datetime.now()
    scrum_dt = datetime.datetime(now.year, now.month, now.day, 10, 0)
    if scrum_dt < now:
        scrum_dt += datetime.timedelta(days=1)

    conn.execute('INSERT INTO calendar_events (title, event_datetime, is_scrum) VALUES (?, ?, 1)',
                 ("Daily Scrum", scrum_dt.isoformat()))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/finance', methods=['GET', 'POST'])
def api_finance():
    conn = get_db_connection()
    if request.method == 'GET':
        # Group expenses by date (ignoring time) for the last 7 days roughly, or just all
        query = '''
            SELECT DATE(date) as date,
                   SUM(CASE WHEN category='spent' THEN amount ELSE 0 END) as total_spent,
                   SUM(CASE WHEN category='won' THEN amount ELSE 0 END) as total_won
            FROM expenses
            GROUP BY date
            ORDER BY date DESC
            LIMIT 7
        '''
        daily_totals = conn.execute(query).fetchall()
        conn.close()
        return jsonify({'daily_totals': [dict(d) for d in daily_totals]})

    elif request.method == 'POST':
        data = request.json
        amount = data.get('amount')
        desc = data.get('description')
        category = data.get('category')

        conn.execute('INSERT INTO expenses (amount, description, category) VALUES (?, ?, ?)', (amount, desc, category))
        conn.commit()

        # Determine if it's necessary to scold
        if category == 'spent':
            prompt = f"The user just logged an expense of ${amount} for '{desc}'. If this seems unnecessary, frivolous, or could have been avoided, SCOLD THEM MERCILESSLY as Dot, justifying why it's a bad idea and urging them to save money. If it's a basic necessity (like rent or basic groceries), be begrudgingly accepting but remind them to be frugal. Keep it under 3 sentences."
        else:
            prompt = f"The user just logged an income/gain of ${amount} for '{desc}'. Give a short, slightly approving but mostly demanding response as Dot, telling them not to squander it."

        ai_msg = generate_ai_response(prompt)

        # Log to chat history as well
        conn.execute('INSERT INTO chat_history (sender, message) VALUES (?, ?)', ('Dot', ai_msg))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'dot_message': ai_msg})

@app.route('/api/finance/advice', methods=['GET'])
def api_finance_advice():
    conn = get_db_connection()
    expenses = conn.execute('SELECT amount, description, category, date FROM expenses ORDER BY date DESC LIMIT 20').fetchall()
    conn.close()

    expense_text = "\n".join([f"{e['date']} - {e['category'].upper()}: ${e['amount']} ({e['description']})" for e in expenses])
    if not expense_text:
        expense_text = "No recent transactions."

    prompt = f"Here are the user's recent financial transactions:\n{expense_text}\n\nBased on this, provide a short, highly critical financial analysis and actionable guide on how to save money as Dot. Scold them if their expenses outweigh their income or if they are buying useless things. Justify your scolding based on the data. Be abrasive but genuinely helpful."

    advice = generate_ai_response(prompt)
    return jsonify({'status': 'success', 'advice': advice})

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    conn = get_db_connection()
    settings = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()

    first_run = bool(settings['first_run']) if settings and settings['first_run'] is not None else True

    # Check if MOTD needs updating (every hour)
    current_time = datetime.datetime.now()
    motd_time_str = settings['motd_time'] if settings else None
    motd_time = datetime.datetime.fromisoformat(motd_time_str) if motd_time_str else None

    motd = settings['motd'] if settings else None

    if not motd or not motd_time or (current_time - motd_time).total_seconds() > 3600:
        if settings and settings['deepseek_key']:
            motd = generate_ai_response("Provide a random 'Message of the Hour' that is funny, slightly snarky, and motivational. Keep it under 2 sentences.")
        else:
            motd = "[System]: Please configure your DeepSeek API key in System Settings to enable Dot's motivational messages."

        conn.execute('UPDATE settings SET motd = ?, motd_time = ? WHERE id = 1', (motd, current_time.isoformat()))
        conn.commit()

    # Calculate stats
    total_tasks = conn.execute('SELECT COUNT(*) FROM medium_tasks').fetchone()[0]
    completed_tasks = conn.execute("SELECT COUNT(*) FROM medium_tasks WHERE status = 'done'").fetchone()[0]

    total_routines = conn.execute('SELECT COUNT(*) FROM routine_tasks').fetchone()[0]
    completed_routines = conn.execute('SELECT COUNT(*) FROM routine_tasks WHERE done_today = 1').fetchone()[0]

    sprint_count = conn.execute('SELECT COUNT(*) FROM sprints').fetchone()[0]

    tama = apply_tamagotchi_decay(conn)

    conn.close()

    return jsonify({
        'first_run': first_run,
        'motd': motd,
        'stats': {
            'tasks': {'total': total_tasks, 'completed': completed_tasks},
            'routines': {'total': total_routines, 'completed': completed_routines},
            'sprint_count': sprint_count
        },
        'tamagotchi': dict(tama) if tama else {},
        'pet_state': tamagotchi_state(tama)
    })


@app.route('/api/tamagotchi/color', methods=['POST'])
def api_tamagotchi_color():
    conn = get_db_connection()
    try:
        tama = conn.execute('SELECT * FROM tamagotchi WHERE id = 1').fetchone()
        current = tama['color'] if tama and tama['color'] else 'gold'
        idx = TAMA_COLORS.index(current) if current in TAMA_COLORS else -1
        new_color = TAMA_COLORS[(idx + 1) % len(TAMA_COLORS)]
        conn.execute('UPDATE tamagotchi SET color = ? WHERE id = 1', (new_color,))
        conn.commit()
        return jsonify({'status': 'success', 'color': new_color})
    finally:
        conn.close()


@app.route('/api/notifications', methods=['GET'])
def api_notifications():
    conn = get_db_connection()
    now = datetime.datetime.now()
    notifications = []

    # 15 min warning
    warning_15 = now + datetime.timedelta(minutes=15)
    events_15 = conn.execute('''SELECT * FROM calendar_events
                                WHERE event_datetime > ?
                                AND event_datetime <= ?
                                AND notified_15 = 0''',
                             (now.isoformat(), warning_15.isoformat())).fetchall()

    for e in events_15:
        notifications.append({"message": f"15 minutes until: {e['title']}"})
        conn.execute('UPDATE calendar_events SET notified_15 = 1 WHERE id = ?', (e['id'],))

    # 5 min warning
    warning_5 = now + datetime.timedelta(minutes=5)
    events_5 = conn.execute('''SELECT * FROM calendar_events
                               WHERE event_datetime > ?
                               AND event_datetime <= ?
                               AND notified_5 = 0''',
                            (now.isoformat(), warning_5.isoformat())).fetchall()

    for e in events_5:
        notifications.append({"message": f"5 minutes until: {e['title']}"})
        conn.execute('UPDATE calendar_events SET notified_5 = 1 WHERE id = ?', (e['id'],))

    conn.commit()
    conn.close()
    return jsonify({"notifications": notifications})

@app.route('/api/calendar', methods=['GET', 'POST', 'DELETE'])
def api_calendar():
    conn = get_db_connection()

    try:
        if request.method == 'GET':
            events = conn.execute('SELECT * FROM calendar_events ORDER BY event_datetime ASC').fetchall()
            return jsonify([dict(e) for e in events])

        elif request.method == 'POST':
            data = request.json
            title = data.get('title')
            dt_str = data.get('datetime')
            conn.execute('INSERT INTO calendar_events (title, event_datetime) VALUES (?, ?)', (title, dt_str))
            conn.commit()
            return jsonify({"status": "success"})

        elif request.method == 'DELETE':
            event_id = request.json.get('id')
            conn.execute('DELETE FROM calendar_events WHERE id = ?', (event_id,))
            conn.commit()
            return jsonify({"status": "deleted"})
    finally:
        conn.close()

@app.route('/api/scrum', methods=['GET', 'POST'])
def api_scrum():
    conn = get_db_connection()
    try:
        if request.method == 'GET':
            entries = conn.execute('SELECT * FROM scrum_entries ORDER BY id DESC LIMIT 30').fetchall()
            impediments = conn.execute('SELECT * FROM impediments ORDER BY resolved ASC, id DESC').fetchall()
            overcome = conn.execute('SELECT COUNT(*) FROM impediments WHERE resolved = 1').fetchone()[0]
            return jsonify({
                'entries': [dict(e) for e in entries],
                'impediments': [dict(i) for i in impediments],
                'overcome_count': overcome
            })

        # POST: log a daily stand-up
        data = request.json
        sprint_id = data.get('sprint_id') or None
        yesterday = data.get('yesterday', '')
        today = data.get('today', '')
        impediments = data.get('impediments', '')

        sprint_text = ""
        if sprint_id:
            s = conn.execute('SELECT * FROM sprints WHERE id = ?', (sprint_id,)).fetchone()
            if s:
                sprint_text = f"Sprint goal: {s['objective']} (currently {s['progress']}% complete)."

        prompt = (
            f"This is the user's Daily Scrum stand-up. {sprint_text}\n"
            f"1) What they did yesterday: {yesterday}\n"
            f"2) What they'll do today: {today}\n"
            f"3) Impediments: {impediments or 'None'}\n\n"
            "Respond as Dot: acknowledge yesterday's progress, sharpen today's plan into something concrete and doable, "
            "and if there are impediments, give one or two practical tips to get past them. Keep it punchy, under 5 sentences."
        )
        feedback = generate_ai_response(prompt)

        conn.execute('''INSERT INTO scrum_entries (sprint_id, yesterday, today, impediments, ai_feedback)
                        VALUES (?, ?, ?, ?, ?)''',
                     (sprint_id, yesterday, today, impediments, feedback))

        # Log a real impediment record if the user reported something meaningful
        imp = (impediments or '').strip()
        if imp and imp.lower() not in ('none', 'no', 'n/a', 'na', 'nothing', 'none.'):
            conn.execute('INSERT INTO impediments (sprint_id, description) VALUES (?, ?)', (sprint_id, imp))

        conn.execute('INSERT INTO chat_history (sender, message) VALUES (?, ?)', ('Dot', feedback))
        conn.commit()
        return jsonify({'status': 'success', 'feedback': feedback})
    finally:
        conn.close()


@app.route('/api/impediments/resolve', methods=['POST'])
def api_resolve_impediment():
    conn = get_db_connection()
    try:
        imp_id = request.json.get('id')
        conn.execute('UPDATE impediments SET resolved = 1 WHERE id = ?', (imp_id,))
        conn.commit()
        overcome = conn.execute('SELECT COUNT(*) FROM impediments WHERE resolved = 1').fetchone()[0]
        msg = generate_ai_response(
            f"The user just overcame an impediment. They have now overcome {overcome} obstacle(s) in total. "
            "Give a short, begrudgingly proud one-liner reminding them they made it through and to keep going."
        )
        return jsonify({'status': 'success', 'overcome_count': overcome, 'dot_message': msg})
    finally:
        conn.close()


@app.route('/api/tasks/subtasks', methods=['GET', 'POST', 'PUT'])
def api_subtasks():
    conn = get_db_connection()
    try:
        if request.method == 'GET':
            task_id = request.args.get('task_id')
            subs = conn.execute('SELECT * FROM subtasks WHERE task_id = ? ORDER BY id ASC', (task_id,)).fetchall()
            return jsonify([dict(s) for s in subs])
        elif request.method == 'POST':
            data = request.json
            conn.execute('INSERT INTO subtasks (task_id, title) VALUES (?, ?)',
                         (data.get('task_id'), data.get('title')))
            conn.commit()
            return jsonify({'status': 'success'})
        elif request.method == 'PUT':
            data = request.json
            conn.execute('UPDATE subtasks SET done = ? WHERE id = ?',
                         (1 if data.get('done') else 0, data.get('id')))
            conn.commit()
            return jsonify({'status': 'success'})
    finally:
        conn.close()


@app.route('/api/tasks/deconstruct', methods=['POST'])
def api_deconstruct():
    conn = get_db_connection()
    try:
        task_id = request.json.get('task_id')
        task = conn.execute('SELECT * FROM medium_tasks WHERE id = ?', (task_id,)).fetchone()
        if not task:
            return jsonify({'status': 'error', 'message': 'Task not found.'}), 404

        prompt = (
            "Break this task into 3 to 5 concrete micro-steps the user can tackle one at a time.\n"
            f"Task: {task['title']}\nDescription: {task['description'] or 'N/A'}\n\n"
            "Respond with ONLY the micro-steps, one per line. No numbering, no preamble, no commentary. "
            "Each step should be a short, actionable phrase."
        )
        response = generate_ai_response(prompt)

        # If the AI errored (e.g. missing API key), surface it instead of creating junk steps.
        if response.strip().startswith('[DOT]'):
            return jsonify({'status': 'error', 'message': response})

        steps = []
        for line in response.splitlines():
            line = re.sub(r'^\s*(\d+[\.\)]|[-*•])\s*', '', line.strip()).strip()
            if line:
                steps.append(line)
        steps = steps[:5]

        for s in steps:
            conn.execute('INSERT INTO subtasks (task_id, title) VALUES (?, ?)', (task_id, s))
        conn.commit()

        subs = conn.execute('SELECT * FROM subtasks WHERE task_id = ? ORDER BY id ASC', (task_id,)).fetchall()
        return jsonify({'status': 'success', 'subtasks': [dict(s) for s in subs]})
    finally:
        conn.close()


@app.route('/api/focus/nudge', methods=['POST'])
def api_focus_nudge():
    data = request.json or {}
    task = data.get('task') or 'their current task'
    prompt = (
        f"The user has been focusing on '{task}' for a while now. Send a short motivational nudge as Dot — "
        "remind them that if they're blocked they can ask you for help, and push them to keep going. One or two sentences."
    )
    msg = generate_ai_response(prompt)
    return jsonify({'message': msg})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
