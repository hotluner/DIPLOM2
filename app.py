from venv import logger

from flask import Config, Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_session import Session
import secrets
from database import Database
from recommender import MovieRecommender
from models import User
from tmdb_service import tmdb_service
from config import config
import json
from datetime import datetime
import os
import tmdbsimple as tmdb
from movie_selector import MovieSelector

app = Flask(__name__)

# Загружаем конфигурацию
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Настройка сессии
app.config['SECRET_KEY'] = Config.SECRET_KEY if hasattr(Config, 'SECRET_KEY') else secrets.token_hex(16)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_session'
app.config['SESSION_PERMANENT'] = False
Session(app)

# Инициализация БД и рекомендательной системы
db = Database()
recommender = MovieRecommender(db)

movie_selector = MovieSelector()

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    return render_template('index.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        email = request.form.get('email', '').strip()
        
        # Валидация
        if not username:
            flash('Введите имя пользователя', 'danger')
            return render_template('register.html')
        
        if len(username) < 3:
            flash('Имя пользователя должно содержать минимум 3 символа', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'danger')
            return render_template('register.html')
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'danger')
            return render_template('register.html')
        
        # Создаём пользователя
        user = db.create_user(username, password, email)
        if not user:
            flash('Пользователь с таким именем уже существует', 'danger')
            return render_template('register.html')
        
        # Автоматический вход после регистрации
        session['user_id'] = user.user_id
        session['username'] = user.username
        
        flash(f'Добро пожаловать, {username}! 🎬', 'success')
        return redirect(url_for('preferences'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в систему"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Введите имя пользователя и пароль', 'danger')
            return render_template('login.html')
        
        # Аутентификация
        user = db.authenticate_user(username, password)
        if not user:
            flash('Неверное имя пользователя или пароль', 'danger')
            return render_template('login.html')
        
        session['user_id'] = user.user_id
        session['username'] = user.username
        
        flash(f'С возвращением, {username}! 🎬', 'success')
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    """Страница выбора предпочтений (обязательный этап)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Список доступных жанров
    available_genres = [
        'Боевик', 'Драма', 'Комедия', 'Фантастика', 'Ужасы', 
        'Триллер', 'Приключения', 'Криминал', 'Мелодрама', 
        'Документальный', 'Анимация', 'Семейный', 'Военный',
        'Детектив', 'Мистика', 'Фэнтези', 'Исторический', 
        'Музыка', 'Нуар', 'Вестерн'
    ]
    
    # Список стран
    available_countries = [
        'США', 'Великобритания', 'Россия', 'Франция', 'Германия',
        'Италия', 'Испания', 'Канада', 'Австралия', 'Япония',
        'Китай', 'Южная Корея', 'Индия', 'Мексика', 'Бразилия'
    ]
    
    # Годы для выбора (от 1950 до текущего)
    current_year = datetime.now().year
    available_years = list(range(current_year, 1949, -1))
    
    if request.method == 'POST':
        # Получаем выбранные жанры
        selected_genres = request.form.getlist('genres')
        
        # Проверяем, выбран ли хотя бы один жанр
        if not selected_genres:
            flash('Пожалуйста, выберите хотя бы один жанр!', 'danger')
            return render_template('preferences.html', 
                                 user=user,
                                 genres=available_genres,
                                 countries=available_countries,
                                 years=available_years)
        
        # Получаем выбранных актёров из скрытого поля
        selected_actors = request.form.get('actors', '').split(',')
        selected_actors = [a.strip() for a in selected_actors if a.strip()]
        
        # Получаем выбранных режиссёров из скрытого поля
        selected_directors = request.form.get('directors', '').split(',')
        selected_directors = [d.strip() for d in selected_directors if d.strip()]
        
        # Получаем год
        year_from = request.form.get('year_from')
        year_to = request.form.get('year_to')
        
        # Сохраняем предпочтения
        user.preferences = {
            'genres': selected_genres,
            'actors': selected_actors,
            'directors': selected_directors,
            'countries': request.form.getlist('countries'),
            'year_from': year_from if year_from else None,
            'year_to': year_to if year_to else None,
            'selected_at': datetime.now().isoformat()
        }
        db.update_user(user)
        
        flash('Предпочтения сохранены! Теперь оцените фильмы.', 'success')
        return redirect(url_for('rating'))
    
    return render_template('preferences.html', 
                         user=user,
                         genres=available_genres,
                         countries=available_countries,
                         years=available_years)

@app.route('/rating', methods=['GET', 'POST'])
def rating():
    """Страница оценки фильмов - по одному фильму за раз с умным подбором"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Проверяем, выбраны ли предпочтения
    if not user.preferences or not user.preferences.get('genres'):
        flash('Сначала выберите свои предпочтения!', 'warning')
        return redirect(url_for('preferences'))
    
    MIN_RATINGS = 10
    
    # Инициализируем список пропущенных в сессии
    if 'skipped_movies' not in session:
        session['skipped_movies'] = []
    
    # Получаем все фильмы
    all_movies = db.get_all_movies()
    
    # Если фильмов меньше 50, создаём больше
    if len(all_movies) < 50:
        recommender._create_sample_movies(250)
        all_movies = db.get_all_movies()
    
    # Получаем ID оценённых и пропущенных фильмов
    rated_movie_ids = set(user.ratings.keys())
    skipped_movie_ids = set(session['skipped_movies'])
    
    # Настраиваем MovieSelector
    movie_selector.set_context(
        user=user,
        all_movies=all_movies,
        rated_movies=rated_movie_ids,
        skipped_movies=skipped_movie_ids
    )
    
    rated_count = len(rated_movie_ids)
    
    if request.method == 'POST':
        # Проверяем, был ли пропуск
        skip_keys = [key for key in request.form.keys() if key.startswith('skip_')]
        if skip_keys:
            # Сохраняем пропущенный фильм в сессию
            for key in skip_keys:
                movie_id = key.replace('skip_', '')
                if movie_id and movie_id not in session['skipped_movies']:
                    session['skipped_movies'].append(movie_id)
                    session.modified = True
            return redirect(url_for('rating'))
        
        # Сохраняем оценку
        movie_id = request.form.get('movie_id')
        rating_key = f'rating_{movie_id}'
        
        if rating_key in request.form:
            try:
                rating_value = int(request.form[rating_key])
                if 1 <= rating_value <= 10:
                    user.ratings[movie_id] = rating_value
                    db.update_user(user)
                    
                    # Если фильм был в пропущенных, удаляем его оттуда
                    if movie_id in session['skipped_movies']:
                        session['skipped_movies'].remove(movie_id)
                        session.modified = True
                    
                    flash(f'Фильм оценён на {rating_value}/10!', 'success')
            except (ValueError, TypeError):
                pass
        
        # Проверяем, достигнуто ли минимальное количество оценок
        if len(user.ratings) >= MIN_RATINGS:
            # Очищаем пропущенные из сессии
            session.pop('skipped_movies', None)
            return redirect(url_for('recommendations'))
        else:
            return redirect(url_for('rating'))
    
    # GET запрос - используем умный подбор
    next_movie = movie_selector.get_next_movie()
    
    # Получаем статистику
    stats = movie_selector.get_movie_stats()
    
    # Если все фильмы просмотрены, но оценок меньше MIN_RATINGS
    if not next_movie and rated_count < MIN_RATINGS:
        # Сбрасываем пропущенные, чтобы показать их снова
        session['skipped_movies'] = []
        session.modified = True
        flash('Вы просмотрели все фильмы! Попробуйте оценить некоторые из них.', 'info')
        return redirect(url_for('rating'))
    
    return render_template('rating.html', 
                         user=user,
                         movie_to_rate=next_movie,
                         rated_count=rated_count,
                         min_ratings=MIN_RATINGS,
                         total_movies=len(all_movies),
                         skipped_count=len(session.get('skipped_movies', [])),
                         stats=stats)

@app.route('/recommendations')
def recommendations():
    """Страница с рекомендациями"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Проверяем, выбраны ли предпочтения
    if not user.preferences or not user.preferences.get('genres'):
        flash('Сначала выберите свои предпочтения!', 'warning')
        return redirect(url_for('preferences'))
    
    # Проверяем, достаточно ли оценок
    if not user.has_min_ratings(10):
        flash('Оцените как минимум 10 фильмов для получения рекомендаций!', 'warning')
        return redirect(url_for('rating'))
    
    # Проверяем, есть ли уже рекомендации и не устарели ли они
    has_valid_recommendations = False
    recommendations = []
    
    if user.recommendations and user.recommendations.get('items'):
        # Проверяем, не устарели ли рекомендации (например, > 1 дня)
        generated_at = user.recommendations.get('generated_at')
        if generated_at:
            try:
                gen_time = datetime.fromisoformat(generated_at)
                time_diff = datetime.now() - gen_time
                if time_diff.days < 1:
                    has_valid_recommendations = True
                    recommendations = user.recommendations.get('items', [])
            except (ValueError, TypeError):
                pass
        
        # Если рекомендации есть, но устарели - генерируем новые
        if not has_valid_recommendations and user.recommendations.get('items'):
            flash('Рекомендации обновлены с учётом новых оценок!', 'info')
    
    # Если нет валидных рекомендаций - генерируем
    if not has_valid_recommendations:
        # Генерируем рекомендации
        recs = recommender.get_recommendations(user, top_n=25)
        
        # Сохраняем в БД
        user.recommendations = {
            'items': recs,
            'generated_at': datetime.now().isoformat(),
            'total_count': len(recs)
        }
        db.update_user(user)
        recommendations = recs
        flash('Рекомендации сгенерированы!', 'success')
    
    return render_template('recommendations.html', 
                         user=user,
                         recommendations=recommendations or user.recommendations.get('items', []))

@app.route('/movie/<movie_id>')
def movie_detail(movie_id):
    """Детальная информация о фильме"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    movie = db.get_movie(movie_id)
    if not movie:
        return render_template('404.html'), 404
    
    # Проверяем, оценил ли пользователь этот фильм
    user_rating = user.ratings.get(movie_id)
    
    return render_template('movie_detail.html', 
                         movie=movie,
                         user=user,
                         user_rating=user_rating)

@app.route('/admin')
def admin():
    """Административная панель"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Проверяем, является ли пользователь администратором
    if not user.is_admin:
        flash('Доступ запрещён. Требуются права администратора.', 'danger')
        return redirect(url_for('index'))
    
    all_users = db.get_all_users()
    return render_template('admin.html', users=all_users)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Удаление пользователя"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin = db.get_user_by_id(session['user_id'])
    if not admin or not admin.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    
    # Не даём удалить самого себя
    if user_id == admin.user_id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    
    db.delete_user(user_id)
    return jsonify({'success': True})

@app.route('/admin/delete_recommendations/<int:user_id>', methods=['POST'])
def delete_recommendations(user_id):
    """Полное удаление рекомендаций и данных пользователя (только для админа)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin = db.get_user_by_id(session['user_id'])
    if not admin or not admin.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    
    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Полностью очищаем все данные пользователя
    user.preferences = {}
    user.ratings = {}
    user.recommendations = {}
    user.skipped = {}
    
    # Обновляем в базе данных
    db.update_user(user)
    
    # Если это текущий пользователь - очищаем сессию
    if user_id == session['user_id']:
        # Очищаем все данные сессии
        session.pop('skipped_movies', None)
        session.pop('user_recommendations', None)
        
        # Обновляем пользователя в сессии
        updated_user = db.get_user_by_id(user_id)
        if updated_user:
            session['user_id'] = updated_user.user_id
            session['username'] = updated_user.username
    
    # Логируем действие
    logger.info(f"🗑️ Полностью очищены данные пользователя {user.username or user_id}")
    logger.info(f"   Предпочтения: {user.preferences}")
    logger.info(f"   Оценки: {len(user.ratings)}")
    logger.info(f"   Рекомендации: {user.recommendations}")
    
    return jsonify({
        'success': True,
        'message': 'Все данные пользователя удалены. Пользователь должен пройти все этапы заново.',
        'user_id': user_id
    })

@app.route('/admin/update_movies')
def admin_update_movies():
    """Обновление базы данных фильмов из TMDB (только для админа)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user or not user.is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Получаем популярные фильмы
        popular_movies = tmdb_service.get_popular_movies(page=1)
        
        # Добавляем детали для каждого фильма
        added_count = 0
        for movie_data in popular_movies[:30]:  # Ограничиваем 30 фильмами
            # Получаем детальную информацию
            details = tmdb_service.get_movie_details(movie_data['tmdb_id'])
            if details:
                # Проверяем, есть ли фильм в БД
                existing = db.get_movie(details['movie_id'])
                if not existing:
                    db.add_movie(details)
                    added_count += 1
        
        flash(f'Добавлено {added_count} новых фильмов из TMDB!', 'success')
    except Exception as e:
        flash(f'Ошибка при обновлении фильмов: {str(e)}', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/search_movies')
def admin_search_movies():
    """Поиск фильмов в TMDB (только для админа)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'Query required'}), 400
    
    results = tmdb_service.search_movies(query)
    return jsonify(results)

