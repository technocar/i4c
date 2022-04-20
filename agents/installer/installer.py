import sys
import os
import yaml
import logging.config
from i4c import I4CConnection

args = {opt:opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt.startswith("-")}

profile = args.get("--profile")
config_file = args.get("--config-file", "installer.conf")

with open(config_file, "r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

profile = profile or cfg.get("profile")

paths = cfg["paths"]
if not isinstance(paths, list):
    raise Exception("configuration error, paths should be a list.")
if not all((isinstance(p, dict) and len(p) == 1) for p in paths):
    raise Exception("configuration error, path items should be single key dicts.")
paths = [i for p in paths for i in p.items()]

if "log" in cfg:
    logging.config.dictConfig(cfg["log"])

log = logging.getLogger("installer")

log.debug("creating connection")
c = I4CConnection(profile=profile)


def change_status(id, prev_status, status, msg):
    log.debug(f"status {prev_status} -> {status}, {msg}")
    b = {"change":{"status":status, "status_msg":msg},
         "conditions":[{"status":[prev_status]}]}
    resp = c.installation.update(id=id, body=b)
    resp = resp["changed"]
    if not resp:
        log.debug(f"status NOT changed")
    return resp


def stream_copy(src, dst):
    "This will pump data from a stream to another, used to download from http to file/stdout."
    buf = src.read(0x10000)
    while buf:
        dst.write(buf)
        buf = src.read(0x10000)

log.debug("getting installations")
installations = c.installation.list(status="todo")
log.debug(f"got {len(installations)}")

for installation in installations:
    try:
        id = installation["id"]
        files = installation["files"]
        project = installation["project"]
        ver = installation["invoked_version"]
        realver = installation["real_version"]
        if str(realver) != ver:
            ver = f"{ver} ({realver})"

        log.info(f"installing {id} for {project} .{ver}")

        if not change_status(id, "todo", "working", "analysing"):
            raise Exception("state is not 'todo' anymore")
    except Exception as e:
        log.error(f"{e}")
        continue

    try:
        # we group files by longest prefix
        file_groups = {}
        for f in files:
            pres = (pre for (pre, _) in paths if f.startswith(pre))
            if not pres:
                raise Exception(f"unknown file type '{f}'")
            pres = sorted(pres, key=lambda s: len(s), reverse=True)
            pre = pres[0]
            f = f[len(pre):]
            file_groups.setdefault(pre, []).append(f)

        # we take prefixes in order
        for prefix, base_path in paths:
            to_copy = file_groups.get(prefix, [])

            for f in to_copy:
                if not change_status(id, "working", "working", f"installing {prefix} {f}"):
                    log.warning("status changed, stopping")
                    continue

                source = prefix + f
                target = base_path + f
                target_dir, _ = os.path.split(target)
                temp_target = target_dir + "\\.tempfile"

                resp = c.installation.file(id=id, savepath=prefix+f)

                log.debug(f"saving to {target}")
                with open(temp_target, "wb") as f:
                    stream_copy(resp, f)
                os.remove(target)
                os.rename(temp_target, target)

        change_status(id, "working", "done", "done")
    except Exception as e:
        log.error(f"{e}")
        try:
            change_status(id, "working", "fail", f"{e}")
        except Exception as e:
            log.error(f"{e}")
        continue
