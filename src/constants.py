"""User-facing texts, templates and tuning knobs."""

# --- limits ----------------------------------------------------------------

TELEGRAM_MESSAGE_LIMIT = 4096
RECENT_TRIPS_COUNT = 3
LOG_LINES_TO_SHOW = 20
USER_LOG_LINES_TO_SHOW = 30

# --- reply keyboard buttons ------------------------------------------------

BTN_CHECK_BALANCE = "Проверить баланс"
BTN_LOGS = "Логи"
BTN_USERS = "Пользователи"

# --- inline buttons --------------------------------------------------------

BTN_USER_LOGS = "📝 Логи"
BTN_USER_DELETE = "🗑️ Удалить"
BTN_BACK_TO_USERS = "⬅️ Назад к пользователям"

# --- general messages ------------------------------------------------------

MSG_WELCOME = "Добро пожаловать в бот для отслеживания поездок"
MSG_COMMAND_NOT_FOUND = "Команда не найдена"
MSG_ACCESS_DENIED = "Доступ запрещен"
MSG_STALE_BUTTON = "Кнопка устарела, откройте список пользователей заново"
MSG_INTERNAL_ERROR = "Произошла ошибка, попробуйте позже"
MSG_TRUNCATED = "\n\n... (сообщение обрезано)"

# --- private mode ----------------------------------------------------------

MSG_PRIVATE_BOT = "🔒 Это приватный бот.\n\nЧтобы продолжить, введите кодовое слово:"
MSG_SECRET_CODE_ACCEPTED = "✅ Кодовое слово принято! Добро пожаловать!"

# --- logs ------------------------------------------------------------------

MSG_LOGS_DISABLED = "Логи отключены"
MSG_LOGS_FILE_ERROR = "Ошибка чтения файла логов"
MSG_LOGS_EMPTY = "Лог пуст"
MSG_NO_LOGS_FOR_USER = "Нет логов для пользователя {user_id}"
MSG_USER_LOGS_USAGE = "Использование: /logs {user_id}"

USER_LOGS_TEMPLATE = """Логи для пользователя {user_id}:

📊 Статистика: {total} записей
• Запусков бота: {starts}
• Проверок баланса: {balance_checks}
• Просмотров логов: {log_views}
• Просмотров пользователей: {user_views}
• Неизвестных команд: {unknown_commands}

🕐 Последняя активность:
{last_entry}

📝 Последние логи:
{lines}"""

# --- user management -------------------------------------------------------

MSG_NO_USERS = "Нет пользователей"
MSG_USERS_LIST = "👥 Список пользователей:\n\nНажмите на пользователя для управления:"
MSG_USER_ACTIONS = "👤 Пользователь {user_id}\n\nВыберите действие:"
MSG_USER_DELETED = "✅ Пользователь {user_id} удален"
MSG_USER_NOT_FOUND = "❌ Пользователь {user_id} не найден"
MSG_CANNOT_DELETE_SELF = "❌ Нельзя удалить самого себя"
MSG_INVALID_USER_ID = "Неверный формат ID пользователя"
MSG_DELETE_USAGE = "Использование: /delete {user_id}"

# --- balance rendering (HTML) ---------------------------------------------

TRIP_TEMPLATE = """<blockquote><b>{index}. {time}</b>
👤 <b>{name}</b> ({phone})
📍 {from_address}
🏁 {to_address}
📏 {distance} км • ⏱ {waiting} мин
💵 <b>{price} р.</b></blockquote>"""

NO_TRIPS_TEMPLATE = "<i>Пока поездок нет.</i>"

BALANCE_TEMPLATE = "<b>💰 Баланс:</b> {balance} р.\n\n<b>🚕 Последние поездки:</b>\n\n{trips}"

LAST_UPDATE_TEMPLATE = "\n\n<i>Последнее обновление: {time}</i>"
