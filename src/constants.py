"""Constants for the Taxi Bot."""

# Redis keys
REDIS_KEY_BALANCE = 'balance'
REDIS_KEY_TRIPS = 'trips'
REDIS_KEY_USERS = 'users'
REDIS_KEY_TIMESTAMP = 'timestamp'

# UI Messages (Russian)
MSG_WELCOME = "Добро пожаловать в бот для отслеживания поездок"
MSG_COMMAND_NOT_FOUND = "Команда не найдена"
MSG_LOGS_DISABLED = "Логи отключены"
MSG_NO_USERS = "Нет пользователей"

# Private bot messages
MSG_PRIVATE_BOT = "🔒 Это приватный бот.\n\nЧтобы продолжить, введите кодовое слово:"
MSG_SECRET_CODE_ACCEPTED = "✅ Кодовое слово принято! Добро пожаловать!"
MSG_SECRET_CODE_INVALID = ""  # Empty - no response for invalid code

# Button labels
BTN_CHECK_BALANCE = "Проверить баланс"
BTN_LOGS = "Логи"
BTN_USERS = "Пользователи"

# Inline button labels
BTN_USER_LOGS = "📝 Логи"
BTN_USER_DELETE = "🗑️ Удалить"
BTN_BACK_TO_USERS = "⬅️ Назад к пользователям"

# Admin commands
CMD_DELETE_USER = "/delete"
CMD_USER_LOGS = "/logs"

# Messages
MSG_USER_DELETED = "Пользователь {user_id} удален"
MSG_USER_NOT_FOUND = "Пользователь {user_id} не найден"
MSG_INVALID_USER_ID = "Неверный формат ID пользователя"
MSG_DELETE_USAGE = "Использование: /delete {user_id}"
MSG_CANNOT_DELETE_SELF = "Нельзя удалить самого себя"

# Log search messages
MSG_USER_LOGS_HEADER = "Логи для пользователя {user_id}:"
MSG_USER_LOGS_NOT_FOUND = "Логи для пользователя {user_id} не найдены"
MSG_USER_LOGS_USAGE = "Использование: /logs {user_id}"
MSG_LOGS_FILE_ERROR = "Ошибка чтения файла логов"
MSG_NO_LOGS_FOR_USER = "Нет логов для пользователя {user_id}"

# User management messages
MSG_USER_ACTIONS = "👤 Пользователь {user_id}\n\nВыберите действие:"
MSG_USER_DELETED_INLINE = "✅ Пользователь {user_id} удален"
MSG_USER_NOT_FOUND_INLINE = "❌ Пользователь {user_id} не найден"
MSG_CANNOT_DELETE_SELF_INLINE = "❌ Нельзя удалить самого себя"
MSG_USERS_LIST_HEADER = "👥 Список пользователей:\n\n"

# Trip display settings
RECENT_TRIPS_COUNT = 3
LOG_LINES_TO_SHOW = 20

# Trip message templates
TRIP_TEMPLATE = """<blockquote><b>{index}. {time}</b>
👤 <b>{name}</b> ({phone})
📍 {from_address}
🏁 {to_address}
📏 {distance} км • ⏱ {waiting} мин
💵 <b>{price} р.</b></blockquote>"""

NO_TRIPS_TEMPLATE = "<i>Пока поездок нет.</i>"

BALANCE_TEMPLATE = "<b>💰 Баланс:</b> {balance} р.\n\n<b>🚕 Последние поездки:</b>\n\n{trips}"

