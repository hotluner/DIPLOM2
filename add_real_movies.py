# add_real_movies.py - Добавление 250 реальных фильмов из TMDB

from database import Database
from tmdb_service import tmdb_service
import logging
import time
from tqdm import tqdm

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_real_movies(count: int = 250):
    """
    Добавляет реальные фильмы из TMDB в базу данных
    
    Args:
        count: количество фильмов для добавления
    """
    db = Database()
    
    # Проверяем, сколько фильмов уже есть
    existing = db.get_all_movies()
    logger.info(f"📊 В базе уже {len(existing)} фильмов")
    
    if len(existing) >= count:
        logger.info(f"✅ В базе уже достаточно фильмов ({len(existing)})")
        return
    
    # Получаем популярные фильмы из разных источников
    logger.info(f"🔄 Загрузка {count} фильмов из TMDB...")
    
    all_movies = []
    
    # Загружаем из разных источников
    sources = [
        ('popular', 1, 50),
        ('popular', 2, 50),
        ('popular', 3, 50),
        ('popular', 4, 50),
        ('popular', 5, 50),
        ('top_rated', 1, 25),
        ('top_rated', 2, 25),
        ('upcoming', 1, 25),
        ('now_playing', 1, 25),
        ('now_playing', 2, 25),
    ]
    
    for source, page, limit in sources:
        logger.info(f"   📥 Загрузка {source} страница {page}...")
        
        if source == 'popular':
            movies = tmdb_service.get_popular_movies(page=page)
        elif source == 'top_rated':
            movies = tmdb_service.get_top_rated_movies(page=page)
        elif source == 'upcoming':
            movies = tmdb_service.get_upcoming_movies(page=page)
        elif source == 'now_playing':
            movies = tmdb_service.get_now_playing_movies(page=page)
        else:
            continue
        
        if movies:
            all_movies.extend(movies[:limit])
            logger.info(f"      ✅ Получено {len(movies[:limit])} фильмов")
        else:
            logger.warning(f"      ⚠️ Не удалось получить фильмы из {source}")
        
        time.sleep(0.5)
    
    # Удаляем дубликаты по tmdb_id
    seen_ids = set()
    unique_movies = []
    for movie in all_movies:
        if movie['tmdb_id'] not in seen_ids:
            seen_ids.add(movie['tmdb_id'])
            unique_movies.append(movie)
    
    logger.info(f"📊 Найдено {len(unique_movies)} уникальных фильмов")
    
    # Добавляем фильмы в БД
    added = 0
    skipped = 0
    errors = 0
    
    # Ограничиваем количество
    movies_to_add = unique_movies[:count]
    
    logger.info(f"📥 Загрузка детальной информации о {len(movies_to_add)} фильмах...")
    
    for movie_data in tqdm(movies_to_add, desc="Загрузка фильмов"):
        try:
            # Получаем детальную информацию
            details = tmdb_service.get_movie_details(movie_data['tmdb_id'])
            
            if details and details.get('title') and details.get('title') != 'Без названия':
                # Проверяем, есть ли уже в БД
                existing_movie = db.get_movie(details['movie_id'])
                if not existing_movie:
                    db.add_movie(details)
                    added += 1
                    
                    # Логируем каждые 10 фильмов
                    if added % 10 == 0:
                        logger.info(f"   ✅ Добавлено {added} фильмов...")
                else:
                    skipped += 1
            else:
                errors += 1
                logger.warning(f"   ⚠️ Не удалось получить детали для фильма ID: {movie_data.get('tmdb_id')}")
            
            time.sleep(0.2)
            
        except Exception as e:
            errors += 1
            logger.error(f"   ❌ Ошибка при добавлении фильма: {e}")
    
    # Выводим статистику
    logger.info("\n" + "="*50)
    logger.info("📊 СТАТИСТИКА:")
    logger.info(f"   ✅ Добавлено: {added}")
    logger.info(f"   ⏭️ Пропущено (уже есть): {skipped}")
    logger.info(f"   ❌ Ошибок: {errors}")
    logger.info("="*50)
    
    # Финальная статистика
    final_movies = db.get_all_movies()
    genres = set()
    for movie in final_movies:
        genres.update(movie.get('genres', []))
    
    print("\n📊 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"   📽️ Всего фильмов в базе: {len(final_movies)}")
    print(f"   🏷️ Уникальных жанров: {len(genres)}")
    print(f"   🎭 Жанры: {', '.join(sorted(genres))}")
    
    if len(final_movies) < 250:
        print(f"\n⚠️ В базе только {len(final_movies)} фильмов. Попробуйте запустить скрипт еще раз.")

if __name__ == '__main__':
    print("🎬 ЗАГРУЗКА РЕАЛЬНЫХ ФИЛЬМОВ ИЗ TMDB")
    print("="*50)
    add_real_movies(250)