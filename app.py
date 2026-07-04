import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import re
import time
import socket

UPLOAD_FOLDER = "static/uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.secret_key = "secret123"

def is_internet_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)  # Google DNS
        return True
    except OSError:
        return False

@app.before_request
def check_internet():
    # Allow static files
    if request.endpoint == 'static':
        return
    
    if not is_internet_available():
        return redirect(url_for('no_internet'))
    
@app.route('/no_internet')
def no_internet():
    return render_template("no_internet.html")


def is_valid_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True

# 🔹 Create Database & Tables
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            name TEXT,
            email TEXT UNIQUE,
            branch TEXT,
            student TEXT,
            password TEXT,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doubts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            branch TEXT,
            subject TEXT,
            question TEXT,
            file TEXT,
            answer TEXT,
            teacher_file TEXT,
            teacher_name TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
    CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doubt_id INTEGER,
    teacher_name TEXT,
    answer TEXT,
    file TEXT,
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

    conn.commit()
    conn.close()


# Home Page
@app.route("/")
def home():
    return render_template("index.html")

# 🔹 Register Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    
    if request.method == 'POST':
        role = request.form['role']
        name = request.form['name']
        email = request.form['email']
        branch = request.form['branch']
        password = request.form['password']
        
        
        if not is_valid_password(password):
            flash("Password must contain 8 chars, 1 capital, 1 number, 1 symbol", "error")
            return redirect(url_for('register'))
    
        hashed_password = generate_password_hash(password)
        
        from datetime import datetime
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
        
            cursor.execute('''
                INSERT INTO users (role, name, email, branch, password, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (role, name, email, branch, hashed_password, created_at))

            conn.commit()
            conn.close()
    
            flash("✅ Registered successfully! Please login.", "success")
            return redirect(url_for('login'))

        except Exception as e:
            print("ERROR:", e)
            flash("❌ Email already exists!")
            
            return redirect(url_for('register'))

    return render_template('register.html')


# 🔹 Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '').lower()

        if not email or not password or not role:
            flash("All fields are required","error")
            return redirect(url_for('login'))

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()

        conn.close()

        # ❌ user not found
        if user is None:
            flash("Email not found","error")
            return redirect(url_for('login'))

        # 🔍 DEBUG (safe now)
        print("USER:", user)

        db_password = user[6]   # ✅ FIXED
        db_role = user[1].strip().lower()  # ✅ FIXED

        # password check
        if not check_password_hash(db_password, password):
            flash("Wrong password","error")
            return redirect(url_for('login'))

        # role check
        if db_role != role:
            flash("Role mismatch")
            return redirect(url_for('login'))

        # session
        session['name'] = user[2]
        session['email'] = user[3]
        session['role'] = db_role
        session['branch'] = user[4]

        # redirect
        if db_role == "student":
            return redirect(url_for('student_dashboard'))
        elif db_role == "teacher":
            return redirect(url_for('teacher_dashboard'))
        elif db_role == "admin":
            return redirect(url_for('admin_dashboard'))

        flash("Invalid role","error")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # 🔹 Step 1: Check if email exists
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()

        if not user:
            flash("❌ Email not registered", "error")
            conn.close()
            return render_template('forgot_password.html')

        # 🔹 Step 2: If password fields submitted
        if new_password and confirm_password:
            if new_password != confirm_password:
                flash("❌ Passwords do not match", "error")
                conn.close()
                return render_template('forgot_password.html', show_reset=True, email=email)

            if not is_valid_password(new_password):
                flash("Password must contain 8 chars, 1 capital, 1 number, 1 symbol", "error")
                conn.close()
                return render_template('forgot_password.html', show_reset=True, email=email)

            hashed = generate_password_hash(new_password)

            cursor.execute("UPDATE users SET password=? WHERE email=?", (hashed, email))
            conn.commit()
            conn.close()

            flash("✅ Password changed successfully! Please login.", "success")
            return redirect(url_for('login'))

        conn.close()

        # 🔹 Show reset form
        return render_template('forgot_password.html', show_reset=True, email=email)

    return render_template('forgot_password.html')

# 🔹 Student Dashboard
@app.route('/student_dashboard')
def student_dashboard():
    if 'name' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.id, d.subject, d.branch, d.student_name, d.question, d.file,
        r.answer, r.file, r.teacher_name, r.time, d.date
        FROM doubts d
        LEFT JOIN responses r ON d.id = r.doubt_id
        WHERE d.student_name = ?
        ORDER BY d.id DESC
    """, (session['name'],))

    doubts = cursor.fetchall()
    conn.close()

    return render_template('student_dashboard.html', name=session['name'], doubts=doubts)


# 🔹 Submit Doubt
@app.route('/submit_doubt', methods=['POST'])
def submit_doubt():
    subject = request.form['subject']
    question = request.form['question']
    file = request.files['file']
    
    UPLOAD_FOLDER = os.path.join(app.root_path,'static/uploads')
  
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)  
        
    file = request.files.get('file')
    filename = None
    
    if file and file.filename != "":
        filename = str(int(time.time())) + "_" + secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO doubts (student_name, branch, subject, question, file)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['name'], session['branch'], subject, question, filename))

    conn.commit()
    conn.close()
    
    flash("Doubt submitted succesfully!","success")

    return redirect('/student_dashboard')

# ================= TEACHER DASHBOARD =================
@app.route("/teacher_dashboard")
def teacher_dashboard():
    if "name" not in session:
        return redirect("/login")

    branch = session.get("branch")  # MCA, BCA, etc.

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Pending doubts (no answer)
    cursor.execute("""
        SELECT d.* FROM doubts d
        WHERE d.branch=? AND d.id NOT IN (SELECT doubt_id FROM responses)
        ORDER BY d.id DESC
    """, (branch,))
    pending = cursor.fetchall()

    # Responded doubts
    cursor.execute("""
        SELECT r.id, d.id, d.student_name, d.branch, d.subject,
        d.question, d.file, r.answer, r.file, r.teacher_name, r.time
        FROM doubts d JOIN responses r ON d.id = r.doubt_id
        WHERE r.teacher_name = ?
        ORDER BY r.id DESC
    """, (session['name'],))
    responded = cursor.fetchall()

    conn.close()

    return render_template("teacher_dashboard.html",
                           name=session["name"],
                           branch=branch,
                           pending=pending,
                           responded=responded)


# ================= SAVE RESPONSE =================
@app.route("/add_response/<int:id>", methods=["POST"])
def add_response(id):
    
    if 'name' not in session:
        return redirect(url_for('login'))
    
    answer = request.form.get("answer")
    file = request.files.get("file")
    
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads')
        
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
 
    filename = None
    
    if file and file.filename != "":
        filename = str(int(time.time())) + "_" + secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO responses ( doubt_id, teacher_name, answer, file) VALUES (?, ?, ?, ?)
    """, (id, session['name'],answer, filename))

    conn.commit()
    conn.close()
    
    flash("Response submitted successfully!" )

    return redirect(url_for("teacher_dashboard"))

@app.route('/admin_dashboard')
def admin_dashboard():

    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get users
    cursor.execute("SELECT id, name, email, role, branch, created_at FROM users")
    users = cursor.fetchall()
    
    # Separate users
    students = [u for u in users if u[3] == 'student']
    teachers = [u for u in users if u[3] == 'teacher']
    
    # 🔥 DOUBTS (NEW)
    cursor.execute("""
    SELECT 
        d.id,
        d.student_name,
        d.branch,
        d.subject,
        d.question,
        d.file,
        r.answer,
        r.file,
        r.teacher_name,
        d.date
    FROM doubts d
    LEFT JOIN responses r ON d.id = r.doubt_id
    ORDER BY d.id DESC
    """)
    doubts = cursor.fetchall()

    # Analytics
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    student_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='teacher'")
    teacher_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    admin_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM doubts")
    total_doubts = cursor.fetchone()[0]

    conn.close()

    return render_template("admin_dashboard.html",
                           users=users,
                           students=students,
                           teachers=teachers,
                           doubts=doubts,
                           student_count=student_count,
                           teacher_count=teacher_count,
                           admin_count=admin_count,
                           total_doubts=total_doubts)

@app.route('/delete_user/<int:id>', methods=['POST'])
def delete_user(id):

    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Prevent deleting admin
    cursor.execute("SELECT role FROM users WHERE id=?", (id,))
    user = cursor.fetchone()

    if user and user[0] == 'admin':
        flash("You cannot delete an admin!", "error")
        return redirect(url_for('admin_dashboard'))

    cursor.execute("DELETE FROM users WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("User deleted successfully","success")
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_doubt/<int:id>', methods=['POST'])
def delete_doubt(id):

    if 'name' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM doubts WHERE id=? AND student_name=?", 
                   (id, session['name']))

    conn.commit()
    conn.close()

    flash("Doubt deleted successfully!", "success")

    return redirect(url_for('student_dashboard'))

@app.route("/delete_response/<int:id>", methods=["POST"])
def delete_response(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM responses
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    flash("Response deleted successfully!")
    return redirect(url_for("teacher_dashboard"))


# 🔹 Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    app.run(debug=True)