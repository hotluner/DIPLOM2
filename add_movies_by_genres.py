# add_movies_by_genres.py - Добавление фильмов по жанрам

from database import Database
from tmdb_service import tmdb_service
import logging
import time
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_movies_by_genres():
    """Добавляет фильмы разных жанров для разнообразия"""
    db = Database()
    
    # Получаем список жанров
    genres = tmdb_service.get_genres()
    
    # Выбираем популярные жанры
    popular_genres = [
        'Боевик', 'Драма', 'Комедия', 'Фантастика', 
        'Приключения', 'Криминал', 'Триллер', 'Ужасы'
    ]
    
    genre_ids = []
    for genre_name in popular_genres:
        for genre in genres:
            if genre['name'] == genre_name:
                genre_ids.append(genre['id'])
                break
    
    logger.info(f"Найдено {len(genre_ids)} жанров")
    
    all_movies = []
    
    # Для каждого жанра загружаем фильмы
    for genre_id in genre_ids:
        logger.info(f"Загрузка фильмов для жанра {genre_id}...")
        movies = tmdb_service.get_movies_by_genres([genre_id], page=1)
        
        # Берем по 5 фильмов из каждого жанра
        for movie in movies[:5]:
            if movie not in all_movies:
                all_movies.append(movie)
        
        time.sleep(0.5)
    
    # Удаляем дубликаты
    seen_ids = set()
    unique_movies = []
    for movie in all_movies:
        if movie['tmdb_id'] not in seen_ids:
            seen_ids.add(movie['tmdb_id'])
            unique_movies.append(movie)
    
    logger.info(f"Найдено {len(unique_movies)} уникальных фильмов")
    
    # Добавляем в БД
    added = 0
    for movie_data in tqdm(unique_movies, desc="Добавление фильмов"):
        try:
            details = tmdb_service.get_movie_details(movie_data['tmdb_id'])
            if details and details.get('title'):
                existing = db.get_movie(details['movie_id'])
                if not existing:
                    db.add_movie(details)
                    added += 1
                    logger.info(f"✅ Добавлен: {details['title']}")
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
    
    logger.info(f"✅ Добавлено {added} новых фильмов")

if __name__ == '__main__':
    add_movies_by_genres()