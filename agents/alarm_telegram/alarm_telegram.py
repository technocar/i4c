import i4c
import telegram
import yaml
import logging.config
import sys
import time
import datetime
import re

from telegram.ext.commandhandler import CommandHandler
from telegram.ext.updater import Updater
from telegram.ext.dispatcher import Dispatcher
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext

cfg: dict = None
log: logging.Logger = None
poll = 0
i4c_conn: i4c.I4CConnection = None
bot: telegram.Bot = None
updater: Updater = None
dispatcher: Dispatcher = None


def is_accessible(telegram_user: telegram.User, function: str, chat_id: str) -> bool:
    global log

    #    TODO: Add code to check if the current user has the right to execute command
    #    Telegram user must be mapped to i4c user

    result = True
    if not result:
        log.error(f"Telegram user {telegram_user.username} doesn't have the right to {function}")
        bot.send_message(chat_id=chat_id, parse_mode=telegram.constants.PARSEMODE_HTML,
                         text="Nincs hozzá joga")
    return result


def init_bot():
    global bot
    global i4c_conn
    global updater
    global dispatcher

    def my_user_id(update: Update, context: CallbackContext):
        if is_accessible(update.effective_user, "my_user_id", update.effective_chat.id):
            bot.send_message(chat_id=update.effective_chat.id,
                             parse_mode=telegram.constants.PARSEMODE_HTML,
                             text=f"Az ön azonosítója: {update.effective_user.id}")

    def my_chat_id(update: Update, context: CallbackContext):
        # rslt = context.bot.get_chat_member(chat_id=update.effective_chat.id, user_id=update.effective_user.id)
        if is_accessible(update.effective_user, "my_chat_id", update.effective_chat.id):
            bot.send_message(chat_id=update.effective_chat.id,
                             parse_mode=telegram.constants.PARSEMODE_HTML,
                             text=f"A chat szoba azonosítója: {update.effective_chat.id}")

    def command(update: Update, context: CallbackContext):
        if is_accessible(update.effective_user, "command", update.effective_chat.id):
            bot.send_message(chat_id=update.effective_chat.id,
                             parse_mode=telegram.constants.PARSEMODE_HTML,
                             text="""Üdvözli az i4c telegram bot!
                                 
<b>command</b> - Elérhető parancsok listája
<b>mychatid</b> - Ennek a chat szobának az azonosítója
<b>myuserid</b> - Az Ön azonosítója
<b>logo</b> - TechnoCar logo""")

    def logo(update: Update, context: CallbackContext):
        if is_accessible(update.effective_user, "logo", update.effective_chat.id):
            bot.send_photo(chat_id=update.effective_chat.id,
                           photo="http://www.technocar.hu/assets/images/tc-logo-121x117.jpg")

    if bot is None:
        log.debug("getting telegram API key")
        api_key = i4c_conn.invoke_url('settings/telegram_api_key')
        bot = telegram.Bot(token=api_key)

    if updater is None:
        updater = Updater(bot=bot, use_context=True)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler(command="mychatid", callback=my_chat_id))
        dispatcher.add_handler(CommandHandler(command="myuserid", callback=my_user_id))
        dispatcher.add_handler(CommandHandler(command="command", callback=command))
        dispatcher.add_handler(CommandHandler(command="logo", callback=logo))
        updater.start_polling()


def init_globals():
    global cfg
    global log
    global poll
    global i4c_conn
    
    with open("alarm_telegram.conf", "r") as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)

    if "log" in cfg:
        logging.config.dictConfig(cfg["log"])
    log = logging.getLogger("push_notif_agent")

    poll = next((opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt == "--poll"), None)
    poll = poll or cfg.get("poll", None)
    if poll:
        m = re.fullmatch(r"0*([1-9]\d*)\s*(m?s)", poll)
        if not m:
            raise Exception(f"Poll must be positive integer seconds (5s) or milliseconds (200ms). {poll} was given.")
        poll = int(m[1])
        if m[2] == "ms":
            poll = poll / 1000.0
    log.debug(f"poll: {poll}s")

    profile = next((opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt == "--profile"), None)
    profile = profile or cfg.get("profile", None)
    log.debug(f"using profile {profile}")

    i4c_conn = i4c.I4CConnection(profile=profile)


def main():

    def set_status(id, status):
        try:
            log.debug(f"marking as {status}")
            chg = {"conditions": [{"status": ["outbox"]}], "change": {"status": status}}
            i4c_conn.invoke_url(f'alarm/recips/{id}', 'PATCH', jsondata=chg)
        except Exception as e:
            log.error(f"error while marking as {status}: {e}")

    def set_backoff(id, fail_count, backoff):
        try:
            log.debug(f"setting backoff")
            chg = {"conditions": [{"status": ["outbox"]}],
                   "change": {"backoff_until": backoff.isoformat(), "fail_count": fail_count}}
            i4c_conn.invoke_url(f'alarm/recips/{id}', 'PATCH', jsondata=chg)
        except Exception as e:
            log.error(f"error while setting backoff: {e}")

    while True:
        init_bot()
        notifs = i4c_conn.invoke_url('alarm/recips?status=outbox&method=telegram&noaudit=1&no_backoff=1')
        for notif in notifs:
            ev = notif["event"]
            id = notif["id"]

            try:
                log.info(f'sending to {notif["address"]} for {ev["alarm"]}')
                bot.send_message(chat_id=notif["address"], text=ev["description"])
                set_status(id, "sent")
            except Exception as e:
                fail_count = notif["fail_count"]
                if fail_count > 4:
                    log.error(f'too many fails, giving up for {notif["address"]}: {e}')
                    set_status(notif["id"], 'failed')
                else:
                    log.error(f'temporary fail, retrying later for {notif["address"]}: {e}')
                    fail_count += 1
                    backoff = datetime.datetime.now().astimezone() + \
                              datetime.timedelta(seconds=[1, 5, 10, 60, 240][fail_count - 1])
                    set_backoff(notif["id"], fail_count, backoff)

        if not poll:
            break

        time.sleep(poll)
        log.debug("finished")


if __name__ == '__main__':
    try:
        init_globals()
        init_bot()
        main()
        updater.stop()
    except Exception as e:
        log.error(f"error: {e}")
        raise
