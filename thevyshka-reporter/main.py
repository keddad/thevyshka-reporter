from os import environ
import telebot
import logging
import sqlite3
from contextlib import closing

db_name = f"db.db"
all_contents = ['animation', 'audio', 'contact', 'dice', 'document', 'location', 'photo', 'poll', 'sticker', 'text',
                'venue', 'video', 'video_note', 'voice']

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

telebot.apihelper.ENABLE_MIDDLEWARE = True
logger = logging.getLogger(__name__)
bot = telebot.TeleBot(environ.get("BOT_TOKEN"))
admin_group_id = int(environ.get("ADMIN_CHAT"))


def ensure_migrations():
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS messages
                (from_id integer, message_id integer primary key, forwarded_id integer)
            """)
        conn.commit()


@bot.middleware_handler(update_types=["message"])
def register_message(bot_instance, message: telebot.types.Message):
    if message.text and message.text.startswith("/"):
        logging.debug(f"Skipped command from {message.chat.id}")
        return

    try:
        with sqlite3.connect(db_name) as conn:
            with closing(conn.cursor()) as c:
                c.execute("INSERT INTO messages VALUES (?, ?, ?)", (message.from_user.id, message.id, 0))
            conn.commit()
    except sqlite3.Error as e:
        logging.warning(f"{e} in middleware")


@bot.message_handler(commands=["start", "help"])
def start(message: telebot.types.Message):
    bot.send_message(message.chat.id, "Пиши, котик")


@bot.message_handler(func=lambda m: m.chat.id == admin_group_id, content_types=all_contents)
def respond_from_admin(message: telebot.types.Message):
    response_to = message.reply_to_message

    if not response_to:
        logging.debug(f"Not forwarding admin message from {message.from_user.id}")
        return

    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as c:
            c.execute("SELECT * FROM messages WHERE forwarded_id=?", (response_to.id,))
            db_res = c.fetchone()

    if not db_res:
        logging.warning(f"Unexpected None from database while fetching {response_to.id}")
        return

    bot.copy_message(db_res[0], admin_group_id, message.id, reply_to_message_id=db_res[1])


@bot.message_handler(func=lambda m: m.chat.id != admin_group_id, content_types=all_contents)
def forward_to_admin(message: telebot.types.Message):
    forwarded_message = bot.forward_message(admin_group_id, message.chat.id, message.id)
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as c:
            c.execute("""
                UPDATE messages SET forwarded_id=? WHERE message_id=?
            """, (forwarded_message.id, message.id))
        conn.commit()

    logger.debug(f"Forwarded {message.id} from {message.from_user.id}")


def main():
    ensure_migrations()
    bot.infinity_polling()


if __name__ == '__main__':
    main()
