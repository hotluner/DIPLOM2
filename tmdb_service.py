# tmdb_service.py - Сервис для работы с TMDB API

import tmdbsimple as tmdb
from config import Config
import logging
from typing import List, Dict, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TMDBCache:
    """Простой кеш для TMDB запросов"""
    def __init__(self):
        self.cache = {}
    
    def get(self, key):
        return self.cache.get(key)
    
    def set(self, key, value):
        self.cache[key] = value
        return value

class TMDBService:
    """Сервис для работы с TMDB API"""
    
    def __init__(self):
        # Инициализация с API-ключом
        self.api_key = Config.TMDB_API_KEY
        if not self.api_key:
            raise ValueError("TMDB_API_KEY не найден в .env файле!")
        
        tmdb.API_KEY = self.api_key
        self.language = Config.TMDB_LANGUAGE
        self.cache = TMDBCache()
        logger.info(f"TMDB Service инициализирован")
    
    def search_movies(self, query: str, year: Optional[int] = None) -> List[Dict]:
        """
        Поиск фильмов по названию
        
        Args:
            query: поисковый запрос
            year: год фильма (опционально)
        
        Returns:
            Список найденных фильмов
        """
        try:
            search = tmdb.Search()
            response = search.movie(query=query, year=year, language=self.language)
            
            movies = []
            # response - это словарь
            if 'results' in response:
                for movie_data in response['results']:
                    movies.append(self._format_movie_data(movie_data))
            
            logger.info(f"Найдено {len(movies)} фильмов по запросу '{query}'")
            return movies
        except Exception as e:
            logger.error(f"Ошибка при поиске фильмов: {e}")
            return []
    
    def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        """
        Получение детальной информации о фильме
        
        Args:
            movie_id: ID фильма в TMDB
        
        Returns:
            Словарь с данными о фильме
        """
        cache_key = f"movie_{movie_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            movie = tmdb.Movies(movie_id)
            response = movie.info(language=self.language)
            
            # response - это словарь
            if not response:
                logger.warning(f"Пустой ответ для фильма {movie_id}")
                return None
            
            # Получаем credits отдельно
            credits_response = movie.credits(language=self.language)
            
            # Извлекаем актёров и режиссёров
            actors = []
            directors = []
            
            if credits_response and 'cast' in credits_response:
                # Берем первых 5 актёров
                for actor in credits_response['cast'][:5]:
                    if 'name' in actor:
                        actors.append(actor['name'])
            
            if credits_response and 'crew' in credits_response:
                for crew_member in credits_response['crew']:
                    if crew_member.get('job') == 'Director':
                        if 'name' in crew_member:
                            directors.append(crew_member['name'])
            
            # Формируем данные фильма
            movie_data = {
                'movie_id': f"tt{response.get('id', '')}",
                'tmdb_id': response.get('id'),
                'title': response.get('title', 'Без названия'),
                'original_title': response.get('original_title', ''),
                'year': response.get('release_date', '')[:4] if response.get('release_date') else None,
                'genres': [],
                'actors': actors,
                'directors': directors,
                'description': response.get('overview', ''),
                'poster_url': self._get_poster_url(response.get('poster_path')),
                'backdrop_url': self._get_backdrop_url(response.get('backdrop_path')),
                'imdb_rating': response.get('vote_average', 0),
                'vote_count': response.get('vote_count', 0),
                'popularity': response.get('popularity', 0),
                'runtime': response.get('runtime', None)
            }
            
            # Добавляем жанры
            if 'genres' in response:
                for genre in response['genres']:
                    if 'name' in genre:
                        movie_data['genres'].append(genre['name'])
            
            self.cache.set(cache_key, movie_data)
            logger.info(f"Получена информация о фильме: {movie_data['title']}")
            return movie_data
            
        except Exception as e:
            logger.error(f"Ошибка при получении деталей фильма {movie_id}: {e}")
            return None
    
    def get_popular_movies(self, page: int = 1) -> List[Dict]:
        """
        Получение популярных фильмов
        
        Args:
            page: номер страницы
        
        Returns:
            Список популярных фильмов
        """
        cache_key = f"popular_{page}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            movie = tmdb.Movies()
            response = movie.popular(page=page, language=self.language)
            
            movies = []
            # response - это словарь
            if 'results' in response:
                for movie_data in response['results']:
                    movies.append(self._format_movie_data(movie_data))
            else:
                logger.warning(f"Ответ не содержит 'results': {response.keys() if isinstance(response, dict) else type(response)}")
            
            self.cache.set(cache_key, movies)
            logger.info(f"Получено {len(movies)} популярных фильмов")
            return movies
            
        except Exception as e:
            logger.error(f"Ошибка при получении популярных фильмов: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_top_rated_movies(self, page: int = 1) -> List[Dict]:
        """
        Получение топ-рейтинговых фильмов
        
        Args:
            page: номер страницы
        
        Returns:
            Список топ-фильмов
        """
        cache_key = f"top_rated_{page}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            movie = tmdb.Movies()
            response = movie.top_rated(page=page, language=self.language)
            
            movies = []
            if 'results' in response:
                for movie_data in response['results']:
                    movies.append(self._format_movie_data(movie_data))
            
            self.cache.set(cache_key, movies)
            logger.info(f"Получено {len(movies)} топ-фильмов")
            return movies
        except Exception as e:
            logger.error(f"Ошибка при получении топ-фильмов: {e}")
            return []
    
    def get_movies_by_genre(self, genre_id: int, page: int = 1) -> List[Dict]:
        """
        Получение фильмов по жанру
        
        Args:
            genre_id: ID жанра в TMDB
            page: номер страницы
        
        Returns:
            Список фильмов жанра
        """
        try:
            discover = tmdb.Discover()
            response = discover.movie(
                with_genres=genre_id,
                page=page,
                language=self.language,
                sort_by='popularity.desc'
            )
            
            movies = []
            if 'results' in response:
                for movie_data in response['results']:
                    movies.append(self._format_movie_data(movie_data))
            
            logger.info(f"Получено {len(movies)} фильмов для жанра {genre_id}")
            return movies
        except Exception as e:
            logger.error(f"Ошибка при получении фильмов по жанру: {e}")
            return []
    
    def _format_movie_data(self, movie_data) -> Dict:
        """Форматирует данные фильма для единообразного использования"""
        # Проверяем, что movie_data - это словарь
        if isinstance(movie_data, dict):
            return {
                'movie_id': f"tt{movie_data.get('id', '')}",
                'tmdb_id': movie_data.get('id'),
                'title': movie_data.get('title', 'Без названия'),
                'original_title': movie_data.get('original_title', ''),
                'year': movie_data.get('release_date', '')[:4] if movie_data.get('release_date') else None,
                'genres': [],
                'actors': [],
                'directors': [],
                'description': movie_data.get('overview', ''),
                'poster_url': self._get_poster_url(movie_data.get('poster_path')),
                'backdrop_url': self._get_backdrop_url(movie_data.get('backdrop_path')),
                'imdb_rating': movie_data.get('vote_average', 0),
                'vote_count': movie_data.get('vote_count', 0),
                'popularity': movie_data.get('popularity', 0)
            }
        else:
            # Если не словарь, пробуем преобразовать через __dict__
            try:
                if hasattr(movie_data, '__dict__'):
                    data = movie_data.__dict__
                    return {
                        'movie_id': f"tt{data.get('id', '')}",
                        'tmdb_id': data.get('id'),
                        'title': data.get('title', 'Без названия'),
                        'original_title': data.get('original_title', ''),
                        'year': data.get('release_date', '')[:4] if data.get('release_date') else None,
                        'genres': [],
                        'actors': [],
                        'directors': [],
                        'description': data.get('overview', ''),
                        'poster_url': self._get_poster_url(data.get('poster_path')),
                        'backdrop_url': self._get_backdrop_url(data.get('backdrop_path')),
                        'imdb_rating': data.get('vote_average', 0),
                        'vote_count': data.get('vote_count', 0),
                        'popularity': data.get('popularity', 0)
                    }
            except:
                pass
            
            logger.warning(f"Неизвестный тип данных: {type(movie_data)}")
            return {
                'movie_id': '',
                'tmdb_id': None,
                'title': 'Неизвестный фильм',
                'year': None,
                'genres': [],
                'actors': [],
                'directors': [],
                'description': '',
                'poster_url': None,
                'backdrop_url': None,
                'imdb_rating': 0,
                'vote_count': 0,
                'popularity': 0
            }
    
    def _get_poster_url(self, poster_path: Optional[str]) -> str:
        """Генерирует URL для постера"""
        if poster_path:
            return f"{Config.TMDB_IMAGE_BASE_URL}{Config.TMDB_POSTER_SIZE}{poster_path}"
        return None
    
    def _get_backdrop_url(self, backdrop_path: Optional[str]) -> str:
        """Генерирует URL для фонового изображения"""
        if backdrop_path:
            return f"{Config.TMDB_IMAGE_BASE_URL}{Config.TMDB_BACKDROP_SIZE}{backdrop_path}"
        return None
    
    def get_genres(self) -> List[Dict]:
        """Получение списка жанров"""
        cache_key = "genres"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            genres_api = tmdb.Genres()
            response = genres_api.movie_list(language=self.language)
            
            genres_list = []
            if 'genres' in response:
                for genre in response['genres']:
                    genres_list.append({
                        'id': genre.get('id'),
                        'name': genre.get('name')
                    })
                self.cache.set(cache_key, genres_list)
                return genres_list
            
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении жанров: {e}")
            return []

    def get_movies_by_genres(self, genre_ids: List[int], page: int = 1) -> List[Dict]:
        """
        Получение фильмов по нескольким жанрам
        
        Args:
            genre_ids: список ID жанров
            page: номер страницы
        
        Returns:
            Список фильмов
        """
        try:
            discover = tmdb.Discover()
            response = discover.movie(
                with_genres=','.join(map(str, genre_ids)),
                page=page,
                language=self.language,
                sort_by='popularity.desc',
                vote_count_gte=100  # Только фильмы с минимум 100 голосами
            )
            
            movies = []
            if 'results' in response:
                for movie_data in response['results']:
                    movies.append(self._format_movie_data(movie_data))
            
            logger.info(f"Получено {len(movies)} фильмов по жанрам {genre_ids}")
            return movies
        except Exception as e:
            logger.error(f"Ошибка при получении фильмов по жанрам: {e}")
            return []

    def get_upcoming_movies(self, page: int = 1) -> List[Dict]:
        """
        Получение предстоящих фильмов
        
        Args:
            page: номер страницы
        
        Returns:
            Список предстоящих фильмов
        """
        cache_key = f"upcoming_{page}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            movie = tmdb.Movies()
            response = movie.upcoming(page=page, language=self.language)
            
            movies = []
            if 'results' in response:
                for movie_data in response['results']:
                    movies.append(self._format_movie_data(movie_data))
            
            self.cache.set(cache_key, movies)
            logger.info(f"Получено {len(movies)} предстоящих фильмов")
            return movies
        except Exception as e:
            logger.error(f"Ошибка при получении предстоящих фильмов: {e}")
            return []
    
    def get_now_playing_movies(self, page: int = 1) -> List[Dict]:
        """
        Получение фильмов, которые сейчас в прокате
        
        Args:
            page: номер страницы
        
        Returns:
            Список фильмов в прокате
        """
        cache_key = f"now_playing_{page}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            movie = tmdb.Movies()
            response = movie.now_playing(page=page, language=self.language)
            
            movies = []
            if 'results' in response:
                for movie_data in response['results']:
                    movies.append(self._format_movie_data(movie_data))
            
            self.cache.set(cache_key, movies)
            logger.info(f"Получено {len(movies)} фильмов в прокате")
            return movies
        except Exception as e:
            logger.error(f"Ошибка при получении фильмов в прокате: {e}")
            return []
        
# Создаём глобальный экземпляр сервиса
tmdb_service = TMDBService()