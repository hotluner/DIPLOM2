# init_movies.py - Скрипт для заполнения базы данных фильмами

from database import Database
from movies_data import SAMPLE_MOVIES

def init_movies():
    """Заполняет базу данных фильмами"""
    db = Database()
    
    # Проверяем, сколько фильмов уже есть
    existing = db.get_all_movies()
    print(f"В базе данных уже {len(existing)} фильмов")
    
    if len(existing) < len(SAMPLE_MOVIES):
        print("Добавляем новые фильмы...")
        for movie in SAMPLE_MOVIES:
            db.add_movie(movie)
        print(f"✅ Добавлено {len(SAMPLE_MOVIES)} фильмов")
    else:
        print("✅ База данных уже заполнена фильмами")
    
    # Выводим статистику
    movies = db.get_all_movies()
    genres = set()
    for movie in movies:
        genres.update(movie.get('genres', []))
    
    print(f"\n📊 Статистика:")
    print(f"  - Всего фильмов: {len(movies)}")
    print(f"  - Жанров: {len(genres)}")
    print(f"  - Жанры: {', '.join(sorted(genres))}")

if __name__ == '__main__':
    init_movies()