import sqlite3
import json
from typing import Optional, Dict, List
from datetime import datetime
from contextlib import contextmanager
from models import User
import secrets

class Database:
    """Класс для работы с SQLite"""
    
    def __init__(self, db_path: str = 'instance/movies.db'):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для подключения к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_db(self):
        """Создаёт таблицы, если их нет"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
        
            # Таблица пользователей - создаём с нуля с правильной структурой
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    email TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    preferences TEXT DEFAULT '{}',
                    ratings TEXT DEFAULT '{}',
                    recommendations TEXT DEFAULT '{}',
                    skipped TEXT DEFAULT '{}',
                    last_recommended_at TEXT,
                    is_admin INTEGER DEFAULT 0
                )
            ''')

            
            # Проверяем и добавляем недостающие поля (для существующих БД)
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]

            # Добавляем поля, если их нет (без UNIQUE, чтобы избежать ошибок)
            fields_to_add = {
                'username': 'TEXT',
                'password_hash': 'TEXT',
                'email': 'TEXT',
                'skipped': 'TEXT DEFAULT "{}"',
                'is_admin': 'INTEGER DEFAULT 0'
            }

            for field, field_type in fields_to_add.items():
                if field not in columns:
                    try:
                        cursor.execute(f'ALTER TABLE users ADD COLUMN {field} {field_type}')
                        print(f"✅ Добавлено поле {field}")
                    except sqlite3.OperationalError as e:
                        print(f"⚠️ Не удалось добавить поле {field}: {e}")

            # Таблица фильмов (для демонстрации)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS movies (
                    movie_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    year INTEGER,
                    genres TEXT NOT NULL,
                    actors TEXT,
                    directors TEXT,
                    description TEXT,
                    poster_url TEXT,
                    imdb_rating REAL,
                    created_at TEXT
                )
            ''')
            
            # Индексы для производительности
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_session ON users(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_movie_genres ON movies(genres)')
            
            # Создаём администратора по умолчанию (если нет пользователей)
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
            
            print("✅ База данных инициализирована")

    
    # ---------- Работа с пользователями ----------
    
    def create_user(self, username: str, password: str, email: str = None) -> Optional[User]:
        """Создаёт нового пользователя с паролем"""
        # Проверяем, существует ли пользователь
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return None  # Пользователь уже существует
    
        session_id = secrets.token_urlsafe(32)
        now = datetime.now().isoformat()
    
        user = User(session_id=session_id)
        user.username = username
        user.email = email
        user.set_password(password)
        user.created_at = datetime.now()
        user.updated_at = datetime.now()
    
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (session_id, username, password_hash, email, created_at, updated_at, preferences, ratings, recommendations, skipped, is_admin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                username,
                user.password_hash,
                email,
                now,
                now,
                '{}',
                '{}',
                '{}',
                '{}',
                0
            ))
            user.user_id = cursor.lastrowid
    
        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Получает пользователя по имени"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            
        if row:
            return User.from_dict(dict(row))
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получает пользователя по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
        if row:
            return User.from_dict(dict(row))
        return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Аутентифицирует пользователя"""
        user = self.get_user_by_username(username)
        if user and user.check_password(password):
            return user
        return None
    
    def get_user_by_session(self, session_id: str) -> Optional[User]:
        """Получает пользователя по session_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            
        if row:
            return User.from_dict(dict(row))
        return None
    
    def update_user(self, user: User):
        """Обновляет данные пользователя"""
        user.updated_at = datetime.now()
        data = user.to_dict()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET preferences = ?, ratings = ?, recommendations = ?, 
                    updated_at = ?, last_recommended_at = ?
                WHERE user_id = ?
            ''', (
                data['preferences'],
                data['ratings'],
                data['recommendations'],
                data['updated_at'],
                data['last_recommended_at'],
                user.user_id
            ))
    
    def delete_user(self, user_id: int):
        """Удаляет пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    
    def get_all_users(self) -> List[User]:
        """Получает всех пользователей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
        return [User.from_dict(dict(row)) for row in rows]
    
    # ---------- Работа с фильмами ----------
    
    def add_movie(self, movie_data: Dict):
        """Добавляет фильм в БД"""
        now = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO movies 
                (movie_id, title, year, genres, actors, directors, description, poster_url, imdb_rating, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                movie_data.get('movie_id'),
                movie_data.get('title'),
                movie_data.get('year'),
                json.dumps(movie_data.get('genres', [])),
                json.dumps(movie_data.get('actors', [])),
                json.dumps(movie_data.get('directors', [])),
                movie_data.get('description', ''),
                movie_data.get('poster_url', ''),
                movie_data.get('imdb_rating', 0.0),
                now
            ))
    
    def get_movie(self, movie_id: str) -> Optional[Dict]:
        """Получает фильм по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM movies WHERE movie_id = ?', (movie_id,))
            row = cursor.fetchone()
            
        if row:
            data = dict(row)
            data['genres'] = json.loads(data['genres'])
            data['actors'] = json.loads(data['actors'])
            data['directors'] = json.loads(data['directors'])
            return data
        return None
    
    def get_all_movies(self) -> List[Dict]:
        """Получает все фильмы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM movies ORDER BY title')
            rows = cursor.fetchall()
            
        movies = []
        for row in rows:
            data = dict(row)
            data['genres'] = json.loads(data['genres'])
            data['actors'] = json.loads(data['actors'])
            data['directors'] = json.loads(data['directors'])
            movies.append(data)
        return movies