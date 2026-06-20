# reset_and_update_movies.py - Полное обновление базы данных фильмов из TMDB

from database import Database
from tmdb_service import tmdb_service
import logging
import time
from tqdm import tqdm
import sqlite3

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_all_movies():
    """Удаляет все фильмы из базы данных"""
    db = Database()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, сколько фильмов было
            cursor.execute("SELECT COUNT(*) FROM movies")
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Удаляем все фильмы
                cursor.execute("DELETE FROM movies")
                # Сбрасываем автоинкремент (опционально)
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='movies'")
                logger.info(f"🗑️ Удалено {count} фильмов из базы данных")
            else:
                logger.info("ℹ️ База данных уже пуста")
            
            return count
    except Exception as e:
        logger.error(f"❌ Ошибка при очистке базы: {e}")
        return 0

def get_diverse_movies(limit: int = 250) -> list:
    """
    Получает разнообразные фильмы из разных источников
    
    Args:
        limit: общее количество фильмов (по умолчанию 250)
    
    Returns:
        Список фильмов
    """
    logger.info(f"🔄 Загрузка {limit} фильмов из разных источников...")
    
    all_movies = []
    
    # Загружаем из разных источников для разнообразия
    sources = [
        ('popular', 1, 40),    # 40 популярных
        ('popular', 2, 40),    # еще 40 популярных
        ('popular', 3, 40),    # еще 40 популярных
        ('top_rated', 1, 30),  # 30 топ-рейтинговых
        ('top_rated', 2, 30),  # еще 30 топ-рейтинговых
        ('upcoming', 1, 20),   # 20 предстоящих
        ('now_playing', 1, 25), # 25 сейчас в прокате
        ('now_playing', 2, 25), # еще 25 сейчас в прокате
    ]
    
    for source, page, count in sources:
        try:
            logger.info(f"   📥 Загрузка {source} (страница {page})...")
            
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
                # Берем только нужное количество
                movies_to_add = movies[:count]
                all_movies.extend(movies_to_add)
                logger.info(f"      ✅ Получено {len(movies_to_add)} фильмов")
            else:
                logger.warning(f"      ⚠️ Не удалось получить фильмы из {source}")
            
            time.sleep(0.3)
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка при загрузке из {source}: {e}")
    
    # Удаляем дубликаты по tmdb_id
    seen_ids = set()
    unique_movies = []
    for movie in all_movies:
        if movie['tmdb_id'] not in seen_ids and movie['tmdb_id'] is not None:
            seen_ids.add(movie['tmdb_id'])
            unique_movies.append(movie)
    
    logger.info(f"📊 Найдено {len(unique_movies)} уникальных фильмов")
    return unique_movies[:limit]

def update_movies_with_details(movies: list) -> tuple:
    """
    Обновляет фильмы, добавляя детальную информацию
    
    Args:
        movies: список фильмов
    
    Returns:
        (added, errors) - количество добавленных и ошибок
    """
    db = Database()
    added = 0
    errors = 0
    
    logger.info("📥 Загрузка детальной информации о фильмах...")
    
    for movie_data in tqdm(movies, desc="Загрузка фильмов"):
        try:
            # Пропускаем фильмы без ID
            if not movie_data.get('tmdb_id'):
                errors += 1
                continue
            
            # Получаем детальную информацию
            details = tmdb_service.get_movie_details(movie_data['tmdb_id'])
            
            if details and details.get('title') and details.get('title') != 'Без названия':
                # Проверяем обязательные поля
                if not details.get('genres'):
                    logger.warning(f"   ⚠️ Нет жанров у фильма: {details['title']}")
                
                # Добавляем в БД
                db.add_movie(details)
                added += 1
                
                # Логируем каждые 10 фильмов
                if added % 10 == 0:
                    logger.info(f"   ✅ Добавлено {added} фильмов...")
            else:
                errors += 1
                logger.warning(f"   ⚠️ Не удалось получить детали для фильма ID: {movie_data.get('tmdb_id')}")
            
            # Небольшая задержка, чтобы не превысить лимиты API
            time.sleep(0.2)
            
        except Exception as e:
            errors += 1
            logger.error(f"   ❌ Ошибка при добавлении фильма: {e}")
    
    return added, errors

def reset_and_update(limit: int = 250):
    """
    Основная функция: очищает БД и добавляет новые фильмы
    
    Args:
        limit: количество фильмов для добавления (по умолчанию 250)
    """
    print("\n" + "="*60)
    print("🎬 ОБНОВЛЕНИЕ БАЗЫ ДАННЫХ ФИЛЬМОВ")
    print("="*60 + "\n")
    
    # 1. Очищаем базу данных
    logger.info("ШАГ 1: Очистка базы данных...")
    deleted_count = clear_all_movies()
    print(f"   🗑️ Удалено: {deleted_count} фильмов\n")
    
    # 2. Получаем фильмы из TMDB
    logger.info("ШАГ 2: Загрузка фильмов из TMDB...")
    movies = get_diverse_movies(limit)
    
    if not movies:
        logger.error("❌ Не удалось загрузить фильмы из TMDB")
        logger.info("💡 Проверьте:")
        logger.info("   1. Правильно ли указан TMDB_API_KEY в .env файле")
        logger.info("   2. Есть ли интернет-соединение")
        logger.info("   3. Не заблокирован ли доступ к TMDB API")
        return
    
    print(f"   📊 Загружено: {len(movies)} фильмов\n")
    
    # 3. Добавляем фильмы с деталями
    logger.info("ШАГ 3: Добавление фильмов в базу данных...")
    added, errors = update_movies_with_details(movies)
    
    # 4. Выводим статистику
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА ОБНОВЛЕНИЯ:")
    print(f"   ✅ Успешно добавлено: {added}")
    print(f"   ❌ Ошибок: {errors}")
    print("="*60 + "\n")
    
    # 5. Проверяем финальный результат
    db = Database()
    final_movies = db.get_all_movies()
    
    if final_movies:
        # Статистика по жанрам
        genres = {}
        for movie in final_movies:
            for genre in movie.get('genres', []):
                genres[genre] = genres.get(genre, 0) + 1
        
        print("📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"   📽️ Всего фильмов: {len(final_movies)}")
        print(f"   🏷️ Жанров: {len(genres)}")
        print(f"   🎭 Топ-10 жанров:")
        for genre, count in sorted(genres.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"      - {genre}: {count} фильмов")
        
        print("\n🎬 ПРИМЕРЫ ДОБАВЛЕННЫХ ФИЛЬМОВ:")
        for i, movie in enumerate(final_movies[:10], 1):
            genres_str = ', '.join(movie['genres'][:2]) if movie['genres'] else 'Нет жанров'
            print(f"   {i}. {movie['title']} ({movie['year']}) - {genres_str}")
    else:
        print("❌ В базе данных нет фильмов!")
        print("💡 Попробуйте запустить скрипт еще раз или проверьте подключение к TMDB")

if __name__ == '__main__':
    try:
        # Меняем количество фильмов на 250
        reset_and_update(limit=250)
    except KeyboardInterrupt:
        print("\n\n⚠️ Процесс прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()