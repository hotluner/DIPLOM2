# test_tmdb.py - Проверка подключения к TMDB

import tmdbsimple as tmdb
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем API ключ
API_KEY = os.getenv('TMDB_API_KEY')
print(f"API Key: {API_KEY[:10]}..." if API_KEY else "API Key не найден!")

if not API_KEY:
    print("❌ Ошибка: TMDB_API_KEY не найден в .env файле")
    exit(1)

# Инициализируем
tmdb.API_KEY = API_KEY

try:
    # Тестируем поиск
    search = tmdb.Search()
    response = search.movie(query='Inception', language='ru-RU')
    
    # response - это словарь, а не объект
    print(f"Тип ответа: {type(response)}")
    
    # Проверяем, что в ответе есть результаты
    if 'results' in response:
        results = response['results']
        print(f"Найдено фильмов: {len(results)}")
        
        if results:
            movie = results[0]
            print(f"Первый фильм: {movie['title']} ({movie['release_date'][:4] if movie['release_date'] else 'N/A'})")
            print("✅ API работает нормально")
        else:
            print("⚠️ Поиск не вернул результатов")
    else:
        print(f"⚠️ Ответ не содержит 'results': {response.keys()}")
        
except Exception as e:
    print(f"❌ Ошибка при запросе к TMDB: {e}")
    import traceback
    traceback.print_exc()