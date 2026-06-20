# movie_selector.py - Умный подбор фильмов для оценки

import random
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MovieSelector:
    """
    Класс для умного подбора фильмов для оценки
    """
    
    def __init__(self):
        self.user = None
        self.all_movies = []
        self.rated_movies = set()
        self.skipped_movies = set()
        
    def set_context(self, user, all_movies, rated_movies, skipped_movies):
        """Устанавливает контекст для подбора"""
        self.user = user
        self.all_movies = all_movies
        self.rated_movies = rated_movies
        self.skipped_movies = skipped_movies
    
    def get_next_movie(self) -> Optional[Dict]:
        """
        Главный метод: возвращает следующий фильм для оценки
        """
        # Получаем доступные фильмы
        available = self._get_available_movies()
        
        if not available:
            return None
        
        # Если у пользователя есть предпочтения - используем их
        if self.user.preferences and self.user.preferences.get('genres'):
            return self._get_movie_by_preferences(available)
        
        # Если пользователь уже оценил несколько фильмов - ищем похожие
        if len(self.rated_movies) >= 3:
            return self._get_movie_by_similarity(available)
        
        # Иначе - случайный фильм
        return self._get_random_movie(available)
    
    def _get_available_movies(self) -> List[Dict]:
        """Получает список доступных фильмов (не оценённых и не пропущенных)"""
        available = []
        for movie in self.all_movies:
            movie_id = movie.get('movie_id')
            if movie_id not in self.rated_movies and movie_id not in self.skipped_movies:
                available.append(movie)
        return available
    
    def _get_movie_by_preferences(self, available: List[Dict]) -> Dict:
        """
        Выбирает фильм на основе предпочтений пользователя
        Использует разные стратегии для разнообразия
        """
        if not available:
            return None
        
        # Получаем предпочтения
        preferred_genres = set(self.user.preferences.get('genres', []))
        preferred_actors = set(self.user.preferences.get('actors', []))
        preferred_directors = set(self.user.preferences.get('directors', []))
        
        # Вычисляем score для каждого фильма
        scored_movies = []
        for movie in available:
            score = 0
            movie_genres = set(movie.get('genres', []))
            movie_actors = set(movie.get('actors', []))
            movie_directors = set(movie.get('directors', []))
            
            # 1. Совпадение жанров (вес 0.5)
            if preferred_genres:
                genre_match = len(movie_genres & preferred_genres) / max(len(preferred_genres), 1)
                score += genre_match * 0.5
            
            # 2. Совпадение актёров (вес 0.3)
            if preferred_actors:
                actor_match = len(movie_actors & preferred_actors) / max(len(preferred_actors), 1)
                score += actor_match * 0.3
            
            # 3. Совпадение режиссёров (вес 0.2)
            if preferred_directors:
                director_match = len(movie_directors & preferred_directors) / max(len(preferred_directors), 1)
                score += director_match * 0.2
            
            # Добавляем бонус за популярность (0-0.1)
            popularity = movie.get('popularity', 0) / 100
            score += min(popularity, 0.1)
            
            scored_movies.append((movie, score))
        
        # Сортируем по убыванию score
        scored_movies.sort(key=lambda x: x[1], reverse=True)
        
        # Берем топ-10 самых релевантных
        top_movies = [m[0] for m in scored_movies[:10]]
        
        # Выбираем случайный из топ-10 для разнообразия
        return random.choice(top_movies) if top_movies else available[0]
    
    def _get_movie_by_similarity(self, available: List[Dict]) -> Dict:
        """
        Выбирает фильм, похожий на уже оценённые пользователем
        """
        if not available or not self.rated_movies:
            return self._get_random_movie(available)
        
        # Получаем жанры оценённых фильмов
        rated_genres = set()
        rated_actors = set()
        rated_directors = set()
        
        for movie_id in self.rated_movies:
            movie = self._find_movie_by_id(movie_id)
            if movie:
                rated_genres.update(movie.get('genres', []))
                rated_actors.update(movie.get('actors', []))
                rated_directors.update(movie.get('directors', []))
        
        if not rated_genres:
            return self._get_random_movie(available)
        
        # Вычисляем схожесть с оценёнными фильмами
        scored_movies = []
        for movie in available:
            movie_genres = set(movie.get('genres', []))
            
            # Коэффициент Жаккара для жанров
            if movie_genres and rated_genres:
                intersection = len(movie_genres & rated_genres)
                union = len(movie_genres | rated_genres)
                similarity = intersection / union if union > 0 else 0
            else:
                similarity = 0
            
            # Добавляем бонус за свежесть (чтобы не показывать слишком похожие)
            freshness = 1.0 - similarity
            
            score = similarity * 0.7 + freshness * 0.3
            scored_movies.append((movie, score))
        
        # Сортируем по убыванию
        scored_movies.sort(key=lambda x: x[1], reverse=True)
        
        # Берем топ-15 и выбираем случайный
        top_movies = [m[0] for m in scored_movies[:15]]
        return random.choice(top_movies) if top_movies else available[0]
    
    def _get_random_movie(self, available: List[Dict]) -> Dict:
        """Выбирает случайный фильм с учётом разнообразия"""
        if not available:
            return None
        
        # Если фильмов мало - просто случайный
        if len(available) <= 20:
            return random.choice(available)
        
        # Пытаемся выбрать фильм из разных жанров
        # Группируем по жанрам
        genres_groups = {}
        for movie in available:
            genres = movie.get('genres', [])
            if genres:
                main_genre = genres[0]
                if main_genre not in genres_groups:
                    genres_groups[main_genre] = []
                genres_groups[main_genre].append(movie)
        
        # Выбираем случайный жанр
        if genres_groups:
            random_genre = random.choice(list(genres_groups.keys()))
            return random.choice(genres_groups[random_genre])
        
        return random.choice(available)
    
    def _find_movie_by_id(self, movie_id: str) -> Optional[Dict]:
        """Находит фильм по ID в списке всех фильмов"""
        for movie in self.all_movies:
            if movie.get('movie_id') == movie_id:
                return movie
        return None
    
    def get_movie_stats(self) -> Dict:
        """
        Получает статистику по доступным фильмам
        """
        available = self._get_available_movies()
        
        # Статистика по жанрам
        genres_count = {}
        for movie in available:
            for genre in movie.get('genres', []):
                genres_count[genre] = genres_count.get(genre, 0) + 1
        
        # Средняя популярность
        avg_popularity = sum(m.get('popularity', 0) for m in available) / max(len(available), 1)
        
        return {
            'total_available': len(available),
            'total_rated': len(self.rated_movies),
            'total_skipped': len(self.skipped_movies),
            'genres_count': genres_count,
            'avg_popularity': avg_popularity,
            'has_preferences': bool(self.user.preferences and self.user.preferences.get('genres'))
        }