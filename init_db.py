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
            motd TEXT,
            motd_time DATETIME
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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Scrum answers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS scrum_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            yesterday TEXT,
            today TEXT,
            impediments TEXT
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

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print(f"Database initialized successfully at {db_utils.get_db_path()}")
