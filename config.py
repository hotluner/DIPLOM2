# config.py - Конфигурация приложения

import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

class Config:
    """Основная конфигурация"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    TMDB_API_KEY = os.getenv('TMDB_API_KEY')
    TMDB_LANGUAGE = os.getenv('TMDB_LANGUAGE', 'ru-RU')
    TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/'
    TMDB_POSTER_SIZE = 'w500'
    TMDB_BACKDROP_SIZE = 'w1280'
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = './flask_session'
    SESSION_PERMANENT = False

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    SESSION_TYPE = 'redis'  # Для продакшена лучше использовать Redis

# Выбираем конфигурацию
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}