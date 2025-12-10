import sqlite3

DB_FILE = 'shared_calendar.db'
MAX_USERS = 10

def init_db():
    """Inizializza il database creando le tabelle necessarie."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Tabella Gruppi (Semplicistica, assumiamo un solo gruppo per ora)
    c.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            share_link TEXT UNIQUE
        )
    ''')
    # Assicurati che esista almeno un gruppo di default
    c.execute("INSERT OR IGNORE INTO groups (id, name, share_link) VALUES (1, 'Calendario Condiviso', 'link_condiviso_1234')")

    # Tabella Utenti
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            nickname TEXT UNIQUE NOT NULL,
            group_id INTEGER,
            FOREIGN KEY (group_id) REFERENCES groups(id)
        )
    ''')

    # Tabella Attività
    c.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            creator_id INTEGER,
            FOREIGN KEY (creator_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    """Restituisce una connessione al database."""
    return sqlite3.connect(DB_FILE)

def add_user(nickname, group_id=1):
    """Aggiunge un nuovo utente al gruppo."""
    conn = get_db_connection()
    c = conn.cursor()
    # Verifica il limite di 10 utenti
    c.execute("SELECT COUNT(*) FROM users WHERE group_id = ?", (group_id,))
    if c.fetchone()[0] >= MAX_USERS:
        conn.close()
        return False, f"Limite massimo di {MAX_USERS} utenti raggiunto per questo calendario."

    try:
        c.execute("INSERT INTO users (nickname, group_id) VALUES (?, ?)", (nickname, group_id))
        conn.commit()
        return True, c.lastrowid
    except sqlite3.IntegrityError:
        return False, "Nickname già in uso."
    finally:
        conn.close()

def add_activity(title, desc, start, end, creator_id):
    """Aggiunge una nuova attività."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO activities (title, description, start_time, end_time, creator_id)
        VALUES (?, ?, ?, ?, ?)
    """, (title, desc, start, end, creator_id))
    conn.commit()
    conn.close()

def get_activities():
    """Recupera tutte le attività con il nome del creatore."""
    conn = get_db_connection()
    # Utilizziamo JOIN per ottenere il nickname del creatore
    activities = conn.execute("""
        SELECT a.*, u.nickname 
        FROM activities a
        JOIN users u ON a.creator_id = u.id
        ORDER BY a.start_time
    """).fetchall()
    conn.close()
    return activities

def get_users(group_id=1):
    """Recupera tutti gli utenti del gruppo."""
    conn = get_db_connection()
    users = conn.execute("SELECT id, nickname FROM users WHERE group_id = ?", (group_id,)).fetchall()
    conn.close()
    return users