@app.route('/api/search_actors')
def search_actors():
    """Поиск актёров по запросу"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    try:
        # Ищем актёров через TMDB
        search = tmdb.Search()
        response = search.person(query=query, language='ru-RU')
        
        actors = []
        if 'results' in response:
            for person in response['results'][:10]:
                # Проверяем, что это актёр
                if person.get('known_for_department') == 'Acting':
                    actors.append({
                        'id': person['id'],
                        'name': person['name'],
                        'profile_path': person.get('profile_path'),
                        'popularity': person.get('popularity', 0)
                    })
        
        return jsonify(actors)
    except Exception as e:
        print(f"Ошибка поиска актёров: {e}")
        return jsonify([])

@app.route('/api/search_directors')
def search_directors():
    """Поиск режиссёров по запросу"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    try:
        # Ищем режиссёров через TMDB
        search = tmdb.Search()
        response = search.person(query=query, language='ru-RU')
        
        directors = []
        if 'results' in response:
            for person in response['results'][:10]:
                # Проверяем, что это режиссёр
                if person.get('known_for_department') == 'Directing':
                    directors.append({
                        'id': person['id'],
                        'name': person['name'],
                        'profile_path': person.get('profile_path'),
                        'popularity': person.get('popularity', 0)
                    })
        
        return jsonify(directors)
    except Exception as e:
        print(f"Ошибка поиска режиссёров: {e}")
        return jsonify([])

@app.route('/reset_progress', methods=['POST'])
def reset_progress():
    """Сброс прогресса пользователя (очищает предпочтения, оценки и рекомендации)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Очищаем все данные
    user.preferences = {}
    user.ratings = {}
    user.recommendations = {}
    user.skipped = {}
    
    # Обновляем в базе данных
    db.update_user(user)
    
    # Очищаем сессию
    session.pop('skipped_movies', None)
    session.pop('user_recommendations', None)
    
    logger.info(f"🔄 Пользователь {user.username or user.user_id} сбросил свой прогресс")
    
    return jsonify({
        'success': True,
        'message': 'Прогресс сброшен. Начните заново с выбора предпочтений.'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)