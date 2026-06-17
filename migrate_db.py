# migrate_db.py - Скрипт для обновления базы данных

from database import Database
from datetime import datetime
import sqlite3

def migrate():
    """Добавляет новые поля в существующую БД"""
    db = Database()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем существующие поля
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Добавляем недостающие поля (без UNIQUE)
        if 'username' not in columns:
            print("Добавляем поле username...")
            try:
                cursor.execute('ALTER TABLE users ADD COLUMN username TEXT')
                print("✅ Поле username добавлено")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Ошибка: {e}")
        
        if 'password_hash' not in columns:
            print("Добавляем поле password_hash...")
            try:
                cursor.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
                print("✅ Поле password_hash добавлено")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Ошибка: {e}")
        
        if 'email' not in columns:
            print("Добавляем поле email...")
            try:
                cursor.execute('ALTER TABLE users ADD COLUMN email TEXT')
                print("✅ Поле email добавлено")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Ошибка: {e}")
        
        if 'is_admin' not in columns:
            print("Добавляем поле is_admin...")
            try:
                cursor.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
                print("✅ Поле is_admin добавлено")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Ошибка: {e}")
        
        if 'skipped' not in columns:
            print("Добавляем поле skipped...")
            try:
                cursor.execute('ALTER TABLE users ADD COLUMN skipped TEXT DEFAULT "{}"')
                print("✅ Поле skipped добавлено")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Ошибка: {e}")
        
        # Создаём администратора, если нет пользователей
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        
        if count == 0:
            from werkzeug.security import generate_password_hash
            admin_password = generate_password_hash('admin123')
            cursor.execute('''
                INSERT INTO users (session_id, username, password_hash, created_at, updated_at, is_admin)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                'admin_session_' + datetime.now().strftime('%Y%m%d%H%M%S'),
                'admin',
                admin_password,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                1
            ))
            print("✅ Создан администратор по умолчанию (логин: admin, пароль: admin123)")
        else:
            print(f"⚠️ В базе уже есть {count} пользователей")
            
            # Проверяем, есть ли админ
            cursor.execute("SELECT user_id FROM users WHERE is_admin = 1 LIMIT 1")
            admin_exists = cursor.fetchone()
            
            if not admin_exists:
                print("⚠️ Администратор не найден. Создаём...")
                from werkzeug.security import generate_password_hash
                admin_password = generate_password_hash('admin123')
                cursor.execute('''
                    INSERT INTO users (session_id, username, password_hash, created_at, updated_at, is_admin)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    'admin_session_' + datetime.now().strftime('%Y%m%d%H%M%S'),
                    'admin',
                    admin_password,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    1
                ))
                print("✅ Создан администратор по умолчанию (логин: admin, пароль: admin123)")
        
        print("✅ Миграция завершена")

if __name__ == '__main__':
    migrate()