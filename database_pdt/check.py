# check.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "System.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("--- CẤU TRÚC BẢNG TRONG CƠ SỞ DỮ LIỆU ---")
schemas = cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall()
for name, sql in schemas:
    print(f"Bảng: {name}")
    print(f"Cấu trúc SQL khởi tạo:\n{sql}\n{'-'*40}")
conn.close()