import os
import datetime
from flask import Flask, render_template, request, jsonify
import sqlite3
import db_utils
from ai_provider import generate_ai_response

app = Flask(__name__)

def get_db_connection():
    return db_utils.get_db_connection()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scrum', methods=['GET', 'POST'])
def api_scrum():
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        today = datetime.date.today().isoformat()

        conn.execute('''
            INSERT INTO scrum_entries (date, yesterday, today, impediments)
            VALUES (?, ?, ?, ?)
        ''', (today, data.get('yesterday'), data.get('today'), data.get('impediments')))
        conn.commit()

        # Get AI Feedback
        prompt = f"The user just submitted their daily scrum. Yesterday they did: {data.get('yesterday')}. Today they plan to: {data.get('today')}. Impediments: {data.get('impediments')}. Provide a short snarky, yet motivating response as Dot."
        ai_feedback = generate_ai_response(prompt)

        conn.close()
        return jsonify({'status': 'success', 'feedback': ai_feedback})
    else:
        entries = conn.execute('SELECT * FROM scrum_entries ORDER BY id DESC LIMIT 5').fetchall()
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
        routines = conn.execute('SELECT * FROM routine_tasks').fetchall()
        tama = conn.execute('SELECT * FROM tamagotchi WHERE id = 1').fetchone()
        conn.close()
        return jsonify({
            'routines': [dict(r) for r in routines],
            'tamagotchi': dict(tama) if tama else {}
        })
    elif request.method == 'POST':
        data = request.json
        conn.execute('INSERT INTO routine_tasks (title, description, done_today) VALUES (?, ?, 0)',
                     (data.get('title'), data.get('description', '')))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    elif request.method == 'PUT':
        # Mark routine as done, boost tamagotchi stats
        data = request.json
        routine_id = data.get('id')

        conn.execute('UPDATE routine_tasks SET done_today = 1 WHERE id = ?', (routine_id,))
        # Simple tamagotchi stat boost logic
        conn.execute('''
            UPDATE tamagotchi
            SET health = MIN(100, health + 10),
                happiness = MIN(100, happiness + 10),
                cleanliness = MIN(100, cleanliness + 10)
            WHERE id = 1
        ''')
        conn.commit()

        # Optionally, get a Dot response if health is low, etc (skipped for simplicity, keeping it positive here)
        msg = generate_ai_response("The user just completed a routine task and fed their virtual cat. Give a very short, begrudgingly proud response as Dot.")
        conn.execute('INSERT INTO chat_history (sender, message) VALUES (?, ?)', ('Dot', msg))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'dot_message': msg})

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
        history = conn.execute('SELECT * FROM chat_history ORDER BY id ASC').fetchall()
        conn.close()
        return jsonify([dict(h) for h in history])
    elif request.method == 'POST':
        data = request.json
        user_msg = data.get('message')
        conn.execute('INSERT INTO chat_history (sender, message) VALUES (?, ?)', ('User', user_msg))

        prompt = f"The user says: {user_msg}. Respond as Dot, your abrasive but affectionate AI assistant personality."
        ai_msg = generate_ai_response(prompt)

        conn.execute('INSERT INTO chat_history (sender, message) VALUES (?, ?)', ('Dot', ai_msg))
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
            SET deepseek_key = ?
            WHERE id = 1
        ''', (data.get('deepseek_key'),))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    else:
        settings = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
        conn.close()
        if settings:
            return jsonify(dict(settings))
        return jsonify({})

@app.route('/api/finish_intro', methods=['POST'])
def api_finish_intro():
    conn = get_db_connection()
    conn.execute('UPDATE settings SET first_run = 0 WHERE id = 1')
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

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

    scrum_count = conn.execute('SELECT COUNT(*) FROM scrum_entries').fetchone()[0]

    tama = conn.execute('SELECT * FROM tamagotchi WHERE id = 1').fetchone()

    conn.close()

    return jsonify({
        'first_run': first_run,
        'motd': motd,
        'stats': {
            'tasks': {'total': total_tasks, 'completed': completed_tasks},
            'routines': {'total': total_routines, 'completed': completed_routines},
            'scrum_count': scrum_count
        },
        'tamagotchi': dict(tama) if tama else {}
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
