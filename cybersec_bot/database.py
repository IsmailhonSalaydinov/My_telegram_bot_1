import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name='cybersecurity.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        """Создание соединения с БД"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Инициализация базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Создание таблицы пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                lessons_completed INTEGER DEFAULT 0,
                total_lessons INTEGER DEFAULT 5,
                avg_score REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создание таблицы прогресса по урокам
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lesson_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                lesson_number INTEGER,
                completed BOOLEAN DEFAULT FALSE,
                score INTEGER DEFAULT 0,
                completed_at TIMESTAMP,
                UNIQUE(user_id, lesson_number),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Создание таблицы результатов тестов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id INTEGER,
                answer INTEGER,
                is_correct BOOLEAN,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
    
    def add_user(self, user_id, username=None, first_name=None, last_name=None):
        """Добавление нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка при добавлении пользователя: {e}")
            return False
        finally:
            conn.close()
    
    def update_user_progress(self, user_id, lesson_num=None, score=0):
        """Обновление прогресса пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Добавляем запись о пройденном уроке (только если еще не пройден)
            if lesson_num and lesson_num <= 5:  # Уроки только 1-5
                cursor.execute('''
                    INSERT OR REPLACE INTO lesson_progress 
                    (user_id, lesson_number, completed, score, completed_at)
                    VALUES (?, ?, TRUE, ?, ?)
                ''', (user_id, lesson_num, score, datetime.now()))
            
            # Обновляем опыт пользователя
            cursor.execute('''
                UPDATE users 
                SET experience = experience + ?,
                    last_active = ?
                WHERE user_id = ?
            ''', (score, datetime.now(), user_id))
            
            # Пересчитываем количество пройденных уроков
            cursor.execute('''
                UPDATE users
                SET lessons_completed = (
                    SELECT COUNT(DISTINCT lesson_number) 
                    FROM lesson_progress 
                    WHERE user_id = ? AND completed = TRUE AND lesson_number <= 5
                )
                WHERE user_id = ?
            ''', (user_id, user_id))
            
            # Пересчитываем уровень (каждые 100 опыта = 1 уровень, начинаем с 1 уровня)
            cursor.execute('''
                UPDATE users
                SET level = 1 + (experience / 100)
                WHERE user_id = ?
            ''', (user_id,))
            
            # Пересчитываем средний балл
            cursor.execute('''
                UPDATE users
                SET avg_score = (
                    SELECT AVG(score) 
                    FROM lesson_progress 
                    WHERE user_id = ? AND completed = TRUE
                )
                WHERE user_id = ?
            ''', (user_id, user_id))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка при обновлении прогресса: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_user_stats(self, user_id):
        """Получение статистики пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT level, experience, lessons_completed, total_lessons, avg_score
                FROM users 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                # Преобразуем уровень в целое число
                level = int(result[0]) if result[0] else 1
                experience = result[1] if result[1] else 0
                lessons_completed = result[2] if result[2] else 0
                total_lessons = result[3] if result[3] else 5
                avg_score = result[4] if result[4] else 0
                
                return (level, experience, lessons_completed, total_lessons, avg_score)
            return None
        except Exception as e:
            print(f"❌ Ошибка при получении статистики: {e}")
            return None
        finally:
            conn.close()
    
    def get_leaderboard(self, limit=10):
        """Получение таблицы лидеров"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT username, level, experience, lessons_completed
                FROM users 
                ORDER BY experience DESC, level DESC
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            leaders = []
            for row in results:
                leaders.append((
                    row[0] if row[0] else "Аноним",
                    int(row[1]) if row[1] else 1,
                    row[2] if row[2] else 0,
                    row[3] if row[3] else 0
                ))
            return leaders
        except Exception as e:
            print(f"❌ Ошибка при получении таблицы лидеров: {e}")
            return []
        finally:
            conn.close()
    
    def add_quiz_result(self, user_id, question_id, answer, is_correct):
        """Добавление результата теста"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO quiz_results (user_id, question_id, answer, is_correct)
                VALUES (?, ?, ?, ?)
            ''', (user_id, question_id, answer, is_correct))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка при добавлении результата теста: {e}")
            return False
        finally:
            conn.close()
    
    def reset_user_progress(self, user_id):
        """Сброс прогресса пользователя (для отладки)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Удаляем прогресс по урокам
            cursor.execute('DELETE FROM lesson_progress WHERE user_id = ?', (user_id,))
            
            # Удаляем результаты тестов
            cursor.execute('DELETE FROM quiz_results WHERE user_id = ?', (user_id,))
            
            # Сбрасываем статистику пользователя
            cursor.execute('''
                UPDATE users 
                SET level = 1, 
                    experience = 0, 
                    lessons_completed = 0,
                    avg_score = 0
                WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            print(f"✅ Прогресс пользователя {user_id} сброшен")
            return True
        except Exception as e:
            print(f"❌ Ошибка при сбросе прогресса: {e}")
            return False
        finally:
            conn.close()

# Создаем глобальный экземпляр базы данных
db = Database()
