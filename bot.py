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
# context. Error handlers also receive the raised TelegramError object in error.


def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def update_wishlist(update: Update, context: CallbackContext) -> int:

    update.message.reply_text('What do you want from Santa?')

    return UPDATE_WISHLIST


def update_wishlist_handler(update: Update, context: CallbackContext) -> int:

    user = update.message.from_user
    cur.execute(f"UPDATE TABLE main SET wishlist='{update.message.text}' WHERE user_id={user.id};")
    conn.commit()

    update.message.reply_text('Got it!')

    return ConversationHandler.END


def wishlist(update: Update, context: CallbackContext) -> int:

    context.bot.send_message(chat_id=update.effective_chat.id, text="What do you want from santa my dear?")

    return WISHLIST 


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
        update.message.reply_text('Oops! Error occurred')
        return ConversationHandler.END
    update.message.reply_text('Now tell me how to call you!')

    return NAME


def define_name(update: Update, context: CallbackContext) -> int:

    user = update.message.from_user
    logger.info("User %s is called %s", user.username, update.message.text)
    try:
        cur.execute(f"UPDATE main SET name = '{update.message.text}' WHERE user_id = {user.id};")
        conn.commit()
    except Exception:
        update.message.reply_text('Oops! Error occurred, try again')
        cur.execute(f"delete from main WHERE user_id = {user.id};")
        conn.commit()
        return ConversationHandler.END
    update.message.reply_text('You for sure will get an amazing present from santa!')

    return ConversationHandler.END


def shuffle(update: Update, context: CallbackContext) -> int:

    reply_keyboard = [['Yes', 'No']]

    update.message.reply_text(
        'So we need to pick a chat where everyone is present and I can start shuffling and you can see it.\n',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Do you wish to set this chat as main?'
        ),
    )
    
    return SHUFFLE


def shuffle_handler(update: Update, context: CallbackContext) -> int:

    if update.message.text=='No':
        update.message.reply_text('No means No', reply_markup=ReplyKeyboardRemove(),)
        return ConversationHandler.END
    
    update.message.reply_text('Starting then...', reply_markup=ReplyKeyboardRemove(),)

    cur.execute(f"truncate table shuffle;")

    cur.execute(f"select user_id from main;")
    l = cur.fetchall()
    
    if len(l)<=2:
        update.message.reply_text('No people to play with :(')
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

    update.message.reply_text('Done shuffling!')

    cur.execute("""select s.user_id, m.name, m.wishlist
                    from shuffle as s
                    inner JOIN main as m
                    on s.is_santa_for=m.user_id;""")

    data = cur.fetchall()
    for element in data:
        context.bot.send_message(chat_id=element[0], text=f"You are a secret santa for {element[1]} and his wishlist is: {element[2]}")

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversationn."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


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
                                           WISHLIST: [MessageHandler(Filters.text , wishlist_handler)],
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