import os
from flask import Flask, render_template

app = Flask(__name__)

import sqlite3
from flask import request, jsonify

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

from ai_provider import generate_ai_response
import datetime

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

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        conn.execute('''
            UPDATE settings
            SET openai_key = ?, gemini_key = ?, deepseek_key = ?, active_provider = ?
            WHERE id = 1
        ''', (data.get('openai_key'), data.get('gemini_key'), data.get('deepseek_key'), data.get('active_provider')))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    else:
        settings = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
        conn.close()
        if settings:
            return jsonify(dict(settings))
        return jsonify({})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
