import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from database import db

import os

# Роутер для админ-команд
admin_router = Router()

# Токен бота
BOT_TOKEN = "8778190926:AAFWOk-4RAxG0WHZuMWjSK94TGtFS5NG2Hk"

# Проверяем токен
if not BOT_TOKEN:
    print("❌ ОШИБКА: Не найден BOT_TOKEN!")
    exit(1)

# Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Включаем админ-роутер
dp.include_router(admin_router)

# Список администраторов (загружается из файла)
ADMIN_IDS = []

# ============= СОСТОЯНИЯ ДЛЯ АДМИН-ПАНЕЛИ =============
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_stats_user = State()
    waiting_for_reset_user = State()
    waiting_for_add_admin = State()
    waiting_for_remove_admin = State()

# ============= КЛАВИАТУРЫ =============

def get_main_keyboard():
    """Клавиатура главного меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Уроки"), KeyboardButton(text="🎯 Тесты")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🏆 Достижения")],
            [KeyboardButton(text="🥇 Лидеры"), KeyboardButton(text="📅 Ежедневные задания")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_lessons_keyboard():
    """Клавиатура выбора уроков"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1️⃣ Урок 1: Основы"), KeyboardButton(text="2️⃣ Урок 2: Пароли")],
            [KeyboardButton(text="3️⃣ Урок 3: Фишинг"), KeyboardButton(text="4️⃣ Урок 4: Шифрование")],
            [KeyboardButton(text="5️⃣ Урок 5: Сети"), KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_tasks_keyboard():
    """Клавиатура для ежедневных заданий"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Отметить задание"), KeyboardButton(text="📋 Мои задания")],
            [KeyboardButton(text="🎁 Получить награду"), KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_tests_keyboard():
    """Клавиатура для тестов"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Тест 1: Основы"), KeyboardButton(text="📝 Тест 2: Безопасность")],
            [KeyboardButton(text="📊 Результаты тестов"), KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_quiz_keyboard(question_num):
    """Inline клавиатура для тестов"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="А", callback_data=f"quiz_{question_num}_1"),
             InlineKeyboardButton(text="Б", callback_data=f"quiz_{question_num}_2")],
            [InlineKeyboardButton(text="В", callback_data=f"quiz_{question_num}_3"),
             InlineKeyboardButton(text="Г", callback_data=f"quiz_{question_num}_4")],
        ]
    )
    return keyboard

def get_admin_keyboard():
    """Клавиатура админ-панели (основная)"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Статистика пользователей", callback_data="admin_stats_users")],
            [InlineKeyboardButton(text="📊 Общая статистика", callback_data="admin_stats_general")],
            [InlineKeyboardButton(text="🔍 Статистика по юзеру", callback_data="admin_stats_specific")],
            [InlineKeyboardButton(text="📢 Рассылка сообщений", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="🗃️ Инфо о БД", callback_data="admin_db_info")],
            [InlineKeyboardButton(text="🔄 Сброс прогресса", callback_data="admin_reset_menu")],
            [InlineKeyboardButton(text="👑 Управление админами", callback_data="admin_manage_admins")],
            [InlineKeyboardButton(text="📈 Топ пользователей", callback_data="admin_top_users")],
            [InlineKeyboardButton(text="🔄 Обновить панель", callback_data="admin_refresh")],
            [InlineKeyboardButton(text="❌ Закрыть панель", callback_data="admin_close")]
        ]
    )
    return keyboard

def get_admin_reset_keyboard():
    """Клавиатура для сброса прогресса"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Сбросить свой прогресс", callback_data="admin_reset_self")],
            [InlineKeyboardButton(text="🗑️ Сбросить прогресс юзера", callback_data="admin_reset_user")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
        ]
    )
    return keyboard

def get_admin_manage_keyboard():
    """Клавиатура управления админами"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_admin")],
            [InlineKeyboardButton(text="➖ Удалить админа", callback_data="admin_remove_admin")],
            [InlineKeyboardButton(text="👑 Список админов", callback_data="admin_list_admins")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
        ]
    )
    return keyboard

# ============= ФУНКЦИИ ДЛЯ АДМИН-ПАНЕЛИ =============

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

def load_admin_ids():
    """Загрузка списка администраторов из файла"""
    global ADMIN_IDS
    try:
        with open('admin_ids.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    admin_id = int(line)
                    if admin_id not in ADMIN_IDS:
                        ADMIN_IDS.append(admin_id)
        print(f"✅ Загружено {len(ADMIN_IDS)} администраторов")
    except FileNotFoundError:
        # Создаем файл с текущим админом
        with open('admin_ids.txt', 'w') as f:
            f.write("1355575267\n")
        ADMIN_IDS = [1355575267]
        print("✅ Создан файл администраторов")
    except Exception as e:
        print(f"❌ Ошибка при загрузке администраторов: {e}")

async def send_admin_panel(chat_id: int, message_id: int = None):
    """Отправка или обновление админ-панели"""
    admin_text = """
🔐 <b>АДМИН ПАНЕЛЬ</b> <i>(только для администраторов)</i>

<b>Доступные функции:</b>
• 👥 Статистика пользователей
• 📊 Общая статистика бота
• 🔍 Статистика конкретного пользователя
• 📢 Рассылка сообщений всем пользователям
• 🗃️ Информация о базе данных
• 🔄 Сброс прогресса (свой или пользователя)
• 👑 Управление администраторами
• 📈 Топ пользователей

<b>Статус:</b> Панель активна
<b>Действие:</b> Выберите опцию ниже
"""
    
    if message_id:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=admin_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=admin_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )

# ============= ОБРАБОТЧИКИ АДМИН-КОМАНД =============

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Админ панель - ТОЛЬКО ДЛЯ АДМИНОВ"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ <b>Доступ запрещен.</b> Эта команда только для администраторов.", parse_mode=ParseMode.HTML)
        return
    
    await send_admin_panel(message.chat.id)
    print(f"✅ Админ {message.from_user.first_name} открыл панель")

