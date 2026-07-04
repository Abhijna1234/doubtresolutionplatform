import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE doubts ADD COLUMN teacher_file TEXT")
    print("Column added successfully!")
except:
    print("Column already exists!")

conn.commit()
conn.close()