import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    """Модель пользователя"""
    
    def __init__(self, user_id: Optional[int] = None, session_id: str = None):
        self.user_id = user_id
        self.session_id = session_id
        self.username = None  # Добавляем имя пользователя
        self.password_hash = None  # Добавляем хеш пароля
        self.email = None  # Добавляем email (опционально)
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.preferences = {}
        self.ratings = {}
        self.recommendations = {}
        self.skipped = {}  # Добавляем поле для пропущенных фильмов
        self.last_recommended_at = None
        self.is_admin = False  # Флаг администратора
    
    def set_password(self, password: str):
        """Устанавливает пароль (хеширует)"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Проверяет пароль"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self) -> Dict:
        """Преобразует объект в словарь для БД"""
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'username': self.username,
            'password_hash': self.password_hash,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'preferences': json.dumps(self.preferences),
            'ratings': json.dumps(self.ratings),
            'recommendations': json.dumps(self.recommendations),
            'skipped': json.dumps(self.skipped),
            'last_recommended_at': self.last_recommended_at.isoformat() if self.last_recommended_at else None,
            'is_admin': 1 if self.is_admin else 0
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Создаёт объект из данных БД"""
        user = cls(
            user_id=data.get('user_id'),
            session_id=data.get('session_id')
        )
        user.username = data.get('username')
        user.password_hash = data.get('password_hash')
        user.email = data.get('email')
        user.created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        user.updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now()
        user.preferences = json.loads(data.get('preferences', '{}'))
        user.ratings = json.loads(data.get('ratings', '{}'))
        user.recommendations = json.loads(data.get('recommendations', '{}'))
        user.skipped = json.loads(data.get('skipped', '{}'))
        user.last_recommended_at = datetime.fromisoformat(data['last_recommended_at']) if data.get('last_recommended_at') else None
        user.is_admin = bool(data.get('is_admin', 0))
        return user
    
    def get_rating_count(self) -> int:
        """Количество оценённых фильмов"""
        return len(self.ratings)
    
    def has_min_ratings(self, min_count: int = 10) -> bool:
        """Проверяет, набрал ли пользователь минимум оценок"""
        return self.get_rating_count() >= min_count
    
    def to_json(self) -> Dict:
        """Для безопасного вывода в JSON (без пароля)"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'rating_count': self.get_rating_count(),
            'is_admin': self.is_admin
        }