import os
import sqlite3

def get_db_path():
    appdata = os.environ.get('APPDATA')
    if appdata:
        db_dir = os.path.join(appdata, 'DotAndComma')
    else:
        db_dir = os.path.expanduser('~/.dotandcomma')
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    return os.path.join(db_dir, 'database.db')

def get_db_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn
