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

    sprint_count = conn.execute('SELECT COUNT(*) FROM sprints').fetchone()[0]

    tama = conn.execute('SELECT * FROM tamagotchi WHERE id = 1').fetchone()

    conn.close()

    return jsonify({
        'first_run': first_run,
        'motd': motd,
        'stats': {
            'tasks': {'total': total_tasks, 'completed': completed_tasks},
            'routines': {'total': total_routines, 'completed': completed_routines},
            'sprint_count': sprint_count
        },
        'tamagotchi': dict(tama) if tama else {}
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
