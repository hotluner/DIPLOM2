# init_tmdb_movies.py - Инициализация БД из TMDB

from database import Database
from tmdb_service import tmdb_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_movies_from_tmdb(limit: int = 50):
    """Загружает популярные фильмы из TMDB в БД"""
    db = Database()
    
    # Проверяем, сколько фильмов уже есть
    existing = db.get_all_movies()
    logger.info(f"В базе уже {len(existing)} фильмов")
    
    if len(existing) >= limit:
        logger.info("База уже заполнена")
        return
    
    # Получаем популярные фильмы
    logger.info("Загрузка популярных фильмов из TMDB...")
    popular = tmdb_service.get_popular_movies(page=1)
    
    if not popular:
        logger.error("Не удалось загрузить фильмы из TMDB")
        return
    
    added = 0
    skipped = 0
    
    for movie_data in popular[:limit]:
        # Получаем детальную информацию
        details = tmdb_service.get_movie_details(movie_data['tmdb_id'])
        
        if details and details.get('title'):
            # Проверяем, есть ли уже в БД
            existing_movie = db.get_movie(details['movie_id'])
            if not existing_movie:
                db.add_movie(details)
                added += 1
                logger.info(f"✅ Добавлен: {details['title']} ({details['year']})")
            else:
                skipped += 1
                logger.info(f"⏭️ Пропущен (уже есть): {details['title']}")
        else:
            skipped += 1
            logger.warning(f"⚠️ Не удалось получить детали для фильма ID: {movie_data.get('tmdb_id')}")
    
    logger.info(f"📊 Итог: добавлено {added}, пропущено {skipped}")
    
    # Выводим статистику
    movies = db.get_all_movies()
    genres = set()
    for movie in movies:
        genres.update(movie.get('genres', []))
    
    print(f"\n📊 Статистика:")
    print(f"  - Всего фильмов: {len(movies)}")
    print(f"  - Жанров: {len(genres)}")
    if genres:
        print(f"  - Жанры: {', '.join(sorted(genres))}")

if __name__ == '__main__':
    init_movies_from_tmdb(50)