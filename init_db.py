import datetime
import db_utils


def _ensure_column(c, table, column, ddl):
    """Add a column to an existing table if it isn't there yet (lightweight migration)."""
    existing = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


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
            user_name TEXT DEFAULT 'User',
            jira_url TEXT,
            jira_email TEXT,
            jira_token TEXT,
            jira_auth_type TEXT DEFAULT 'bearer',
            jira_api_version TEXT DEFAULT '2',
            jira_filters TEXT,
            jira_tempo_url TEXT,
            jira_high_priority TEXT DEFAULT 'Open,Waiting for Support',
            jira_poll_seconds INTEGER DEFAULT 60
        )
    ''')

    # Sensible defaults pre-filled for the current cogep Jira Server setup.
    # After the Cloud migration: change jira_url -> ...atlassian.net, jira_api_version -> 3,
    # jira_auth_type -> basic, set jira_email, and update the filter IDs in Settings.
    JIRA_DEFAULTS = {
        'jira_url': 'https://jira.cogep.com',
        'jira_auth_type': 'bearer',
        'jira_api_version': '2',
        'jira_filters': '{"new": "10712", "assigned": "11419", "waiting": "12004"}',
        'jira_tempo_url': 'https://jira.cogep.com/secure/Tempo.jspa#/my-work/week',
        'jira_high_priority': 'Open,Waiting for Support',
    }

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

    # Ensure at least one settings row exists (with Jira defaults pre-filled)
    c.execute('SELECT COUNT(*) FROM settings')
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO settings
                     (first_run, jira_url, jira_auth_type, jira_api_version, jira_filters, jira_tempo_url, jira_high_priority)
                     VALUES (1, ?, ?, ?, ?, ?, ?)''',
                  (JIRA_DEFAULTS['jira_url'], JIRA_DEFAULTS['jira_auth_type'], JIRA_DEFAULTS['jira_api_version'],
                   JIRA_DEFAULTS['jira_filters'], JIRA_DEFAULTS['jira_tempo_url'], JIRA_DEFAULTS['jira_high_priority']))

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

    # Medium Tasks table (jira_key links a task back to an imported Jira issue)
    c.execute('''
        CREATE TABLE IF NOT EXISTS medium_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending',
            jira_key TEXT
        )
    ''')

    # Routine Tasks table (category distinguishes ordinary routines from medications;
    # reminder_interval is minutes between desktop reminders, 0 = no reminder)
    c.execute('''
        CREATE TABLE IF NOT EXISTS routine_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            done_today BOOLEAN DEFAULT 0,
            category TEXT DEFAULT 'routine',
            reminder_interval INTEGER DEFAULT 0
        )
    ''')

    # Tamagotchi status table (color varies; last_update drives hourly stat decay)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tamagotchi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            health INTEGER DEFAULT 100,
            happiness INTEGER DEFAULT 100,
            cleanliness INTEGER DEFAULT 100,
            color TEXT DEFAULT 'gold',
            last_update DATETIME
        )
    ''')

    now_str = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')

    # Ensure tamagotchi row exists
    c.execute('SELECT COUNT(*) FROM tamagotchi')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO tamagotchi (health, happiness, cleanliness, color, last_update) VALUES (100, 100, 100, ?, ?)',
                  ('gold', now_str))

    # --- Migrations for databases created before these columns existed ---
    _ensure_column(c, 'routine_tasks', 'category', "category TEXT DEFAULT 'routine'")
    _ensure_column(c, 'routine_tasks', 'reminder_interval', "reminder_interval INTEGER DEFAULT 0")
    _ensure_column(c, 'tamagotchi', 'color', "color TEXT DEFAULT 'gold'")
    _ensure_column(c, 'tamagotchi', 'last_update', "last_update DATETIME")
    _ensure_column(c, 'settings', 'jira_url', "jira_url TEXT")
    _ensure_column(c, 'settings', 'jira_email', "jira_email TEXT")
    _ensure_column(c, 'settings', 'jira_token', "jira_token TEXT")
    _ensure_column(c, 'settings', 'jira_auth_type', "jira_auth_type TEXT DEFAULT 'bearer'")
    _ensure_column(c, 'settings', 'jira_api_version', "jira_api_version TEXT DEFAULT '2'")
    _ensure_column(c, 'settings', 'jira_filters', "jira_filters TEXT")
    _ensure_column(c, 'settings', 'jira_tempo_url', "jira_tempo_url TEXT")
    _ensure_column(c, 'settings', 'jira_high_priority', "jira_high_priority TEXT DEFAULT 'Open,Waiting for Support'")
    _ensure_column(c, 'settings', 'jira_poll_seconds', "jira_poll_seconds INTEGER DEFAULT 60")
    _ensure_column(c, 'medium_tasks', 'jira_key', "jira_key TEXT")
    # backfill Jira defaults for pre-existing settings rows that have them empty
    c.execute("UPDATE settings SET jira_url = ? WHERE jira_url IS NULL OR jira_url = ''", (JIRA_DEFAULTS['jira_url'],))
    c.execute("UPDATE settings SET jira_filters = ? WHERE jira_filters IS NULL OR jira_filters = ''", (JIRA_DEFAULTS['jira_filters'],))
    c.execute("UPDATE settings SET jira_tempo_url = ? WHERE jira_tempo_url IS NULL OR jira_tempo_url = ''", (JIRA_DEFAULTS['jira_tempo_url'],))
    c.execute('UPDATE tamagotchi SET last_update = ? WHERE last_update IS NULL', (now_str,))
    c.execute("UPDATE tamagotchi SET color = 'gold' WHERE color IS NULL")

    # Seed default health-reminder routines on a brand-new database (first run only)
    c.execute('SELECT first_run FROM settings WHERE id = 1')
    first_row = c.fetchone()
    c.execute('SELECT COUNT(*) FROM routine_tasks')
    if first_row and first_row[0] and c.fetchone()[0] == 0:
        defaults = [
            ('Drink water', 'Stay hydrated.', 60),
            ('Stand up & move', 'Get the blood flowing.', 90),
            ('Rest your eyes (20-20-20)', 'Look 20ft away for 20 seconds.', 120),
            ('Eat something', 'Fuel up properly.', 240),
        ]
        for title, desc, interval in defaults:
            c.execute('''INSERT INTO routine_tasks (title, description, done_today, category, reminder_interval)
                         VALUES (?, ?, 0, 'routine', ?)''', (title, desc, interval))

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
