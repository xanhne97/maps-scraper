# models.py
import sqlite3

def init_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    address TEXT,
                    phone TEXT
                )''')
    conn.commit()
    conn.close()

def save_result(name, address, phone):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('INSERT INTO results (name, address, phone) VALUES (?, ?, ?)', (name, address, phone))
    conn.commit()
    conn.close()

def get_all_results():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('SELECT name, address, phone FROM results ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return [{'name': row[0], 'address': row[1], 'phone': row[2]} for row in rows]
