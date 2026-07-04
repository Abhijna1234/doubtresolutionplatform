from werkzeug.security import generate_password_hash
import sqlite3
from datetime import datetime

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

email = "admin@gmail.com"
password = "Admin@123"

hashed = generate_password_hash(password)
created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

cursor.execute("SELECT * FROM users WHERE email=?", (email,))
admin = cursor.fetchone()

if admin:
    print("Admin already exists!")
else:
    cursor.execute("""
        INSERT INTO users (role, name, email, branch, password, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("admin", "Admin", email, "Admin", hashed, created_at))

    conn.commit()
    print("✅ Admin created successfully!")    

conn.close()