# sample>
#   http://karatnetsrv:5012/sample
# replay start>
#   curl "karatnetsrv:5012/script?id=recorded" -d "0 .spawn recorded"

import sys
import datetime
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as xmlet
from typing import List
from db_row import condition_db_row, sample_db_row, event_db_row, db_row
import i4c as i4c
from pydantic.schema import datetime


args = filter(lambda s: not s.startswith("--"), sys.argv[1:])
host = next(args, None)
dev = next(args, None)
if dev is None:
    print("record.py host dev [sleeptime] [--poll]")
    raise Exception("Invalid command line config.")
if "://" not in host:
    host = f"http://{host}"
poll = "--poll" in sys.argv
sleeptime = float(next(args, "1"))
i4c_conn = i4c.I4CConnection()


def mtsample(start, count, inst=None):
    start = f"from={start}" if start else ""
    url = f"{host}/sample?{start}&count={count}"
    r = urllib.request.urlopen(url, timeout=10)
    ct = r.headers.get_content_type()
    if ct != "text/xml":
        raise Exception("Error: non XML content")
    xmlstr = r.read()
    x = xmlet.fromstring(xmlstr)
    if x.tag.startswith("{"):
        ns = x.tag
        ns = ns[1:]
        ns, _, _ = ns.partition("}")
        nsdrop = len(ns) + 2
        n = x.find("./mtc:Header", namespaces={"mtc": ns})
        s = x.findall(".//mtc:Samples/*", namespaces={"mtc": ns})
        e = x.findall(".//mtc:Events/*", namespaces={"mtc": ns})
        c = x.findall(".//mtc:Condition/*", namespaces={"mtc": ns})
        err = x.findall(".//mtc:Errors/mtc:Error", namespaces={"mtc": ns})
    else:
        nsdrop = 0
        n = x.find("./Header")
        s = x.findall(".//Samples/*")
        e = x.findall(".//Events/*")
        c = x.findall(".//Condition/*")
        err = x.findall(".//Errors/Error")

    newinst = n.attrib["instanceId"]

    if err:
        if inst is not None and newinst != inst:
            return [], dict(inst=newinst)
        raise Exception("\n".join(e.text for e in err))

    last = int(n.attrib["lastSequence"])
    next = int(n.attrib["nextSequence"])
    first = int(n.attrib["firstSequence"])

    s = [sample_db_row(dev, newinst, n) for n in s]
    e = [event_db_row(dev, newinst, n) for n in e]
    c = [condition_db_row(dev, newinst, n, nsdrop) for n in c]
    data = s  # type: List[db_row]
    data.extend(e)
    data.extend(c)

    return data, dict(next=next, last=last, first=first, inst=newinst)


def value_esc(v):
    return (v or "").replace("\n", "/").replace("\t", " ")


def update_connect_state(old, new):
    if old == new:
        return old

    i4c_conn.invoke_url("log",
                        data=[dict(device=dev,
                              timestamp=datetime.now(),
                              sequence=0,
                              data_id='connect',
                              value_text=new)])
    return new


def main():
    inst = None
    old_inst = None
    start = None
    connect_state = None
    first_run = True
    while True:
        try:
            if first_run:
                first_run = False

                last_instance_res = i4c_conn.invoke_url(f"log/last_instance?device={urllib.parse.quote(dev)}")
                if last_instance_res:
                    old_inst = last_instance_res["instance"]

                find_res = i4c_conn.invoke_url(f"log/find?device={urllib.parse.quote(dev)}&before_count=1&name=connect")
                if find_res:
                    connect_state = find_res[0]["value_text"]

                (_, stats) = mtsample(0, 1)
                inst = stats["inst"]

                if old_inst == inst:
                    start = int(last_instance_res["sequence"]) + 1
                    if start < stats["first"]:
                        start = 0
                else:
                    inst = None
                    start = 0

            (data, stats) = mtsample(start, 100, inst)
            connect_state = update_connect_state(connect_state, 'Normal')
        except Exception as e:
            line = f"\t{datetime.now().astimezone()}\t:META\t{value_esc(str(e))}\n"
            connect_state = update_connect_state(connect_state, 'Fault')
            sys.stdout.write(line)
            time.sleep(sleeptime)
            continue

        if inst is not None and inst != stats["inst"]:
            start = 0
            inst = stats["inst"]
            line = f"\t{datetime.now().astimezone()}\t:META\tinstance changed\n"
            sys.stdout.write(line)
            continue

        inst = stats["inst"]

        dx = [d.AsDict() for d in data]
        i4c_conn.invoke_url("log", jsondata=dx)

        data_line = [f"{d.sequence}\t{d.timestamp}\t{d.data_id}\t{value_esc(d.value_text)}\t{str(d.value_num)}" 
                     f"\t{value_esc(d.value_extra)}\t{value_esc(d.value_add)}\n" for d in data]
        sys.stdout.writelines(data_line)

        start = stats["next"]
        if start > stats["last"]:
            if not poll:
                break
            else:
                time.sleep(sleeptime)


if __name__ == '__main__':
    main()
