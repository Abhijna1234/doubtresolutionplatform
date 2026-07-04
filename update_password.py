from werkzeug.security import generate_password_hash
import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("SELECT email, password FROM users")
users = cursor.fetchall()

cursor.execute("SELECT email, password FROM users")
for email, pw in cursor.fetchall():
    if not pw.startswith("scrypt"):
        cursor.execute("UPDATE users SET password=? WHERE email=?",
                       (generate_password_hash(pw), email))

conn.commit()
conn.close()

print("All passwords fixed!")