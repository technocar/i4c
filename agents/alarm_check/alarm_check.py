import sys
import time
import re
import yaml
import logging.config
import i4c

opts = {opt: opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt.startswith("--")}

config_file = opts.get("--config-file", "alarm_check.conf")

with open(config_file, "r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

if "log" in cfg:
    logging.config.dictConfig(cfg["log"])

log = logging.getLogger("alarm_check")

poll = opts.get("--poll") or cfg.get("poll", None)
if poll:
    m = re.fullmatch(r"0*([1-9]\d*)\s*(m?s)", poll)
    if not m:
        raise Exception(f"Poll must be positive integer seconds (5s) or milliseconds (200ms). {poll} was given.")
    poll = int(m[1])
    if m[2] == "ms":
        poll = poll / 1000.0
    log.debug(f"poll: {poll}s")

profile = opts.get("--profile") or cfg.get("profile", None)
log.debug(f"using profile {profile}")

i4c_conn = i4c.I4CConnection(profile=profile)

while True:
    try:
        log.debug(f"checking")

        alarms = i4c_conn.alarm.check(noaudit=True)

        for a in alarms:
            name = a.get("alarm")
            log.info(f"triggered alarm: {name}")

    except Exception as e:
        log.error(f"{e}")

    if poll is None:
        break

    time.sleep(poll)