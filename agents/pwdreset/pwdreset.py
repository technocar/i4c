import os
import sys
import yaml
import logging.config
import smtplib
import jinja2
import i4c


log = None # will be filled in from main


def fail(msg, exit_code=1):
    if msg is not None:
        print(f"{msg}")
    log.debug(f"fail {exit_code} {msg}")
    sys.exit(exit_code)


def main():
    if os.path.isfile("pwdreset.conf"):
        with open("pwdreset.conf", "r") as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)
    else:
        conf = {}

    if "log" in conf:
        logging.config.dictConfig(conf["log"])

    log = logging.getLogger()
    log.debug("start")

    profile = next((opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt == "--profile"), None)
    if not profile and "profile" in conf:
        profile = conf["profile"]
    log.debug(f"profile: {profile}")

    svr = conf.get("smtp-server", None)
    uid = conf.get("smtp-server", None)
    pwd = conf.get("smtp-password", None)
    mail_from = conf.get("smtp-from", None)
    smtp_protocol = conf.get("smtp-from", "starttls")

    log.debug("accessing profile")
    conn = i4c.I4CConnection(profile=profile)
    extra = conn.profile_data.get("extra", {})
    svr = svr or extra.get("smtp-server", None)
    uid = uid or extra.get("smtp-user", None)
    pwd = pwd or extra.get("smtp-password", None)
    mail_from = mail_from or extra.get("smtp-from", None)
    smtp_protocol = smtp_protocol or extra.get("smtp-protocol", None)

    if svr is None:
        log.debug("no server is given, falling back to localhost")
        svr = "127.0.0.1"
    
    if smtp_protocol not in ("tls", "starttls", "plain"):
        fail(f"Smtp protocol must be tls, starttls or plain. '{smtp_protocol}' was given.")

    with open("pwdreset.html", "r") as f:
        tmpl = f.read()

    env = jinja2.Environment()
    tmpl = env.from_string(tmpl)

    log.debug("getting pwdreset list")
    try:
        resets = conn.pwdreset.list()
    except Exception as e:
        fail(e)

    log.debug(f"got {len(resets)} items")
    for r in resets:
        email = r["email"]
        token = r["token"]
        login = r["loginname"]
        log.info(f"sending to {email} for {login}")

        log.debug("rendering")
        html = tmpl.render(email=email, token=token, login=login)
        print(f"sending to {email}")
        print(html)

        try:
            mailer = smtplib.SMTP(svr)
            mailer.login(uid, pwd)
            # TODO send email
            raise Exception("SENDING NOT IMPLEMENTED")

            try:
                log.debug("marking as sent")
                conn.pwdreset.mark_sent(body={"loginname": login})
            except Exception as e:
                log.error(f"Failed to mark {login} as sent: {e}")

        except Exception as e:
            log.error(f"send fail {email} for {login}")

    log.debug("finished")

if __name__ == '__main__':
    main()