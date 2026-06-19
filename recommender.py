import json
import math
from typing import List, Dict, Optional
from database import Database
from movies_data import SAMPLE_MOVIES

class MovieRecommender:
    """Гибридный алгоритм рекомендаций"""
    
    def __init__(self, db: Database):
        self.db = db
        self.weights = {
            'genre': 0.35,
            'actor': 0.25,
            'director': 0.15,
            'rating': 0.25
        }
    
    def get_recommendations(self, user, top_n: int = 10) -> List[Dict]:
        """
        Генерирует персонализированные рекомендации
        
        Args:
            user: объект пользователя
            top_n: количество рекомендаций
        
        Returns:
            Список фильмов с оценками
        """
        # Получаем все фильмы
        all_movies = self.db.get_all_movies()
        if not all_movies:
            return self._get_popular_movies(top_n)
        
        # Если пользователь не указал предпочтения и не ставил оценки
        if not user.preferences and not user.ratings:
            return self._get_popular_movies(top_n)
        
        # Вычисляем score для каждого фильма
        scored_movies = []
        for movie in all_movies:
            # Пропускаем уже оценённые фильмы
            if movie['movie_id'] in user.ratings:
                continue
                
            score = self._calculate_score(movie, user)
            scored_movies.append({
                **movie,
                'score': round(score, 4)
            })
        
        # Сортируем по убыванию score
        scored_movies.sort(key=lambda x: x['score'], reverse=True)
        
        # Берём топ-N
        recommendations = scored_movies[:top_n]
        
        # Если рекомендаций мало, добавляем популярные фильмы
        if len(recommendations) < top_n:
            popular = self._get_popular_movies(top_n - len(recommendations))
            recommendations.extend(popular)
        
        return recommendations
    
    def _calculate_score(self, movie: Dict, user) -> float:
        """Вычисляет score для одного фильма"""
        score = 0.0
        
        # Проверяем, есть ли предпочтения у пользователя
        if not user.preferences:
            return 0.0
        
        # 1. Совпадение жанров (вес 0.35) - ОБЯЗАТЕЛЬНО
        if user.preferences and 'genres' in user.preferences and user.preferences['genres']:
            genre_score = self._calculate_jaccard_similarity(
                movie['genres'],
                user.preferences.get('genres', [])
            )
            score += genre_score * self.weights['genre']
        
        # 2. Совпадение актёров (вес 0.25) - если выбраны
        if user.preferences and 'actors' in user.preferences and user.preferences['actors']:
            actor_score = self._calculate_jaccard_similarity(
                movie['actors'],
                user.preferences.get('actors', [])
            )
            score += actor_score * self.weights['actor']
        
        # 3. Совпадение режиссёра (вес 0.15) - если выбраны
        if user.preferences and 'directors' in user.preferences and user.preferences['directors']:
            director_score = self._calculate_jaccard_similarity(
                movie['directors'],
                user.preferences.get('directors', [])
            )
            score += director_score * self.weights['director']
        
        # 4. Учёт личных оценок пользователя (вес 0.25)
        if user.ratings:
            # Находим похожие фильмы на основе жанров
            similar_movies = self._find_similar_movies(movie, user)
            if similar_movies:
                rating_score = self._calculate_rating_score(similar_movies, user)
                score += rating_score * self.weights['rating']
        
        return score
    
    def _calculate_jaccard_similarity(self, list1: List, list2: List) -> float:
        """Вычисляет коэффициент Жаккара между двумя списками"""
        if not list1 or not list2:
            return 0.0
        
        set1 = set(list1) if isinstance(list1, list) else set()
        set2 = set(list2) if isinstance(list2, list) else set()
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _find_similar_movies(self, movie: Dict, user, limit: int = 5) -> List[Dict]:
        """Находит фильмы, похожие на заданный (по жанрам)"""
        all_movies = self.db.get_all_movies()
        similar = []
        
        for other in all_movies:
            if other['movie_id'] == movie['movie_id']:
                continue
            
            # Считаем схожесть по жанрам
            genre_sim = self._calculate_jaccard_similarity(
                movie['genres'],
                other['genres']
            )
            
            if genre_sim > 0.2:  # Порог схожести
                similar.append((other, genre_sim))
        
        # Сортируем по схожести
        similar.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in similar[:limit]]
    
    def _calculate_rating_score(self, similar_movies: List[Dict], user) -> float:
        """Вычисляет оценку на основе похожих фильмов"""
        if not similar_movies:
            return 0.0
        
        total_rating = 0.0
        count = 0
        
        for movie in similar_movies:
            if movie['movie_id'] in user.ratings:
                total_rating += user.ratings[movie['movie_id']]
                count += 1
        
        if count == 0:
            return 0.0
        
        # Нормализуем оценку от 0 до 1 (оценки от 1 до 10)
        avg_rating = total_rating / count
        return avg_rating / 10.0
    
    def _get_popular_movies(self, limit: int = 10) -> List[Dict]:
        """Возвращает популярные фильмы (заглушка)"""
        # В реальном проекте здесь был бы запрос к TMDB или другой базе
        popular = self.db.get_all_movies()
        
        # Если БД пуста, создаём тестовые данные
        if not popular:
            return self._create_sample_movies(limit)
        
        # Сортируем по IMDb рейтингу
        popular.sort(key=lambda x: x.get('imdb_rating', 0), reverse=True)
        return popular[:limit]
    
    def _create_sample_movies(self, count: int = 30) -> List[Dict]:
        """Создаёт тестовые фильмы для демонстрации"""
        # Проверяем, сколько фильмов уже есть в БД
        existing_movies = self.db.get_all_movies()
        if existing_movies:
            return existing_movies[:count]  
    
        # Используем данные из movies_data.py
        movies_to_add = SAMPLE_MOVIES[:count]

        
        # Сохраняем в БД
        for movie in movies_to_add:
            self.db.add_movie(movie)
        
        return movies_to_add