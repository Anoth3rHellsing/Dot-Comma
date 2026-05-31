import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openai_key TEXT,
            gemini_key TEXT,
            deepseek_key TEXT,
            active_provider TEXT DEFAULT 'openai'
        )
    ''')

    # Ensure at least one settings row exists
    c.execute('SELECT COUNT(*) FROM settings')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO settings (active_provider) VALUES ("openai")')

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
    print("Database initialized successfully.")
