import json

import cli
import urllib.parse
import yaml
import logging.config
from pywebpush import webpush

with open("logconfig.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)
    logging.config.dictConfig(cfg)
log = logging.getLogger("push_notif_agent")

i4c = cli.I4CConnection()


def mark_sent(id):
    res = i4c.invoke_url(f'alarm/recips/{urllib.parse.quote(str(id))}', 'PATCH',
                         {"conditions": [{"status": ["outbox"]}],
                          "change": {"status": "sent"}
                          })
    log.info(f"Notif marked as sent: res = {res}, id = {id}")


def main():
    try:
        log.info("program started")
        log.info("get settings/push_email")
        email = i4c.invoke_url('settings/push_email')
        log.info("get settings/push_priv_key")
        private_key = i4c.invoke_url('settings/push_priv_key')
        log.info("get settings/alarm/recips")
        notifs = i4c.invoke_url('alarm/recips?status=outbox&method=push')
        for notif in notifs:
            ev = notif["event"]
            data = f'{ev["alarm"]} ({ev["created"]}):\n{ev["summary"]}'

            log.info(f'Sending notif: id = {notif["id"]}')
            try:
                webpush(json.loads(notif["address"]),
                        data,
                        vapid_private_key=private_key,
                        vapid_claims={"sub": f"mailto:{email}"})
            except Exception as e:
                log.error(f"error while sending notification: {e}")
            else:
                mark_sent(notif["id"])
    except Exception as e:
        log.error(f"error: {e}")
        raise
    else:
        log.info("program finished normally")


if __name__ == '__main__':
    main()
