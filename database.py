import sqlite3
import hashlib

DB_NAME = "quiz_database.db"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. สร้างตารางผู้ใช้งาน
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. เพิ่ม user_id เข้าไปในตารางข้อสอบ เพื่อแยกของใครของมัน
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            total_questions INTEGER,
            latest_score INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_set_id INTEGER,
            question_text TEXT,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT, option_e TEXT,
            correct_answer TEXT,
            FOREIGN KEY (quiz_set_id) REFERENCES quiz_sets (id)
        )
    ''')
    conn.commit()
    conn.close()

# --- ระบบ User ---
def create_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hash_password(password)))
        conn.commit()
        user_id = cursor.lastrowid
        return {"status": "success", "user_id": user_id, "username": username}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "มีชื่อผู้ใช้นี้ในระบบแล้ว"}
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE username = ? AND password = ?', (username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"status": "success", "user_id": user[0], "username": user[1]}
    return {"status": "error", "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}

# --- ระบบข้อสอบ (แยกตาม user_id) ---
def save_quiz_to_db(user_id, filename, quiz_data_list):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    total_q = len(quiz_data_list)
    
    cursor.execute('INSERT INTO quiz_sets (user_id, filename, total_questions) VALUES (?, ?, ?)', (user_id, filename, total_q))
    quiz_set_id = cursor.lastrowid
    
    for item in quiz_data_list:
        options = item.get('options', {})
        cursor.execute('''
            INSERT INTO questions (
                quiz_set_id, question_text, option_a, option_b, option_c, option_d, option_e, correct_answer
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (quiz_set_id, item.get('question'), options.get('a'), options.get('b'), options.get('c'), options.get('d'), options.get('e'), item.get('correctAnswer')))
        
    conn.commit()
    conn.close()
    return quiz_set_id

def get_all_quiz_sets(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, filename, total_questions, latest_score, created_at FROM quiz_sets WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for r in rows:
        history.append({"id": r[0], "filename": r[1], "total_questions": r[2], "latest_score": r[3], "created_at": r[4]})
    return history

def get_quiz_by_id(quiz_set_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT question_text, option_a, option_b, option_c, option_d, option_e, correct_answer FROM questions WHERE quiz_set_id = ?', (quiz_set_id,))
    rows = cursor.fetchall()
    conn.close()
    
    quiz_data = [{"question": r[0], "options": {"a": r[1], "b": r[2], "c": r[3], "d": r[4], "e": r[5]}, "correctAnswer": r[6]} for r in rows]
    return quiz_data

def update_score(quiz_id, score):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE quiz_sets SET latest_score = ? WHERE id = ?', (score, quiz_id))
    conn.commit()
    conn.close()