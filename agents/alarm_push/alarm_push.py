import sys
import os
import re
import time
import json
import i4c
import urllib.parse
import yaml
import logging.config
from pywebpush import webpush

with open("alarm_push.conf", "r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)


if "log" in cfg:
    logging.config.dictConfig(cfg["log"])

log = logging.getLogger("push_notif_agent")

poll = next((opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt == "--poll"), None)
poll = poll or conf.get("poll", None)
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
    while True:
        log.debug("get setting push_email")
        email = i4c_conn.invoke_url('settings/push_email')

        log.debug("get setting push_priv_key")
        private_key = i4c_conn.invoke_url('settings/push_priv_key')

        log.debug("get alarm recips")
        notifs = i4c_conn.invoke_url('alarm/recips?status=outbox&method=push')
        for notif in notifs:
            ev = notif["event"]
            data = {
                "notification": {
                    "title": f'{ev["alarm"]} ({ev["created"]})',
                    "body": f'{ev["summary"]}',
                    "timestamp": f'{ev["created"]}',
                    "icon": "/assets/logo.png"
                }
            }

            log.info(f'Sending notif {notif["id"]} to {notif["user"]}')
            try:
                webpush(json.loads(notif["address"]),
                        json.dumps(data),
                        vapid_private_key=private_key,
                        vapid_claims={"sub": f"mailto:{email}"})

                chg = { "conditions": [{"status": ["outbox"]}],
                        "change": {"status": "sent"} }
                try:
                    log.debug("marking as sent")
                    i4c_conn.invoke_url(f'alarm/recips/{urllib.parse.quote(str(id))}', 'PATCH',
                                        jsondata=chg)
                except Exception as e:
                    log.error(f"can't mark notif as sent: {e}")

            except Exception as e:
                # TODO can we determine if the webpush error is permanent?
                #   if permanent, we should indicate fail status
                log.error(f"error while sending notification: {e}")

        if not poll:
            break

        time.sleep(poll)

    log.debug("finished")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log.error(f"error: {e}")
        raise

