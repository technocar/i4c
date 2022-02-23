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

cfg = None
log = None
poll = 0
i4c_conn = None
bot: telegram.Bot = None
updater = None
dispatcher: Dispatcher = None


def init_bot():
    global bot
    global i4c_conn
    global updater
    global dispatcher

    def my_chat_id(update: Update, context: CallbackContext):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 parse_mode=telegram.constants.PARSEMODE_HTML,
                                 text=f"A chat szoba azonosítója: {update.effective_chat.id}")

    def command(update: Update, context: CallbackContext):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 parse_mode=telegram.constants.PARSEMODE_HTML,
                                 text="""Üdvözli az i4c telegram bot!
                                 
<b>command</b> - Elérhető parancsok listája
<b>mychatid</b> - Ennek a chat szobának az azonosítója
<b>logo</b> - TechnoCar logo""")

    def logo(update: Update, context: CallbackContext):
        context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo="http://www.technocar.hu/assets/images/tc-logo-121x117.jpg")



    log.debug("getting telegram API key")
    api_key = i4c_conn.invoke_url('settings/telegram_api_key')

    if bot is None:
        bot = telegram.Bot(token=api_key)

    if updater is None:
        updater = Updater(api_key, use_context=True)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler("mychatid", my_chat_id))
        dispatcher.add_handler(CommandHandler("command", command))
        dispatcher.add_handler(CommandHandler("logo", logo))
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


def main():
    global bot
    global updater


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

