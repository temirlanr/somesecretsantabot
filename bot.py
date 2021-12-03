import logging
import os
import psycopg2

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, conversationhandler

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

PORT = int(os.environ.get('PORT', '8440'))
TOKEN = os.environ["TOKEN"]

DATABASE_URL = os.environ['DATABASE_URL']

conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

mc_id = "-743252633"

WISHLIST = range(1)
# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.


def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def wishlist(update: Update, context: CallbackContext) -> int:

    context.bot.send_message(chat_id=update.effective_chat.id, text="WHat do you want from santa my dear?")

    return WISHLIST 


def wishlist_handler(update: Update, context: CallbackContext) -> int:


    update.message.reply_text('You for sure will get an amazing present from santa!')

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
                                       entry_points=[CommandHandler('suggestion', wishlist)],
                                       states={
                                           WISHLIST: [MessageHandler(Filters.text, wishlist_handler)],
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