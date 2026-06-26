import sqlite3
import db_utils

def init_db():
    conn = db_utils.get_db_connection()
    c = conn.cursor()

    # Settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deepseek_key TEXT,
            first_run BOOLEAN DEFAULT 1,
            context_size INTEGER DEFAULT 10,
            motd TEXT,
            motd_time DATETIME,
            user_name TEXT DEFAULT 'User'
        )
    ''')

    # Calendar Events table
    c.execute('''
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            event_datetime DATETIME,
            notified_15 BOOLEAN DEFAULT 0,
            notified_5 BOOLEAN DEFAULT 0,
            is_scrum BOOLEAN DEFAULT 0
        )
    ''')

    # Ensure at least one settings row exists
    c.execute('SELECT COUNT(*) FROM settings')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO settings (first_run) VALUES (1)')

    # Chat History table
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            archived BOOLEAN DEFAULT 0
        )
    ''')

    # Sprints table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            objective TEXT,
            start_date TEXT,
            end_date TEXT,
            progress INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        )
    ''')

    # Permanent Memory table
    c.execute('''
        CREATE TABLE IF NOT EXISTS permanent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_text TEXT
        )
    ''')

    # Medium Tasks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS medium_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')

    # Routine Tasks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS routine_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            done_today BOOLEAN DEFAULT 0
        )
    ''')

    # Tamagotchi status table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tamagotchi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            health INTEGER DEFAULT 100,
            happiness INTEGER DEFAULT 100,
            cleanliness INTEGER DEFAULT 100
        )
    ''')

    # Ensure tamagotchi row exists
    c.execute('SELECT COUNT(*) FROM tamagotchi')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO tamagotchi (health, happiness, cleanliness) VALUES (100, 100, 100)')

    # Economy & Finance table
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            description TEXT,
            category TEXT,
            date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Daily Scrum stand-up entries
    c.execute('''
        CREATE TABLE IF NOT EXISTS scrum_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sprint_id INTEGER,
            entry_date DATE DEFAULT CURRENT_DATE,
            yesterday TEXT,
            today TEXT,
            impediments TEXT,
            ai_feedback TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Impediments (tracked so Dot can celebrate the user overcoming them)
    c.execute('''
        CREATE TABLE IF NOT EXISTS impediments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sprint_id INTEGER,
            description TEXT,
            resolved INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Sub-tasks: the 3-5 micro-steps a medium task is deconstructed into
    c.execute('''
        CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            title TEXT,
            done INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print(f"Database initialized successfully at {db_utils.get_db_path()}")
