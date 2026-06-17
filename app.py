from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_session import Session
import secrets
from database import Database
from recommender import MovieRecommender
from models import User
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
Session(app)

# Инициализация БД и рекомендательной системы
db = Database()
recommender = MovieRecommender(db)

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
    """Страница выбора предпочтений"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Список доступных жанров
    available_genres = ['Боевик', 'Драма', 'Комедия', 'Фантастика', 'Ужасы', 
        'Триллер', 'Приключения', 'Криминал', 'Мелодрама', 
        'Документальный', 'Анимация', 'Семейный', 'Военный',
        'Детектив', 'Мистика', 'Фэнтези', 'Исторический', 
        'Музыка', 'Нуар', 'Вестерн']
    
    # Список актёров и режиссёров (можно расширить)
    available_actors = ['Леонардо ДиКаприо', 'Том Хэнкс', 'Морган Фриман', 
        'Аль Пачино', 'Брэд Питт', 'Киану Ривз', 'Джонни Депп',
        'Роберт Де Ниро', 'Мэтт Деймон', 'Кристиан Бэйл',
        'Хоакин Феникс', 'Элайджа Вуд', 'Иэн Маккеллен',
        'Вигго Мортенсен', 'Майкл Дж. Фокс', 'Арнольд Шварценеггер',
        'Сигурни Уивер', 'Эми Адамс', 'Эмма Стоун', 'Райан Гослинг',
        'Том Харди', 'Шарлиз Терон', 'Марлон Брандо', 'Джеймс Стюарт']
    available_directors = ['Кристофер Нолан', 'Джеймс Кэмерон', 'Квентин Тарантино',
        'Фрэнк Дарабонт', 'Стивен Спилберг', 'Питер Джексон',
        'Ридли Скотт', 'Дэвид Финчер', 'Дени Вильнёв',
        'Фрэнсис Форд Коппола', 'Роберт Земекис', 'Джордж Лукас',
        'Хаяо Миядзаки', 'Макото Синкай', 'Пол Томас Андерсон',
        'Роберт Эггерс', 'Дэмьен Шазелл']
    
    if request.method == 'POST':
        # Сохраняем предпочтения
        user.preferences = {
            'genres': request.form.getlist('genres'),
            'actors': request.form.getlist('actors'),
            'directors': request.form.getlist('directors'),
            'selected_at': None
        }
        db.update_user(user)
        
        return redirect(url_for('rating'))
    
    return render_template('preferences.html', 
                         user=user,
                         genres=available_genres,
                         actors=available_actors,
                         directors=available_directors)

@app.route('/rating', methods=['GET', 'POST'])
def rating():
    """Страница оценки фильмов - по одному фильму за раз"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    MIN_RATINGS = 10
    
    # Инициализируем список пропущенных в сессии
    if 'skipped_movies' not in session:
        session['skipped_movies'] = []
    
    # Получаем все фильмы
    all_movies = db.get_all_movies()
    
    # Если фильмов нет или меньше 20, создаём больше
    if len(all_movies) < 20:
        recommender._create_sample_movies(30)
        all_movies = db.get_all_movies()
    
    # Исключаем уже оценённые и пропущенные (из сессии)
    rated_movie_ids = set(user.ratings.keys())
    skipped_movie_ids = set(session['skipped_movies'])
    
    # Фильтруем: убираем оценённые и пропущенные
    unrated_movies = [
        m for m in all_movies 
        if m['movie_id'] not in rated_movie_ids 
        and m['movie_id'] not in skipped_movie_ids
    ]
    
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
    
    # GET запрос - показываем следующий фильм для оценки
    next_movie = unrated_movies[0] if unrated_movies else None
    
    # Если все фильмы просмотрены, но оценок меньше 10
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
                         skipped_count=len(session.get('skipped_movies', [])))

@app.route('/recommendations')
def recommendations():
    """Страница с рекомендациями"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Если пользователь ещё не набрал 10 оценок
    if not user.has_min_ratings(10):
        return redirect(url_for('rating'))
    
    # Генерируем рекомендации
    recs = recommender.get_recommendations(user, top_n=10)
    
    # Сохраняем в БД
    user.recommendations = {
        'items': recs,
        'generated_at': None,
        'total_count': len(recs)
    }
    db.update_user(user)
    
    return render_template('recommendations.html', 
                         user=user,
                         recommendations=recs)

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
    """Удаление рекомендаций пользователя"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin = db.get_user_by_id(session['user_id'])
    if not admin or not admin.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    
    user = db.get_user_by_id(user_id)
    if user:
        user.recommendations = {}
        db.update_user(user)
        return jsonify({'success': True})
    return jsonify({'error': 'User not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)