@admin_router.callback_query(F.data.startswith("admin_"))
async def process_admin_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка всех админ-действий"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен.")
        return
    
    action = callback.data
    
    try:
        if action == "admin_stats_users":
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Общее количество
            cursor.execute('SELECT COUNT(*) FROM users')
            total = cursor.fetchone()[0]
            
            # Активные за последние 7 дней
            cursor.execute('SELECT COUNT(*) FROM users WHERE last_active > datetime("now", "-7 days")')
            active_7 = cursor.fetchone()[0]
            
            # Активные за последние 30 дней
            cursor.execute('SELECT COUNT(*) FROM users WHERE last_active > datetime("now", "-30 days")')
            active_30 = cursor.fetchone()[0]
            
            # Новые за последние 7 дней
            cursor.execute('SELECT COUNT(*) FROM users WHERE created_at > datetime("now", "-7 days")')
            new_7 = cursor.fetchone()[0]
            
            conn.close()
            
            stats_text = f"""
📊 <b>СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ</b>

👥 <b>Всего пользователей:</b> {total}
🔥 <b>Активные (7 дней):</b> {active_7}
📅 <b>Активные (30 дней):</b> {active_30}
🆕 <b>Новые (7 дней):</b> {new_7}

💡 <i>Используйте "🔍 Статистика по юзеру" для детальной информации</i>
"""
            
            await callback.message.edit_text(
                stats_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            
        elif action == "admin_stats_general":
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM users')
            total = cursor.fetchone()[0]
            
            cursor.execute('SELECT AVG(level) FROM users')
            avg_level = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT AVG(experience) FROM users')
            avg_exp = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT SUM(lessons_completed) FROM users')
            total_lessons = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT COUNT(*) FROM quiz_results')
            total_quiz_answers = cursor.fetchone()[0] or 0
            
            conn.close()
            
            stats_text = f"""
📈 <b>ОБЩАЯ СТАТИСТИКА БОТА</b>

👥 <b>Пользователей:</b> {total}
🏅 <b>Средний уровень:</b> {avg_level:.1f}
⭐ <b>Средний опыт:</b> {avg_exp:.1f}
📚 <b>Всего пройдено уроков:</b> {total_lessons}
🎯 <b>Всего ответов в тестах:</b> {total_quiz_answers}

📅 <b>Бот запущен:</b> Активен
🔄 <b>Последнее обновление:</b> Сейчас
"""
            
            await callback.message.edit_text(
                stats_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats_general"),
                         InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            
        elif action == "admin_stats_specific":
            await callback.message.edit_text(
                "🔍 <b>ПОЛУЧЕНИЕ СТАТИСТИКИ ПОЛЬЗОВАТЕЛЯ</b>\n\n"
                "Введите username пользователя (например: @username) или его ID:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            await state.set_state(AdminStates.waiting_for_stats_user)
            
        elif action == "admin_broadcast":
            await callback.message.edit_text(
                "📢 <b>РАССЫЛКА СООБЩЕНИЙ</b>\n\n"
                "Введите текст для рассылки всем пользователям:\n\n"
                "<i>Поддерживается HTML-разметка</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            await state.set_state(AdminStates.waiting_for_broadcast)
            
        elif action == "admin_db_info":
            import os
            
            db_name = 'cybersecurity.db'
            if os.path.exists(db_name):
                size = os.path.getsize(db_name)
                size_kb = size / 1024
                
                conn = db.get_connection()
                cursor = conn.cursor()
                
                # Получаем информацию о таблицах
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                tables_info = []
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    tables_info.append(f"• {table_name}: {count} записей")
                
                conn.close()
                
                info_text = f"""
🗃️ <b>ИНФОРМАЦИЯ О БАЗЕ ДАННЫХ</b>

📁 <b>Имя файла:</b> {db_name}
📊 <b>Размер:</b> {size_kb:.2f} KB ({size} байт)
📅 <b>Последнее изменение:</b> {os.path.getmtime(db_name):.0f}

🔧 <b>Таблицы и записи:</b>
{chr(10).join(tables_info)}

💾 <b>Путь:</b> {os.path.abspath(db_name)}
"""
            else:
                info_text = "❌ Файл базы данных не найден."
            
            await callback.message.edit_text(
                info_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            
        elif action == "admin_reset_menu":
            await callback.message.edit_text(
                "🔄 <b>СБРОС ПРОГРЕССА</b>\n\n"
                "Выберите опцию:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_admin_reset_keyboard()
            )
            
        elif action == "admin_reset_self":
            db.reset_user_progress(callback.from_user.id)
            await callback.message.edit_text(
                "✅ <b>Ваш прогресс был сброшен!</b>\n\n"
                "Теперь вы можете начать заново. Используйте /start",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            
        elif action == "admin_reset_user":
            await callback.message.edit_text(
                "🗑️ <b>СБРОС ПРОГРЕССА ПОЛЬЗОВАТЕЛЯ</b>\n\n"
                "Введите username пользователя (например: @username) или его ID:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            await state.set_state(AdminStates.waiting_for_reset_user)
            
        elif action == "admin_manage_admins":
            await callback.message.edit_text(
                "👑 <b>УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ</b>\n\n"
                "Выберите действие:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_admin_manage_keyboard()
            )
            
        elif action == "admin_add_admin":
            await callback.message.edit_text(
                "➕ <b>ДОБАВЛЕНИЕ АДМИНИСТРАТОРА</b>\n\n"
                "Введите ID пользователя для добавления в администраторы:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            await state.set_state(AdminStates.waiting_for_add_admin)
            
        elif action == "admin_remove_admin":
            await callback.message.edit_text(
                "➖ <b>УДАЛЕНИЕ АДМИНИСТРАТОРА</b>\n\n"
                "Введите ID пользователя для удаления из администраторов:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            await state.set_state(AdminStates.waiting_for_remove_admin)
            
        elif action == "admin_list_admins":
            admins_text = "👑 <b>СПИСОК АДМИНИСТРАТОРОВ</b>\n\n"
            
            for i, admin_id in enumerate(ADMIN_IDS, 1):
                try:
                    user = await bot.get_chat(admin_id)
                    name = user.first_name or user.username or str(admin_id)
                    admins_text += f"{i}. {name} (ID: {admin_id})\n"
                except:
                    admins_text += f"{i}. ID: {admin_id} (пользователь не найден)\n"
            
            admins_text += f"\n📊 Всего: {len(ADMIN_IDS)} администратор(ов)"
            
            await callback.message.edit_text(
                admins_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Обновить список", callback_data="admin_list_admins"),
                         InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            
        elif action == "admin_top_users":
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, level, experience, lessons_completed 
                FROM users 
                ORDER BY experience DESC 
                LIMIT 10
            ''')
            top10 = cursor.fetchall()
            
            conn.close()
            
            leaderboard_text = "🏆 <b>ТОП-10 ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
            
            for i, row in enumerate(top10, 1):
                username = row[0] or "Аноним"
                if username != "Аноним" and not username.startswith("@"):
                    username = f"@{username}"
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                leaderboard_text += f"{medal} {username}\n"
                leaderboard_text += f"   Уровень: {row[1]} | ⭐ {row[2]} | 📚 {row[3]}\n\n"
            
            await callback.message.edit_text(
                leaderboard_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_top_users"),
                         InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                    ]
                )
            )
            
        elif action == "admin_refresh":
            await send_admin_panel(callback.message.chat.id, callback.message.message_id)
            
        elif action == "admin_back_to_menu":
            await send_admin_panel(callback.message.chat.id, callback.message.message_id)
            
        elif action == "admin_close":
            await callback.message.delete()
            await callback.answer("Панель закрыта")
            return
            
        await callback.answer()
        
    except Exception as e:
        print(f"❌ Ошибка в админ-панели: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка!</b>\n\n{str(e)}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
                ]
            )
        )
        await callback.answer()

# ============= ОБРАБОТЧИКИ ВВОДА ДАННЫХ =============

@dp.message(AdminStates.waiting_for_stats_user)
async def process_stats_user(message: types.Message, state: FSMContext):
    """Обработка ввода пользователя для статистики"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    target = message.text.strip().replace('@', '')
    
    # Ищем пользователя
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Пробуем найти по username или ID
        cursor.execute('''
            SELECT user_id, username, first_name, last_name, level, experience, 
                   lessons_completed, created_at, last_active
            FROM users 
            WHERE username = ? OR user_id = ?
        ''', (target, target if target.isdigit() else 0))
        
        user_data = cursor.fetchone()
        
        if user_data:
            stats_text = f"""
📊 <b>СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ</b>

👤 <b>ID:</b> {user_data[0]}
📛 <b>Имя:</b> {user_data[2]} {user_data[3] or ''}
🔗 <b>Username:</b> @{user_data[1] or 'нет'}

🏅 <b>Уровень:</b> {user_data[4]}
⭐ <b>Опыт:</b> {user_data[5]}
📚 <b>Уроки:</b> {user_data[6]}/5

📅 <b>Зарегистрирован:</b> {user_data[7]}
🕐 <b>Был активен:</b> {user_data[8]}
"""
        else:
            stats_text = "❌ Пользователь не найден."
    except Exception as e:
        print(f"Ошибка: {e}")
        stats_text = "❌ Ошибка при получении данных."
    finally:
        conn.close()
    
    await message.answer(
        stats_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
            ]
        )
    )
    await state.clear()

@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast_text(message: types.Message, state: FSMContext):
    """Обработка текста для рассылки"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    broadcast_text = message.text
    
    # Подтверждение
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back_to_menu")]
        ]
    )
    
    await message.answer(
        f"📢 <b>ПРЕДПРОСМОТР РАССЫЛКИ</b>\n\n"
        f"{broadcast_text}\n\n"
        f"<i>Будет отправлено всем пользователям бота.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    # Сохраняем текст в state
    await state.update_data(broadcast_text=broadcast_text)
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_reset_user)
async def process_reset_user(message: types.Message, state: FSMContext):
    """Обработка сброса прогресса пользователя"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    target = message.text.strip().replace('@', '')
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Находим пользователя
        cursor.execute('SELECT user_id, username FROM users WHERE username = ? OR user_id = ?', 
                      (target, target if target.isdigit() else 0))
        user_data = cursor.fetchone()
        
        if user_data:
            user_id = user_data[0]
            username = user_data[1] or f"ID {user_id}"
            
            # Сбрасываем прогресс
            db.reset_user_progress(user_id)
            
            result_text = f"✅ Прогресс пользователя @{username} сброшен!"
        else:
            result_text = "❌ Пользователь не найден."
    except Exception as e:
        print(f"Ошибка: {e}")
        result_text = f"❌ Ошибка при сбросе прогресса: {e}"
    finally:
        conn.close()
    
    await message.answer(
        result_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
            ]
        )
    )
    await state.clear()

@dp.message(AdminStates.waiting_for_add_admin)
async def process_add_admin(message: types.Message, state: FSMContext):
    """Обработка добавления администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    admin_id = message.text.strip()
    
    if not admin_id.isdigit():
        await message.answer("❌ ID должен быть числом!")
        return
    
    admin_id = int(admin_id)
    
    # Проверяем, есть ли уже такой ID
    if admin_id in ADMIN_IDS:
        result_text = f"❌ Пользователь {admin_id} уже администратор."
    else:
        # Добавляем в список
        ADMIN_IDS.append(admin_id)
        
        # Сохраняем в файл
        try:
            with open('admin_ids.txt', 'a') as f:
                f.write(f"{admin_id}\n")
            result_text = f"✅ Пользователь {admin_id} добавлен в администраторы."
        except Exception as e:
            result_text = f"✅ Пользователь {admin_id} добавлен, но ошибка при сохранении в файл: {e}"
    
    await message.answer(
        result_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
            ]
        )
    )
    await state.clear()

@dp.message(AdminStates.waiting_for_remove_admin)
async def process_remove_admin(message: types.Message, state: FSMContext):
    """Обработка удаления администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    admin_id = message.text.strip()
    
    if not admin_id.isdigit():
        await message.answer("❌ ID должен быть числом!")
        return
    
    admin_id = int(admin_id)
    
    # Нельзя удалить себя
    if admin_id == message.from_user.id:
        result_text = "❌ Нельзя удалить самого себя."
    elif admin_id in ADMIN_IDS:
        # Удаляем из списка
        ADMIN_IDS.remove(admin_id)
        
        # Обновляем файл
        try:
            with open('admin_ids.txt', 'w') as f:
                for aid in ADMIN_IDS:
                    f.write(f"{aid}\n")
            result_text = f"✅ Пользователь {admin_id} удален из администраторов."
        except Exception as e:
            result_text = f"✅ Пользователь {admin_id} удален, но ошибка при сохранении в файл: {e}"
    else:
        result_text = f"❌ Пользователь {admin_id} не найден в списке администраторов."
    
    await message.answer(
        result_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
            ]
        )
    )
    await state.clear()

# ============= ОБРАБОТЧИК ПОДТВЕРЖДЕНИЯ РАССЫЛКИ =============

@dp.callback_query(F.data == "broadcast_confirm")
async def process_broadcast_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение и отправка рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен.")
        return
    
    # Получаем текст из state
    data = await state.get_data()
    broadcast_text = data.get('broadcast_text', '')
    
    await callback.message.edit_text("🔄 <b>Начинаю рассылку...</b>", parse_mode=ParseMode.HTML)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    for user_row in users:
        try:
            await callback.bot.send_message(
                user_row[0],
                f"📢 <b>ВАЖНОЕ ОБЪЯВЛЕНИЕ ОТ АДМИНИСТРАЦИИ</b>\n\n{broadcast_text}",
                parse_mode=ParseMode.HTML
            )
            success += 1
            await asyncio.sleep(0.05)  # Защита от лимитов
        except:
            failed += 1
    
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"✅ Успешно: {success}\n"
        f"❌ Не удалось: {failed}\n"
        f"📊 Всего: {success + failed}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
            ]
        )
    )
    
    await state.clear()
    await callback.answer()

# ============= СТАРЫЕ АДМИН КОМАНДЫ (для совместимости) =============

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика конкретного пользователя (старая команда)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    # Открываем админ панель с нужным состоянием
    await message.answer(
        "🔍 <b>ПОЛУЧЕНИЕ СТАТИСТИКИ ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        "Введите username пользователя (например: @username) или его ID:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
            ]
        )
    )

@dp.message(Command("users"))
async def cmd_users(message: types.Message):
    """Количество пользователей (старая команда)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    # Перенаправляем в админ панель
    await send_admin_panel(message.chat.id)

@dp.message(Command("db_info"))
async def cmd_db_info(message: types.Message):
    """Информация о базе данных (старая команда)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    # Перенаправляем в админ панель
    await send_admin_panel(message.chat.id)

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    """Рассылка сообщений (старая команда)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    # Открываем админ панель с рассылкой
    await message.answer(
        "📢 <b>РАССЫЛКА СООБЩЕНИЙ</b>\n\n"
        "Введите текст для рассылки всем пользователям:\n\n"
        "<i>Поддерживается HTML-разметка</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back_to_menu")]
            ]
        )
    )
    
##++++++++++++++++++++++start+++++++++++++    
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user = message.from_user
    user_name = user.first_name
    
    # Регистрируем пользователя в БД
    try:
        db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
    except Exception as e:
        print(f"❌ Ошибка при добавлении пользователя: {e}")
    
    # Получаем статистику пользователя
    stats = get_user_detailed_stats(user.id)  # Новая функция!
    
    welcome_text = f"""
👋 Привет, {user_name}!

Я — твой персональный бот-тренер по кибербезопасности!
Я помогу тебе освоить основы цифровой безопасности в увлекательной форме.

{stats['short_stats']}

🎮 <b>Что я умею:</b>
• 📚 Давать уроки по разным темам кибербезопасности
• 🎯 Проверять знания через тесты и задачи
• 🏆 Отслеживать твой прогресс и повышать уровень
• 🥇 Соревноваться с другими в таблице лидеров

👇 Выбери раздел в меню ниже!
    """
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    print(f"✅ Пользователь {user_name} запустил бота")


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    """Сброс прогресса"""
    user = message.from_user
    
    # Проверяем права
    ADMIN_IDS = [1355575267, ]
    if user.id not in ADMIN_IDS:
        await message.answer("❌ Доступ запрещен. Эта команда только для администраторов.")
        return
    
    # Создаем клавиатуру подтверждения
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, сбросить", callback_data="reset_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="reset_cancel")]
        ]
    )
    
    await message.answer(
        "⚠️ <b>Вы уверены, что хотите сбросить свой прогресс?</b>\n\n"
        "Все ваши достижения, опыт и пройденные уроки будут удалены.\n"
        "Это действие нельзя отменить!",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("reset_"))
async def process_reset_callback(callback: types.CallbackQuery):
    """Обработка подтверждения сброса"""
    action = callback.data
    
    if action == "reset_confirm":
        db.reset_user_progress(callback.from_user.id)
        await callback.message.edit_text(
            "✅ <b>Ваш прогресс был сброшен!</b>\n\n"
            "Теперь вы можете начать заново. Используйте /start",
            parse_mode=ParseMode.HTML
        )
        print(f"✅ Пользователь {callback.from_user.first_name} сбросил прогресс")
        
    elif action == "reset_cancel":
        await callback.message.edit_text(
            "❌ <b>Сброс прогресса отменен.</b>\n\n"
            "Ваши данные сохранены.",
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()

@dp.message(Command("mystats"))
async def cmd_mystats(message: types.Message):
    """Показать мою статистику"""
    user = message.from_user
    
    # Получаем статистику из БД
    stats = db.get_user_stats(user.id)
    
    if stats:
        level, experience, lessons_completed, total_lessons, avg_score = stats
        
        # Рассчитываем прогресс до следующего уровня
        exp_to_next = 100 - (experience % 100) if experience % 100 != 0 else 0
        current_level_exp = experience % 100
        
        # Создаем прогресс-бар
        filled = int(current_level_exp / 10)
        empty = 10 - filled
        progress_bar = "█" * filled + "░" * empty
        
        stats_text = f"""
📊 <b>ВАША ТЕКУЩАЯ СТАТИСТИКА</b>

👤 Имя: {user.first_name}
🏅 Уровень: {level}
⭐ Опыт: {experience}
📚 Пройдено уроков: {lessons_completed}/{total_lessons}
🎯 Средний балл: {avg_score:.1f if avg_score else 0}

📈 Прогресс до уровня {level + 1}:
{progress_bar} {current_level_exp}%
⏳ Осталось опыта: {exp_to_next}

🔍 <i>Чтобы увидеть больше статистики, нажмите "📊 Статистика"</i>
"""
    else:
        stats_text = "❌ Не удалось получить вашу статистику. Попробуйте снова."
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

# ============= АДМИН КОМАНДЫ =============
ADMIN_IDS = [1355575267, ]  # ТОЛЬКО ВАШ ID

def is_admin(user_id):
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Админ панель - ТОЛЬКО ДЛЯ АДМИНОВ"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ <b>Доступ запрещен.</b> Эта команда только для администраторов.", parse_mode=ParseMode.HTML)
        return
    
    admin_text = """
🔐 <b>АДМИН ПАНЕЛЬ</b> <i>(только для вас)</i>

<b>Основные команды:</b>
/reset - Сбросить свой прогресс
/stats @username - Статистика любого пользователя
/users - Общая статистика пользователей
/top - Топ пользователей

<b>Управление:</b>
/add_admin ID - Добавить администратора
/remove_admin ID - Удалить администратора
/broadcast текст - Рассылка сообщения
"""
    
    await message.answer(admin_text, parse_mode=ParseMode.HTML)


@dp.message(Command("add_admin"))
async def cmd_add_admin(message: types.Message):
    """Добавить администратора - ТОЛЬКО ДЛЯ АДМИНОВ"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /add_admin ID_пользователя")
        return
    
    new_admin_id = int(args[1])
    
    # Проверяем, есть ли уже такой ID
    if new_admin_id in ADMIN_IDS:
        await message.answer(f"❌ Пользователь {new_admin_id} уже администратор.")
        return
    
    # Добавляем в список
    ADMIN_IDS.append(new_admin_id)
    
    # Сохраняем в файл (для постоянного хранения)
    try:
        with open('admin_ids.txt', 'a') as f:
            f.write(f"{new_admin_id}\n")
    except:
        pass
    
    await message.answer(f"✅ Пользователь {new_admin_id} добавлен в администраторы.")


@dp.message(Command("remove_admin"))
async def cmd_remove_admin(message: types.Message):
    """Удалить администратора - ТОЛЬКО ДЛЯ АДМИНОВ"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /remove_admin ID_пользователя")
        return
    
    admin_id = int(args[1])
    
    # Нельзя удалить себя
    if admin_id == message.from_user.id:
        await message.answer("❌ Нельзя удалить самого себя.")
        return
    
    # Удаляем из списка
    if admin_id in ADMIN_IDS:
        ADMIN_IDS.remove(admin_id)
        await message.answer(f"✅ Пользователь {admin_id} удален из администраторов.")
    else:
        await message.answer(f"❌ Пользователь {admin_id} не найден в списке администраторов.")


@dp.message(Command("admins"))
async def cmd_admins(message: types.Message):
    """Показать список администраторов - ТОЛЬКО ДЛЯ АДМИНОВ"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return
    
    admins_text = "👑 <b>СПИСОК АДМИНИСТРАТОРОВ</b>\n\n"
    
    for i, admin_id in enumerate(ADMIN_IDS, 1):
        try:
            user = await message.bot.get_chat(admin_id)
            name = user.first_name or user.username or str(admin_id)
            admins_text += f"{i}. {name} (ID: {admin_id})\n"
        except:
            admins_text += f"{i}. ID: {admin_id} (пользователь не найден)\n"
    
    admins_text += f"\n📊 Всего: {len(ADMIN_IDS)} администратор(ов)"
    
    await message.answer(admins_text, parse_mode=ParseMode.HTML)


# Загружаем сохраненные ID администраторов при запуске
def load_admin_ids():
    """Загрузка списка администраторов из файла"""
    try:
        with open('admin_ids.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    admin_id = int(line)
                    if admin_id not in ADMIN_IDS:
                        ADMIN_IDS.append(admin_id)
        print(f"✅ Загружено {len(ADMIN_IDS)} администраторов")
    except FileNotFoundError:
        # Создаем файл с текущим админом
        with open('admin_ids.txt', 'w') as f:
            f.write("1355575267\n")
        print("✅ Создан файл администраторов")
    except Exception as e:
        print(f"❌ Ошибка при загрузке администраторов: {e}")

# Вызовите эту функцию при запуске бота
# load_admin_ids()

# ============= ФУНКЦИИ ДЛЯ СТАТИСТИКИ =============

def get_user_detailed_stats(user_id):
    """Получение детальной статистики пользователя"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Основная статистика
        cursor.execute('''
            SELECT level, experience, lessons_completed, total_lessons, avg_score,
                   first_name, username, created_at
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            return {
                'short_stats': "🎮 <b>Начните изучение, чтобы получить первый уровень!</b>",
                'full_stats': "📊 У вас пока нет статистики. Начните с первого урока!"
            }
        
        level = int(user_data[0]) if user_data[0] else 1
        experience = user_data[1] if user_data[1] else 0
        lessons_completed = user_data[2] if user_data[2] else 0
        total_lessons = user_data[3] if user_data[3] else 5
        avg_score = user_data[4] if user_data[4] else 0
        
        # Рассчитываем прогресс до следующего уровня
        current_exp_in_level = experience % 100
        if current_exp_in_level == 0 and experience > 0:
            current_exp_in_level = 100
        
        exp_to_next = 100 - current_exp_in_level
        progress_percent = current_exp_in_level
        
        # Прогресс-бар
        filled = min(int(progress_percent / 10), 10)
        progress_bar = "█" * filled + "░" * (10 - filled)
        
        # Проверяем пройденные уроки
        cursor.execute('''
            SELECT lesson_number FROM lesson_progress 
            WHERE user_id = ? AND completed = TRUE
            ORDER BY lesson_number
        ''', (user_id,))
        
        completed_lessons = [row[0] for row in cursor.fetchall()]
        
        # Результаты тестов
        cursor.execute('''
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM quiz_results 
            WHERE user_id = ?
        ''', (user_id,))
        
        test_data = cursor.fetchone()
        total_questions = test_data[0] if test_data[0] else 0
        correct_answers = test_data[1] if test_data[1] else 0
        test_score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Достижения
        achievements = []
        if lessons_completed >= 1:
            achievements.append("🎯 Новичок")
        if lessons_completed >= 3:
            achievements.append("🎓 Специалист")
        if lessons_completed >= 5:
            achievements.append("🏆 Эксперт")
        if experience >= 300:
            achievements.append("⭐ Опытный")
        if experience >= 500:
            achievements.append("👑 Мастер")
        if test_score >= 80 and total_questions >= 5:
            achievements.append("🧠 Тестировщик")
        
        # Короткая статистика (для /start)
        short_stats = f"""
🏅 <b>Ваш уровень:</b> {level}
⭐ <b>Опыт:</b> {experience}
📚 <b>Пройдено уроков:</b> {lessons_completed}/{total_lessons}
🎯 <b>Тесты:</b> {test_score:.0f}% ({correct_answers}/{total_questions})
"""
        
        # Полная статистика
        full_stats = f"""
📊 <b>ПОДРОБНАЯ СТАТИСТИКА</b>

👤 <b>Исследователь:</b> {user_data[5]}
🔗 <b>Username:</b> @{user_data[6] or 'отсутствует'}
📅 <b>Регистрация:</b> {user_data[7].split()[0] if user_data[7] else 'неизвестно'}

📈 <b>Основные показатели:</b>
🏅 Уровень: {level}
⭐ Опыт: {experience}
📚 Уроки: {lessons_completed}/{total_lessons}
🎯 Средний балл: {avg_score:.1f}
🧠 Тесты: {test_score:.1f}%

📊 <b>Прогресс до уровня {level + 1}:</b>
{progress_bar} {progress_percent}%
⏳ Осталось опыта: {exp_to_next}

📚 <b>Пройденные уроки:</b>
1️⃣ Основы - {'✅' if 1 in completed_lessons else '❌'}
2️⃣ Пароли - {'✅' if 2 in completed_lessons else '❌'}
3️⃣ Фишинг - {'✅' if 3 in completed_lessons else '❌'}
4️⃣ Шифрование - {'✅' if 4 in completed_lessons else '❌'}
5️⃣ Сети - {'✅' if 5 in completed_lessons else '❌'}

🏆 <b>Достижения:</b> {', '.join(achievements) if achievements else 'пока нет'}

💡 <b>Совет:</b> Пройдите все уроки и тесты для максимального опыта!
"""
        
        return {
            'short_stats': short_stats,
            'full_stats': full_stats,
            'level': level,
            'experience': experience,
            'lessons_completed': lessons_completed,
            'test_score': test_score
        }
        
    except Exception as e:
        print(f"❌ Ошибка при получении статистики: {e}")
        return {
            'short_stats': "🎮 <b>Начните изучение, чтобы получить первый уровень!</b>",
            'full_stats': "❌ Ошибка при загрузке статистики."
        }
    finally:
        conn.close()

def get_achievements_list(user_id):
    """Получение списка достижений пользователя"""
    stats = get_user_detailed_stats(user_id)
    achievements = []
    
    if stats['lessons_completed'] >= 1:
        achievements.append(("🎯 Новичок", "Пройдите первый урок", "✅" if stats['lessons_completed'] >= 1 else "❌"))
    if stats['lessons_completed'] >= 3:
        achievements.append(("🎓 Специалист", "Пройдите 3 урока", "✅" if stats['lessons_completed'] >= 3 else "❌"))
    if stats['lessons_completed'] >= 5:
        achievements.append(("🏆 Эксперт", "Пройдите все 5 уроков", "✅" if stats['lessons_completed'] >= 5 else "❌"))
    if stats['experience'] >= 300:
        achievements.append(("⭐ Опытный", "Наберите 300 опыта", "✅" if stats['experience'] >= 300 else "❌"))
    if stats['experience'] >= 500:
        achievements.append(("👑 Мастер", "Наберите 500 опыта", "✅" if stats['experience'] >= 500 else "❌"))
    if stats['test_score'] >= 80:
        achievements.append(("🧠 Тестировщик", "Пройдите тесты на 80%+", "✅" if stats['test_score'] >= 80 else "❌"))
    
    return achievements

def get_user_daily_stats(user_id):
    """Получение ежедневной статистики пользователя"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Сегодняшняя дата
        today = datetime.now().date()
        
        # Проверяем, получал ли пользователь сегодняшнюю награду
        cursor.execute('''
            SELECT last_daily_reward FROM users WHERE user_id = ?
        ''', (user_id,))
        
        last_reward_date = cursor.fetchone()
        
        # Считаем дни подряд
        cursor.execute('''
            SELECT consecutive_days FROM users WHERE user_id = ?
        ''', (user_id,))
        
        consecutive_days = cursor.fetchone()
        consecutive_days = consecutive_days[0] if consecutive_days else 0
        
        # Проверяем, получал ли награду сегодня
        got_today = False
        if last_reward_date and last_reward_date[0]:
            last_date = datetime.strptime(last_reward_date[0].split()[0], "%Y-%m-%d").date()
            got_today = last_date == today
        
        # Награда за текущий день
        if consecutive_days >= 7:
            daily_reward = 100
            day_text = "7+ (максимум)"
        else:
            daily_reward = (consecutive_days + 1) * 10
            day_text = consecutive_days + 1
        
        return {
            'got_today': got_today,
            'consecutive_days': consecutive_days,
            'daily_reward': daily_reward,
            'next_day': day_text
        }
        
    except Exception as e:
        print(f"❌ Ошибка при получении ежедневной статистики: {e}")
        return {
            'got_today': False,
            'consecutive_days': 0,
            'daily_reward': 10,
            'next_day': 1
        }
    finally:
        conn.close()

def update_daily_reward(user_id):
    """Обновление ежедневной награды пользователя"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Сегодняшняя дата
        today = datetime.now().date()
        today_str = today.strftime("%Y-%m-%d %H:%M:%S")
        
        # Получаем текущие данные
        cursor.execute('''
            SELECT last_daily_reward, consecutive_days FROM users WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        
        if result:
            last_reward_date = result[0]
            consecutive_days = result[1] if result[1] else 0
            
            # Проверяем дату последней награды
            if last_reward_date:
                last_date = datetime.strptime(last_reward_date.split()[0], "%Y-%m-%d").date()
                
                # Если получили вчера - увеличиваем счетчик
                if last_date == today - timedelta(days=1):
                    consecutive_days += 1
                # Если пропустили день - сбрасываем
                elif last_date < today - timedelta(days=1):
                    consecutive_days = 1
                # Если уже получили сегодня - ничего не делаем
                else:
                    return None
            else:
                # Первый раз
                consecutive_days = 1
            
            # Рассчитываем награду
            if consecutive_days >= 7:
                reward = 100
            else:
                reward = consecutive_days * 10
            
            # Обновляем данные
            cursor.execute('''
                UPDATE users 
                SET last_daily_reward = ?, 
                    consecutive_days = ?,
                    experience = experience + ?
                WHERE user_id = ?
            ''', (today_str, consecutive_days, reward, user_id))
            
            conn.commit()
            return reward
        
        return None
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении ежедневной награды: {e}")
        return None
    finally:
        conn.close()


def get_achievements_list(user_id):
    """Получение списка достижений пользователя"""
    stats = get_user_detailed_stats(user_id)
    achievements = []
    
    if stats['lessons_completed'] >= 1:
        achievements.append(("🎯 Новичок", "Пройдите первый урок", "✅" if stats['lessons_completed'] >= 1 else "❌"))
    if stats['lessons_completed'] >= 3:
        achievements.append(("🎓 Специалист", "Пройдите 3 урока", "✅" if stats['lessons_completed'] >= 3 else "❌"))
    if stats['lessons_completed'] >= 5:
        achievements.append(("🏆 Эксперт", "Пройдите все 5 уроков", "✅" if stats['lessons_completed'] >= 5 else "❌"))
    if stats['experience'] >= 300:
        achievements.append(("⭐ Опытный", "Наберите 300 опыта", "✅" if stats['experience'] >= 300 else "❌"))
    if stats['experience'] >= 500:
        achievements.append(("👑 Мастер", "Наберите 500 опыта", "✅" if stats['experience'] >= 500 else "❌"))
    if stats['test_score'] >= 80:
        achievements.append(("🧠 Тестировщик", "Пройдите тесты на 80%+", "✅" if stats['test_score'] >= 80 else "❌"))
    
    return achievements



@dp.message(F.text == "📊 Статистика")
async def show_statistics(message: types.Message):
    """Показываем подробную статистику"""
    stats = get_user_detailed_stats(message.from_user.id)
    await message.answer(stats['full_stats'], parse_mode=ParseMode.HTML)

@dp.message(F.text == "🏆 Прогресс")
async def show_progress(message: types.Message):
    """Показываем прогресс пользователя"""
    user_id = message.from_user.id
    stats = get_user_detailed_stats(user_id)
    
    # Дополнительная информация о прогрессе
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Дата последнего урока
        cursor.execute('''
            SELECT MAX(completed_at) FROM lesson_progress 
            WHERE user_id = ? AND completed = TRUE
        ''', (user_id,))
        last_lesson = cursor.fetchone()[0]
        
        # Лучший результат в тестах
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM quiz_results 
            WHERE user_id = ?
            GROUP BY question_id
            ORDER BY correct DESC
            LIMIT 1
        ''', (user_id,))
        
        best_test = cursor.fetchone()
        best_score = (best_test[1] / best_test[0] * 100) if best_test and best_test[0] > 0 else 0
        
        progress_text = f"""
📈 <b>ВАШ ПРОГРЕСС</b>

{stats['full_stats'].split('💡')[0]}  # Берем основную статистику без совета

📅 <b>Активность:</b>
Последний урок: {last_lesson.split()[0] if last_lesson else 'еще не пройдено'}
Лучший тест: {best_score:.0f}%

🎯 <b>Ближайшие цели:</b>
"""
        
        # Рекомендации
        if stats['lessons_completed'] < 5:
            progress_text += f"• Пройти урок {stats['lessons_completed'] + 1} (+{10 + stats['lessons_completed']*5} опыта)\n"
        
        if stats['experience'] < 500:
            needed = 500 - stats['experience']
            progress_text += f"• Набрать 500 опыта ({needed} осталось)\n"
        
        if stats['test_score'] < 80:
            progress_text += f"• Улучшить результат тестов до 80%+\n"
        
        progress_text += "\n💪 <i>Каждый день по чуть-чуть - и вы станете экспертом!</i>"
        
    except Exception as e:
        print(f"Ошибка при получении прогресса: {e}")
        progress_text = stats['full_stats']
    finally:
        conn.close()
    
    await message.answer(progress_text, parse_mode=ParseMode.HTML)


@dp.message(Command("mystats"))
async def cmd_mystats(message: types.Message):
    """Показать мою статистику"""
    stats = get_user_detailed_stats(message.from_user.id)
    await message.answer(stats['full_stats'], parse_mode=ParseMode.HTML)

    

@dp.message(F.text == "📚 Уроки")
async def show_lessons_menu(message: types.Message):
    """Показываем меню уроков"""
    lessons_text = """
📚 <b>КАТАЛОГ УРОКОВ</b>

Выберите урок для изучения:

1️⃣ <b>Основы кибербезопасности</b>
   • Введение в тему
   • Основные понятия и угрозы

2️⃣ <b>Создание надежных паролей</b>
   • Правила создания паролей
   • Менеджеры паролей

3️⃣ <b>Фишинг-атаки</b>
   • Распознавание мошенничества
   • Защита от фишинга

4️⃣ <b>Основы шифрования</b>
   • Что такое шифрование
   • Типы шифрования

5️⃣ <b>Безопасность в сетях</b>
   • Защита Wi-Fi
   • VPN и прокси
    """
    await message.answer(lessons_text, parse_mode=ParseMode.HTML, reply_markup=get_lessons_keyboard())

@dp.message(F.text == "🔙 Назад")
async def back_to_main(message: types.Message):
    """Возврат в главное меню"""
    await message.answer("🔙 Возвращаемся в главное меню", reply_markup=get_main_keyboard())

# ============= ОБРАБОТЧИКИ УРОКОВ =============

lessons_data = {
    1: {
        "title": "Основы кибербезопасности",
        "content": """
📚 <b>Урок 1: Введение в кибербезопасность</b>

<b>Кибербезопасность</b> — это практика защиты систем, сетей и программ от цифровых атак.

<b>Три основных принципа (CIA):</b>
1. 🔒 <b>Конфиденциальность</b> — защита информации от несанкционированного доступа
2. ✅ <b>Целостность</b> — обеспечение точности и полноты данных
3. ⚡ <b>Доступность</b> — гарантия доступа к информации авторизованным пользователям

<b>Основные угрозы:</b>
• 🦠 Вирусы и вредоносное ПО
• 🎣 Фишинг-атаки
• ⚡ DDoS-атаки
• 📤 Утечки данных
• 👥 Социальная инженерия

<b>Статистика:</b>
• 90% кибератак начинаются с фишинга
• Каждые 39 секунд происходит хакерская атака
• Ущерб от киберпреступности к 2025 году достигнет $10.5 трлн

🎯 <i>Запомните: безопасность начинается с осознанности каждого пользователя!</i>
        """,
        "experience": 10
    },
    2: {
        "title": "Создание надежных паролей",
        "content": """
📚 <b>Урок 2: Искусство создания паролей</b>

<b>Хороший пароль должен:</b>
1. Быть не менее 12 символов
2. Содержать заглавные и строчные буквы
3. Включать цифры и специальные символы (!@#$%^&*)
4. Не содержать личную информацию (имя, дату рождения)
5. Быть уникальным для каждого сервиса

<b>Примеры плохих паролей:</b>
• 123456 (самый популярный пароль)
• password / qwerty
• имя + год рождения
• последовательности клавиш (qwerty123)

<b>Как создать надежный пароль:</b>
1. <b>Метод фразы:</b> "ЯЛюблюКибербезопасность2024!" → "ЯЛюблюКиберБезопасность2024!"
2. <b>Акроним:</b> "Каждый Охотник Желает Знать..." → "K0jZnGfS2024!"
3. <b>Генератор паролей:</b> xkcd-метод (четыре случайных слова)

<b>Менеджеры паролей:</b>
• 🔒 Bitwarden (бесплатный, с открытым кодом)
• 🛡️ KeePass (локальное хранение)
• 🍎 iCloud Keychain (для Apple-устройств)
• 🌐 LastPass (популярный, но платный)

<b>Двухфакторная аутентификация (2FA):</b>
Всегда включайте 2FA где это возможно!
• Google Authenticator
• Microsoft Authenticator
• Authy

🎯 <i>Совет: Используйте менеджер паролей и включайте 2FA везде!</i>
        """,
        "experience": 15
    },
    3: {
        "title": "Фишинг-атаки",
        "content": """
📚 <b>Урок 3: Фишинг - охота за вашими данными</b>

<b>Что такое фишинг?</b>
Фишинг — вид мошенничества с целью получения конфиденциальной информации (логины, пароли, данные карт).

<b>Типы фишинга:</b>
1. <b>Электронный фишинг</b> — массовая рассылка писем
2. <b>Спифинг</b> — подделка отправителя
3. <b>Виджинг</b> — голосовой фишинг
4. <b>Смишинг</b> — SMS-фишинг
5. <b>Китобойный</b> — целенаправленная атака на конкретного человека

<b>Признаки фишингового письма:</b>
1. 🔴 Срочность ("Аккаунт будет заблокирован через 24 часа!")
2. 🚫 Незнакомый отправитель
3. ✏️ Ошибки в письме (орфография, грамматика)
4. 🔗 Подозрительные ссылки (не совпадают с текстом)
5. 📎 Неожиданные вложения
6. 👤 Запрос личной информации

<b>Реальный пример фишинга:</b>
"Уважаемый клиент Сбербанка,
Зафиксирована подозрительная активность в вашем аккаунте.
Для проверки перейдите по ссылку: http://sberbank-security.ru/login
Если не сделаете этого в течение 2 часов, аккаунт будет заблокирован.

С уважением, Служба безопасности"

<b>Как защититься:</b>
1. Проверяйте отправителя (полный email, не только имя)
2. Наводите курсор на ссылку (не кликайте!)
3. Вводите адреса сайтов вручную
4. Используйте антифишинговые расширения
5. Включайте 2FA

<b>Что делать если попались:</b>
1. Немедленно смените пароль
2. Проверьте историю входов
3. Сообщите в службу поддержки
4. Если ввели данные карты — заблокируйте её

🎯 <i>Помните: банки никогда не просят пароли и данные карт по email!</i>
        """,
        "experience": 20
    },
    4: {
        "title": "Основы шифрования",
        "content": """
📚 <b>Урок 4: Шифрование - язык секретов</b>

<b>Что такое шифрование?</b>
Шифрование — процесс преобразования информации в нечитаемый вид для защиты от несанкционированного доступа.

<b>Типы шифрования:</b>
1. <b>Симметричное шифрование</b> — один ключ для шифрования и расшифровки
   • AES (Advanced Encryption Standard)
   • DES (Data Encryption Standard)
   • Используется для шифрования файлов

2. <b>Асимметричное шифрование</b> — пара ключей (публичный и приватный)
   • RSA (Rivest-Shamir-Adleman)
   • ECC (Elliptic Curve Cryptography)
   • Используется в SSL/TLS, PGP

<b>Где применяется шифрование:</b>
• 🔐 HTTPS-соединения (браузер показывает замок)
• 📧 Зашифрованная почта (PGP, S/MIME)
• 💾 Шифрование дисков (BitLocker, FileVault)
• 📱 Мессенджеры (Signal, WhatsApp)
• 💳 Платежные системы

<b>Практические примеры:</b>
1. <b>Хэширование паролей</b> — необратимое преобразование
   • bcrypt, scrypt, Argon2
   • Соль (salt) для усиления защиты

2. <b>SSL/TLS сертификаты</b> — защита веб-соединений
   • Проверяйте наличие https://
   • Смотрите на значок замка

3. <b>VPN</b> — шифрование интернет-трафика
   • OpenVPN, WireGuard
   • Выбирайте VPN с no-logs политикой

<b>Квантовые компьютеры и шифрование:</b>
• Современная криптография уязвима перед квантовыми компьютерами
• Разрабатывается постквантовая криптография
• Уже сейчас нужно готовиться к переходу

🎯 <i>Совет: Всегда используйте HTTPS, шифруйте важные файлы и используйте VPN в публичных сетях!</i>
        """,
        "experience": 25
    },
    5: {
        "title": "Безопасность в сетях",
        "content": """
📚 <b>Урок 5: Безопасность в компьютерных сетях</b>

<b>Основные угрозы в сетях:</b>
1. <b>MITM-атаки</b> (Man-in-the-Middle) — перехват трафика
2. <b>Сниффинг</b> — анализ сетевого трафика
3. <b>Подмена ARP</b> — атаки в локальных сетях
4. <b>Wi-Fi взлом</b> — несанкционированный доступ

<b>Защита домашней сети Wi-Fi:</b>
1. 🔐 <b>Измените пароль по умолчанию</b> на роутере
2. 🛡️ <b>Включите WPA3</b> или WPA2 (никогда WEP!)
3. 📡 <b>Скрытие SSID</b> — не транслируйте имя сети
4. 🏠 <b>MAC-фильтрация</b> — только разрешенные устройства
5. 🔄 <b>Регулярное обновление</b> прошивки роутера

<b>VPN (Virtual Private Network):</b>
• Шифрует весь интернет-трафик
• Скрывает реальный IP-адрес
• Обходит географические ограничения

<b>Критерии выбора VPN:</b>
1. No-logs политика (не хранят логи)
2. Современные протоколы (WireGuard, OpenVPN)
3. Юрисдикция (не в странах 5/9/14 глаз)
4. Скорость и стабильность соединения
5. Количество серверов и стран

<b>Рекомендуемые VPN:</b>
• 🔒 ProtonVPN (Швейцария, no-logs)
• 🛡️ Mullvad (Швеция, анонимная регистрация)
• 🌐 IVPN (Гибралтар, прозрачная политика)

<b>Общественные Wi-Fi сети:</b>
• Никогда не вводите пароли без VPN
• Отключайте автоматическое подключение
• Используйте мобильный интернет для важных операций
• Включайте "файрвол" на устройстве

<b>Сетевые инструменты для проверки:</b>
1. Wireshark — анализ сетевого трафика
2. Nmap — сканирование сетей и портов
3. Aircrack-ng — проверка безопасности Wi-Fi
4. Metasploit — тестирование на проникновение

🎯 <i>Правило: Всегда используйте VPN в публичных сетях и обновляйте оборудование!</i>
        """,
        "experience": 30
    }
    
}

# Обработчики для уроков
lesson_buttons = {
    "1️⃣ Урок 1: Основы": 1,
    "2️⃣ Урок 2: Пароли": 2,
    "3️⃣ Урок 3: Фишинг": 3,
    "4️⃣ Урок 4: Шифрование": 4,
    "5️⃣ Урок 5: Сети": 5
}

@dp.message(F.text.in_(lesson_buttons.keys()))
async def show_lesson_detail(message: types.Message):
    """Показываем детали урока"""
    lesson_num = lesson_buttons[message.text]
    lesson = lessons_data[lesson_num]
    
    await message.answer(lesson["content"], parse_mode=ParseMode.HTML)
    
    # Сохраняем прогресс
    user = message.from_user
    score = lesson["experience"]
    try:
        db.update_user_progress(user.id, lesson_num, score)
        
        # Поздравляем с завершением
        await message.answer(
            f"✅ <b>Урок завершен!</b>\n"
            f"🎓 Тема: {lesson['title']}\n"
            f"⭐ Получено опыта: {score}\n",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"❌ Ошибка при сохранении прогресса: {e}")
        await message.answer(
            f"✅ <b>Урок завершен!</b>\n"
            f"🎓 Тема: {lesson['title']}\n"
            f"⭐ Получено опыта: {score}\n",
            parse_mode=ParseMode.HTML
        )

# ============= ТЕСТЫ И КВИЗЫ =============

@dp.message(F.text == "🎯 Тесты")
async def show_tests_menu(message: types.Message):
    """Меню тестов"""
    await message.answer(
        "📝 <b>ТЕСТЫ ПО КИБЕРБЕЗОПАСНОСТИ</b>\n\n"
        "Проверьте свои знания после прохождения уроков!\n"
        "Каждый тест состоит из 5 вопросов.\n"
        "За правильный ответ: +10 опыта\n"
        "За прохождение теста: +50 опыта",
        parse_mode=ParseMode.HTML,
        reply_markup=get_tests_keyboard()
    )



# Хранилище результатов
user_test_progress = {}

@dp.callback_query(F.data.startswith("quiz_"))
async def process_quiz_answer(callback: types.CallbackQuery):
    data = callback.data.split("_")
    question_num = int(data[1])
    answer_num = int(data[2])

    user_id = callback.from_user.id
    test_num = 1 if question_num <= 5 else 2

    # Инициализация прогресса
    if user_id not in user_test_progress:
        user_test_progress[user_id] = {
            "correct": 0,
            "test": test_num
        }

    correct_answer = quiz_questions[test_num][question_num]["correct"]

    # Проверка ответа
    if answer_num == correct_answer:
        user_test_progress[user_id]["correct"] += 1
        await callback.answer("✅ Правильно!")
        is_correct = True
    else:
        await callback.answer("❌ Неправильно")
        is_correct = False

    # 🔥 УДАЛЯЕМ СТАРЫЙ ВОПРОС
    try:
        await callback.message.delete()
    except:
        pass

    # ЕСЛИ ПОСЛЕДНИЙ ВОПРОС
    if question_num == 5:
        total = 5
        correct = user_test_progress[user_id]["correct"]

        if correct == total:
            result_text = (
                "🏆 <b>Идеально!</b>\n\n"
                "✅ Все ответы правильные!\n"
                "🔥 Ты отлично разбираешься в теме!"
            )
        elif correct >= 3:
            result_text = (
                "⚠️ <b>Тест пройден</b>\n\n"
                f"✅ Правильных ответов: {correct} из {total}\n"
                "💪 Можно ещё лучше!"
            )
        else:
            result_text = (
                "❌ <b>Тест не пройден</b>\n\n"
                f"Правильных ответов: {correct} из {total}\n"
                "📚 Рекомендуем повторить урок"
            )

        await callback.message.answer(
            result_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_tests_keyboard()
        )

        del user_test_progress[user_id]
        return

    # ➡️ СЛЕДУЮЩИЙ ВОПРОС
    await send_quiz_question(
        callback.message,
        test_num=test_num,
        question_num=question_num + 1
    )


@dp.message(F.text == "📝 Тест 1: Основы")
async def start_test1(message: types.Message):
    """Начинаем тест 1"""
    await send_quiz_question(message, test_num=1, question_num=1)

@dp.message(F.text == "📝 Тест 2: Безопасность")
async def start_test2(message: types.Message):
    """Начинаем тест 2"""
    await send_quiz_question(message, test_num=2, question_num=1)

@dp.message(F.text == "📊 Результаты тестов")
async def show_my_results(message: types.Message):
    """Показываем результаты тестов пользователя"""
    stats = get_user_detailed_stats(message.from_user.id)
    
    await message.answer(
        f"📊 <b>ВАШИ РЕЗУЛЬТАТЫ ТЕСТОВ</b>\n\n"
        f"🎯 <b>Общий результат:</b> {stats['test_score']:.1f}%\n\n"
        f"📝 <b>Тест 1: Основы</b>\n"
        f"   • Пройден: {'✅' if stats['test_score'] > 0 else '❌'}\n"
        f"   • Результат: {stats['test_score']:.1f}%\n\n"
        f"📝 <b>Тест 2: Безопасность</b>\n"
        f"   • Пройден: {'✅' if stats['test_score'] > 0 else '❌'}\n"
        f"   • Результат: {stats['test_score']:.1f}%\n\n"
        f"💡 <b>Совет:</b> Пройдите тесты несколько раз для улучшения результата!",
        parse_mode=ParseMode.HTML
    )

# Вопросы для тестов
quiz_questions = {
    1: {
        1: {
            "question": "Что такое фишинг?",
            "options": [
                "А) Вид рыбалки",
                "Б) Метод социальной инженерии для получения данных",
                "В) Тип компьютерного вируса",
                "Г) Способ шифрования данных"
            ],
            "correct": 2
        },
        2: {
            "question": "Какой минимальной длины должен быть надежный пароль?",
            "options": [
                "А) 6 символов",
                "Б) 8 символов",
                "В) 12 символов",
                "Г) 16 символов"
            ],
            "correct": 2
        },
        3: {
            "question": "Что означает аббревиатура 2FA?",
            "options": [
                "А) Два фактора аутентификации",
                "Б) Два файла архива",
                "В) Два формата аудио",
                "Г) Два фактора анализа"
            ],
            "correct": 1
        },
        4: {
            "question": "Какой протокол НЕ безопасен для Wi-Fi?",
            "options": [
                "А) WPA2",
                "Б) WPA3",
                "В) WEP",
                "Г) WPA2-PSK"
            ],
            "correct": 3
        },
        5: {
            "question": "Что такое DDoS-атака?",
            "options": [
                "А) Распределенная атака на отказ в обслуживании",
                "Б) Вид компьютерного червя",
                "В) Метод шифрования данных",
                "Г) Тип антивирусной программы"
            ],
            "correct": 1
        }
    },
    2: {
        1: {
            "question": "Что такое MITM-атака?",
            "options": [
                "А) Атака 'человек посередине'",
                "Б) Метод тестирования программ",
                "В) Вид фишинговой атаки",
                "Г) Способ резервного копирования"
            ],
            "correct": 1
        },
        2: {
            "question": "Для чего используется VPN?",
            "options": [
                "А) Для ускорения интернета",
                "Б) Для шифрования трафика и сокрытия IP",
                "В) Для блокировки рекламы",
                "Г) Для создания локальной сети"
            ],
            "correct": 2
        },
        3: {
            "question": "Что такое антивирусное ПО?",
            "options": [
                "А) Программа для ускорения компьютера",
                "Б) Программа для защиты от вредоносного ПО",
                "В) Программа для очистки диска",
                "Г) Программа для шифрования файлов"
            ],
            "correct": 2
        },
        4: {
            "question": "Как часто нужно обновлять ПО?",
            "options": [
                "А) Раз в год",
                "Б) Только когда перестает работать",
                "В) Как только выходят обновления",
                "Г) Никогда не обновлять"
            ],
            "correct": 3
        },
        5: {
            "question": "Что такое социальная инженерия?",
            "options": [
                "А) Наука об обществе",
                "Б) Метод манипуляции людьми для получения информации",
                "В) Тип компьютерной сети",
                "Г) Способ программирования"
            ],
            "correct": 2
        }
    }
}

async def send_quiz_question(message: types.Message, test_num: int, question_num: int):
    """Отправляем вопрос теста"""
    if test_num in quiz_questions and question_num in quiz_questions[test_num]:
        question_data = quiz_questions[test_num][question_num]
        question_text = f"📝 <b>Тест {test_num}, вопрос {question_num}/5</b>\n\n{question_data['question']}\n\n"
        
        for option in question_data["options"]:
            question_text += f"{option}\n"
        
        await message.answer(
            question_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_quiz_keyboard(question_num)
        )
    else:
        # Тест завершен
        await message.answer(
            f"🎉 <b>Тест {test_num} завершен!</b>\n\n"
            f"Вы ответили на все 5 вопросов.\n"
            f"Опыт начислен на ваш аккаунт!\n\n"
            f"🏆 Продолжайте обучение!",
            parse_mode=ParseMode.HTML,
            reply_markup=get_tests_keyboard()
        )

@dp.callback_query(F.data.startswith("quiz_"))
async def process_quiz_answer(callback: types.CallbackQuery):
    """Обработка ответа на вопрос теста"""
    data = callback.data.split("_")
    question_num = int(data[1])
    answer_num = int(data[2])
    test_num = 1 if "quiz_1" in callback.data else 2
    
    # Получаем правильный ответ
    correct_answer = quiz_questions[test_num][question_num]["correct"]
    
    # Проверяем ответ
    if answer_num == correct_answer:
        result_text = "✅ <b>Правильно!</b>"
        is_correct = True
    else:
        result_text = f"❌ <b>Неправильно!</b> Правильный ответ: {['А','Б','В','Г'][correct_answer-1]}"
        is_correct = False
    
    try:
        # Сохраняем результат в БД
        db.add_quiz_result(callback.from_user.id, test_num * 10 + question_num, answer_num, is_correct)
        
        # Увеличиваем опыт за правильный ответ
        if is_correct:
            db.update_user_progress(callback.from_user.id, 10 + question_num, 10)
    except Exception as e:
        print(f"❌ Ошибка при сохранении результата теста: {e}")
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n{result_text}",
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()
    
    # Отправляем следующий вопрос или завершаем тест
    if question_num < 5:
        await asyncio.sleep(1)  # Пауза перед следующим вопросом
        await send_quiz_question(callback.message, test_num, question_num + 1)
    else:
        try:
            # Начисляем опыт за завершение теста
            db.update_user_progress(callback.from_user.id, 20, 50)
        except:
            pass

# ============= СТАТИСТИКА И ЛИДЕРЫ =============

@dp.message(F.text == "📊 Статистика")
async def show_statistics(message: types.Message):
    """Показываем подробную статистику"""
    user = message.from_user
    
    try:
        stats = db.get_user_stats(user.id)
        
        if stats and stats[0]:
            level, experience, lessons_completed, total_lessons, avg_score = stats
            exp_to_next = 100 - (experience % 100)
            progress_percent = (experience % 100)
            
            # Создаем прогресс-бар
            progress_bar = "█" * int(progress_percent / 10) + "░" * (10 - int(progress_percent / 10))
            
            stats_text = f"""
📊 <b>ПОДРОБНАЯ СТАТИСТИКА</b>

👤 <b>Исследователь:</b> {user.first_name}
🏅 <b>Уровень:</b> {level}
⭐ <b>Опыт:</b> {experience}
📚 <b>Пройдено уроков:</b> {lessons_completed}
🎯 <b>Средний балл:</b> {avg_score:.1f if avg_score else 0}

📈 <b>Прогресс до уровня {level + 1}:</b>
{progress_bar} {progress_percent}%
⏳ <b>Осталось опыта:</b> {exp_to_next}

🏆 <b>Достижения:</b>
{'✅' if lessons_completed >= 1 else '❌'} Новичок (1 урок)
{'✅' if lessons_completed >= 3 else '❌'} Специалист (3 урока)
{'✅' if lessons_completed >= 5 else '❌'} Эксперт (5 уроков)
{'✅' if experience >= 500 else '❌'} Мастер (500 опыта)

💡 <b>Совет:</b> Пройдите все уроки и тесты для максимального опыта!
"""
        else:
            stats_text = "📊 У вас пока нет статистики. Начните с первого урока!"
    except Exception as e:
        print(f"❌ Ошибка при получении статистики: {e}")
        stats_text = "📊 У вас пока нет статистики. Начните с первого урока!"
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

@dp.message(F.text == "🥇 Лидеры")
async def show_leaderboard(message: types.Message):
    """Показываем таблицу лидеров"""
    try:
        leaders = db.get_leaderboard(limit=10)
        
        if not leaders:
            await message.answer("🏆 Таблица лидеров пока пуста. Будьте первым!")
            return
        
        leaderboard_text = "🏆 <b>ТОП-10 ИССЛЕДОВАТЕЛЕЙ КИБЕРБЕЗОПАСНОСТИ</b>\n\n"
        
        for i, (username, level, experience, lessons) in enumerate(leaders, 1):
            if username:
                name = f"@{username}"
            else:
                name = "Анонимный исследователь"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            leaderboard_text += f"{medal} {name}\n"
            leaderboard_text += f"   Уровень: {level} | ⭐ {experience} | 📚 {lessons}\n\n"
    except Exception as e:
        print(f"❌ Ошибка при получении таблицы лидеров: {e}")
        await message.answer("🏆 Таблица лидеров пока пуста. Будьте первым!")
        return
    
    # Проверяем позицию текущего пользователя
    user = message.from_user
    try:
        user_stats = db.get_user_stats(user.id)
        if user_stats and user_stats[0]:
            user_level, user_exp, user_lessons, _, _ = user_stats
            
            # Находим позицию пользователя
            user_position = None
            for i, (uname, _, exp, _) in enumerate(leaders, 1):
                if uname == user.username:
                    user_position = i
                    break
            
            if user_position:
                leaderboard_text += f"\n👤 <b>Ваша позиция:</b> {user_position} место"
            else:
                leaderboard_text += f"\n👤 <b>Ваш прогресс:</b> Уровень {user_level}, ⭐ {user_exp}"
    except:
        pass
    
    leaderboard_text += "\n\n🎯 <i>Пройдите больше уроков, чтобы подняться в рейтинге!</i>"
    
    await message.answer(leaderboard_text, parse_mode=ParseMode.HTML)


@dp.message(F.text == "🏆 Достижения")
async def show_achievements(message: types.Message):
    """Показываем достижения пользователя"""
    achievements = get_achievements_list(message.from_user.id)
    
    # Получаем общую статистику
    stats = get_user_detailed_stats(message.from_user.id)
    
    achievements_text = f"""
🏆 <b>ВАШИ ДОСТИЖЕНИЯ</b>

📊 <b>Ваш прогресс:</b>
🏅 Уровень: {stats['level']}
⭐ Опыт: {stats['experience']}
📚 Уроки: {stats['lessons_completed']}/5
🎯 Тесты: {stats['test_score']:.0f}%

━━━━━━━━━━━━━━━━━━━━

<b>Достижения:</b>
"""
    
    completed = 0
    for i, (name, desc, status) in enumerate(achievements, 1):
        achievements_text += f"\n{status} <b>{name}</b>\n"
        achievements_text += f"   <i>{desc}</i>\n"
        if status == "✅":
            completed += 1
    
    total_achievements = len(achievements)
    progress = int(completed / total_achievements * 100)
    
    achievements_text += f"\n━━━━━━━━━━━━━━━━━━━━\n"
    achievements_text += f"📊 <b>Прогресс:</b> {completed}/{total_achievements} ({progress}%)\n"
    
    if completed == total_achievements:
        achievements_text += "🎉 <b>Поздравляем! Вы получили все достижения!</b>"
    elif completed >= total_achievements // 2:
        achievements_text += "💪 <b>Хорошая работа! Продолжайте в том же духе!</b>"
    else:
        achievements_text += "🚀 <b>Продолжайте обучение, чтобы получить больше достижений!</b>"
    
    await message.answer(achievements_text, parse_mode=ParseMode.HTML)

@dp.message(F.text == "📅 Ежедневные задания")
async def show_daily_tasks(message: types.Message):
    """Показываем ежедневные задания"""
    user_id = message.from_user.id
    daily_stats = get_user_daily_stats(user_id)
    
    tasks_text = f"""
📅 <b>ЕЖЕДНЕВНЫЕ ЗАДАНИЯ И НАГРАДЫ</b>

🎁 <b>Ежедневная награда:</b>
День {daily_stats['next_day']}: +{daily_stats['daily_reward']} опыта
📅 Дней подряд: {daily_stats['consecutive_days']}

{'✅ <b>Награда сегодня уже получена!</b>' if daily_stats['got_today'] else '🎁 <b>Награда еще не получена сегодня</b>'}

━━━━━━━━━━━━━━━━━━━━

<b>Задания на сегодня:</b>

📚 <b>Обучение:</b>
✅ Пройти 1 урок (+10 опыта)
✅ Пройти тест (+50 опыта)
✅ Изучить 2 новые темы (+20 опыта)

🏆 <b>Достижения:</b>
✅ Достичь нового уровня (+30 опыта)
✅ Получить новое достижение (+40 опыта)
✅ Пройти урок на 100% (+25 опыта)

👥 <b>Социальные:</b>
✅ Проверить таблицу лидеров (+5 опыта)
✅ Поделиться с другом (+15 опыта)

━━━━━━━━━━━━━━━━━━━━

💡 <b>Как получить награду:</b>
1. Нажмите "🎁 Получить награду"
2. Выполняйте задания каждый день
3. Чем больше дней подряд, тем больше награда!
"""
    await message.answer(tasks_text, parse_mode=ParseMode.HTML, reply_markup=get_tasks_keyboard())

@dp.message(F.text == "✅ Отметить задание")
async def mark_task_complete(message: types.Message):
    """Отметить выполнение задания"""
    await message.answer(
        "✅ <b>Задание отмечено как выполненное!</b>\n\n"
        "Вы получите опыт после проверки заданий.\n"
        "Продолжайте в том же духе! 💪",
        parse_mode=ParseMode.HTML
    )

@dp.message(F.text == "📋 Мои задания")
async def show_my_tasks(message: types.Message):
    """Показать мои текущие задания"""
    stats = get_user_detailed_stats(message.from_user.id)
    daily_stats = get_user_daily_stats(message.from_user.id)
    
    tasks_text = f"""
📋 <b>МОИ ТЕКУЩИЕ ЗАДАНИЯ</b>

🎯 <b>Прогресс сегодня:</b>
📚 Уроки пройдено: {stats['lessons_completed']}/5
🎯 Тесты завершены: {stats['test_score']:.0f}%
🏆 Достижений получено: {len(stats.get('achievements', []))}

━━━━━━━━━━━━━━━━━━━━

<b>Активные задания:</b>

1. 📖 <b>Пройдите урок</b>
   • Прогресс: {stats['lessons_completed']}/5 уроков
   • Награда: +10 опыта за урок
   • Статус: {'✅ Выполнено' if stats['lessons_completed'] >= 5 else '⏳ В процессе'}

2. 🧠 <b>Пройдите тест</b>
   • Прогресс: {stats['test_score']:.0f}% правильных ответов
   • Награда: +50 опыта за тест
   • Статус: {'✅ Выполнено' if stats['test_score'] >= 80 else '⏳ В процессе'}

3. ⭐ <b>Наберите опыт</b>
   • Прогресс: {stats['experience']}/500 опыта
   • Награда: +100 опыта при достижении
   • Статус: {'✅ Выполнено' if stats['experience'] >= 500 else '⏳ В процессе'}

4. 📅 <b>Ежедневная активность</b>
   • Дней подряд: {daily_stats['consecutive_days']}
   • Награда сегодня: +{daily_stats['daily_reward']} опыта
   • Статус: {'✅ Получено' if daily_stats['got_today'] else '🎁 Доступно'}

━━━━━━━━━━━━━━━━━━━━

💡 <b>Совет:</b> Выполняйте задания каждый день для максимального прогресса!
"""
    await message.answer(tasks_text, parse_mode=ParseMode.HTML)

@dp.message(F.text == "🎁 Получить награду")
async def get_daily_reward(message: types.Message):
    """Получить ежедневную награду"""
    user_id = message.from_user.id
    daily_stats = get_user_daily_stats(user_id)
    
    if daily_stats['got_today']:
        await message.answer(
            "🎁 <b>Вы уже получили награду сегодня!</b>\n\n"
            f"Вы получили {daily_stats['daily_reward']} опыта.\n"
            f"Заходите завтра для получения следующей награды!\n\n"
            f"📅 Дней подряд: {daily_stats['consecutive_days']}",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Начисляем награду
    reward = update_daily_reward(user_id)
    
    if reward:
        new_stats = get_user_daily_stats(user_id)
        await message.answer(
            f"🎉 <b>Ежедневная награда получена!</b>\n\n"
            f"✅ Вы получили: +{reward} опыта\n"
            f"📅 Дней подряд: {new_stats['consecutive_days']}\n"
            f"🎁 Следующая награда: +{new_stats['daily_reward']} опыта\n\n"
            f"💪 Продолжайте в том же духе!",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            "❌ <b>Не удалось получить награду</b>\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            parse_mode=ParseMode.HTML
        )

@dp.message(F.text == "🎮 Задания")
async def show_tasks(message: types.Message):
    """Показываем ежедневные задания"""
    tasks_text = """
🎮 <b>ЕЖЕДНЕВНЫЕ ЗАДАНИЯ</b>

Выполняйте задания для получения дополнительного опыта!

📚 <b>Обучение:</b>
✅ Пройти 1 урок (+10 опыта)
✅ Пройти тест (+50 опыта)
✅ Изучить 3 темы за день (+30 опыта)

🏆 <b>Достижения:</b>
✅ Достичь 5 уровня (+100 опыта)
✅ Пройти все уроки (+200 опыта)
✅ Набрать 1000 опыта (+500 опыта)

👥 <b>Социальные:</b>
✅ Пригласить друга (+50 опыта)
✅ Делиться знаниями (+20 опыта)

⏰ <b>Ежедневная награда:</b>
Заходите каждый день для получения награды!
День 1: +10 опыта
День 2: +20 опыта
...
День 7: +100 опыта

💡 <b>Выполняйте задания и повышайте свой уровень!</b>
"""
    await message.answer(tasks_text, parse_mode=ParseMode.HTML)

# ============= ПОМОЩЬ И ИНФОРМАЦИЯ =============

@dp.message(F.text == "❓ Помощь")
async def show_help(message: types.Message):
    help_text = """
❓ <b>СПРАВКА ПО БОТУ</b>

<b>Основные команды:</b>
/start - Главное меню
/help - Эта справка

<b>Разделы бота:</b>
📚 <b>Уроки</b> - 5 уроков по кибербезопасности
🎯 <b>Тесты</b> - Проверка знаний (2 теста по 5 вопросов)
🏆 <b>Прогресс</b> - Ваша статистика и достижения
🥇 <b>Лидеры</b> - Топ-10 исследователей
📊 <b>Статистика</b> - Подробная информация о прогрессе
🎮 <b>Задания</b> - Ежедневные задания и достижения

<b>Система прогресса:</b>
• За каждый урок вы получаете опыт (10-30)
• За правильные ответы в тестах +10 опыта
• За завершение теста +50 опыта
• Каждые 100 опыта - новый уровень

<b>Для дипломной работы:</b>
• Бот создан на Python с использованием aiogram 3.0
• Используется база данных SQLite
• Реализована система мотивации (уровни, опыт)
• Добавлены интерактивные элементы

<b>Контакты:</b>
Разработчик: @Mr_Ismail4ik
GitHub: (https://github.com/IsmailhonSalaydinov/ismail4ikk.git)
Дипломная работа: Тема связана с кибербезопасностью
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@dp.message(F.text == "ℹ️ О боте")
async def about_bot(message: types.Message):
    about_text = """
ℹ️ <b>О ПРОЕКТЕ</b>

🤖 <b>КиберБезопасник Бот</b>
Версия: 2.0.0 (Образовательная)

<b>Цель проекта:</b>
Создание интерактивной образовательной платформы в формате Telegram-бота для обучения основам кибербезопасности.

<b>Образовательные задачи:</b>
1. Повышение цифровой грамотности пользователей
2. Обучение основам кибезопасности в доступной форме
3. Формирование практических навыков защиты данных
4. Создание мотивации через геймификацию

<b>Технологический стек:</b>
• Python 3.11 - основной язык программирования
• Aiogram 3.0 - фреймворк для Telegram ботов
• SQLite - база данных для хранения прогресса
• SQLAlchemy - ORM для работы с БД
• Asyncio - асинхронное программирование

<b>Функциональные возможности:</b>
✅ 5 образовательных модулей
✅ 2 интерактивных теста
✅ Система уровней и опыта
✅ Таблица лидеров
✅ Статистика прогресса
✅ Ежедневные задания

<b>Для дипломной работы:</b>
• Проект демонстрирует практическое применение Python
• Показывает навыки проектирования образовательных систем
• Включает элементы геймификации в обучении
• Имеет потенциал для дальнейшего развития

<b>Перспективы развития:</b>
• Добавление большего количества уроков
• Интеграция с внешними API (проверка паролей и т.д.)
• Мобильное приложение
• Веб-панель администратора
• Аналитика успеваемости

<b>Контакты:</b>
Автор: @Mr_Ismail4ik
Для обратной связи: используйте команду /help
"""
    await message.answer(about_text, parse_mode=ParseMode.HTML)

# ============= ЗАПУСК БОТА =============


async def main():
    """Основная функция запуска бота"""
    # Загружаем список администраторов
    load_admin_ids()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("🤖 БОТ ДЛЯ ИЗУЧЕНИЯ КИБЕРБЕЗОПАСНОСТИ v2.0")
    print("=" * 60)
    print("✅ Виртуальное окружение активировано")
    print(f"✅ Python версия: {os.sys.version}")
    print("=" * 60)
    print("🚀 Запуск бота...")
    print("📝 Проверка токена...")
    
    try:
        bot_info = await bot.get_me()
        print(f"✅ Бот найден: @{bot_info.username}")
        print(f"✅ Имя бота: {bot_info.first_name}")
        print("=" * 60)
        print("✅ Бот готов к работе!")
        print(f"✅ Ссылка на бота: https://t.me/{bot_info.username}")
        print("=" * 60)
        print("👑 Админ панель: /admin")
        print("📚 Доступно уроков: 5")
        print("🎯 Доступно тестов: 2")
        print("=" * 60)
        print("✅ Напишите /start для начала работы")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Ошибка при проверке токена: {e}")
        print("❌ Проверьте токен бота")
        return
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("👋 Бот остановлен пользователем")
        print("=" * 60)
