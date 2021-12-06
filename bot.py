import logging
import os
import psycopg2
import random

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

PORT = int(os.environ.get('PORT', '8440'))
TOKEN = os.environ["TOKEN"]

DATABASE_URL = os.environ['DATABASE_URL']

conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

mc_id = -743252633

WISHLIST, NAME, SHUFFLE, CONFIRMATION, UPDATE_WISHLIST = range(5)
# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error


def start(update, context):
    """Send a message when the command /start is issued"""
    update.message.reply_text('Хаю-хай!!')


def list(update: Update, context: CallbackContext) -> int:
    
    reply = []
    try:
        cur.execute(f"SELECT username, name FROM main;")
        participants = cur.fetchall()
        for i in range(len(participants)):
            reply.append(f"{str(i+1)}. @{participants[i][0]} ({participants[i][1]})")
        update.message.reply_text('\n'.join(reply))
    except Exception:
        update.message.reply_text('Ошибка...')


def delete_me(update: Update, context: CallbackContext) -> int:
    
    user = update.message.from_user
    try:
        cur.execute(f"DELETE FROM main WHERE user_id={user.id};")
        conn.commit()
        update.message.reply_text('Сделано.')
    except Exception:
        update.message.reply_text('Не нашел...')


def update_wishlist(update: Update, context: CallbackContext) -> int:

    update.message.reply_text('Что ты хочешь от Санты?')

    return UPDATE_WISHLIST


def update_wishlist_handler(update: Update, context: CallbackContext) -> int:

    user = update.message.from_user
    cur.execute(f"UPDATE main SET wishlist='{update.message.text}' WHERE user_id={user.id};")
    conn.commit()

    update.message.reply_text('Понял!')

    return ConversationHandler.END


def wishlist(update: Update, context: CallbackContext) -> int:

    context.bot.send_message(chat_id=update.effective_chat.id, text="Что желаете? Если нажали по ошибке или передумали напишите /skip или /cancel чтобы остановить команду.")

    return WISHLIST


def skip_wishlist(update: Update, context: CallbackContext) -> int:

    update.message.reply_text('Понял! Тогда как мне вас называть? Пишите с умом, по этому имени я вас назову вашему тайному санте.')

    return NAME


def cancel_wishlist(update: Update, context: CallbackContext) -> int:

    update.message.reply_text('Отменяю...')

    return ConversationHandler.END


def wishlist_handler(update: Update, context: CallbackContext) -> int:

    user = update.message.from_user
    
    try:
        cur.execute(f"DELETE FROM main WHERE user_id={user.id};")
        conn.commit()
    except Exception:
        pass
    
    try:
        cur.execute(f"INSERT INTO main VALUES ({user.id}, '{str(user.username)}', '{update.message.text}');")
        conn.commit()
    except Exception:
        update.message.reply_text('Упс! Чето не то пошло')
        return ConversationHandler.END
    update.message.reply_text('Как мне вас называть? Пишите с умом, по этому имени я вас назову вашему тайному санте.')

    return NAME


def define_name(update: Update, context: CallbackContext) -> int:

    user = update.message.from_user
    logger.info("User %s is called %s", user.username, update.message.text)
    try:
        cur.execute(f"UPDATE main SET name = '{update.message.text}' WHERE user_id = {user.id};")
        conn.commit()
    except Exception:
        cur.execute(f"delete from main WHERE user_id = {user.id};")
        conn.commit()
        update.message.reply_text('Упс! Попробуйте заново')
        return ConversationHandler.END
    update.message.reply_text('Охохо... Санта позаботится о том чтобы тебе дали отличный подарок!')

    return ConversationHandler.END


def shuffle(update: Update, context: CallbackContext) -> int:

    reply_keyboard = [['Да', 'Нет']]

    update.message.reply_text(
        'Надо выбрать чят где все могут увидеть что я шафлю...\n',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='В этом чате распределять?'
        ),
    )
    
    return SHUFFLE


def shuffle_handler(update: Update, context: CallbackContext) -> int:

    if update.message.text=='Нет':
        update.message.reply_text('Нет так нет', reply_markup=ReplyKeyboardRemove(),)
        return ConversationHandler.END
    
    update.message.reply_text('Начинаю...', reply_markup=ReplyKeyboardRemove(),)

    cur.execute(f"truncate table shuffle;")

    cur.execute(f"select user_id from main;")
    l = cur.fetchall()
    
    if len(l)<=2:
        update.message.reply_text('Не с кем играть чета :(')
        return ConversationHandler.END
    
    try:

        temp = [n for n in l]
        for i in range(len(l)):
            if l[i] in temp:
                temp.remove(l[i])
                shuffle = random.choice(temp)
                temp.remove(shuffle)
                temp.append(l[i])
            else:
                shuffle = random.choice(temp)
                temp.remove(shuffle)
            cur.execute(f"insert into shuffle values ('{l[i][0]}', '{shuffle[0]}');")
    except IndexError:
        cur.execute("TRUNCATE TABLE shuffle;")
        temp = [n for n in l]
        for i in range(len(l)):
            if i==0:
                shuffle = (5,)
                temp.remove(shuffle)
            elif l[i] in temp:
                temp.remove(l[i])
                shuffle = random.choice(temp)
                temp.remove(shuffle)
                temp.append(l[i])
            else:
                shuffle = random.choice(temp)
                temp.remove(shuffle)
            cur.execute(f"insert into shuffle values ('{l[i][0]}', '{shuffle[0]}');")

    conn.commit()

    update.message.reply_text('Готово!')

    cur.execute("""select m.username, m.name, m.wishlist
                    from shuffle as s
                    inner JOIN main as m
                    on s.is_santa_for=m.user_id;""")

    data = cur.fetchall()
    for element in data:
        context.bot.send_message(chat_id=element[0], text=f"Ты тайный Санта этого человека: {element[1]} (username: {element[0]}) и он/онa хочет: {element[2]}")

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversationn."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Пока!', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('ПОМОГАЮ!')


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(
        TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("delete_me", delete_me))
    dp.add_handler(CommandHandler("list", list))
    dp.add_handler(ConversationHandler(
                                       entry_points=[CommandHandler('update_wishlist', update_wishlist)],
                                       states={
                                           UPDATE_WISHLIST: [MessageHandler(Filters.text, update_wishlist_handler)],
                                       },
                                       fallbacks=[CommandHandler('cancel', cancel)],
                                       ))
    dp.add_handler(ConversationHandler(
                                       entry_points=[CommandHandler('wishlist', wishlist)],
                                       states={
                                           WISHLIST: [
                                                      CommandHandler('skip', skip_wishlist),
                                                      CommandHandler('cancel', cancel_wishlist),
                                                      MessageHandler(Filters.text, wishlist_handler), 
                                                      ],
                                           NAME: [MessageHandler(Filters.text, define_name)],
                                       },
                                       fallbacks=[CommandHandler('cancel', cancel)],
                                       ))
    dp.add_handler(ConversationHandler(
                                       entry_points=[CommandHandler('shuffle', shuffle)],
                                       states={
                                           SHUFFLE: [MessageHandler(Filters.chat(mc_id), shuffle_handler)],
                                       },
                                       fallbacks=[CommandHandler('cancel', cancel)],
                                       ))

    # on noncommand i.e message - echo the message on Telegram

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN, 
                          webhook_url="https://somesecretsantabot.herokuapp.com/" + TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()