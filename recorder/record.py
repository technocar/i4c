import sys
import datetime
import time
import urllib.request
import xml.etree.ElementTree as xmlet
import requests
import yaml
from typing import List
from requests.auth import HTTPBasicAuth
import pytz
from db_row import condition_db_row, sample_db_row, event_db_row, db_row
import json
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

with open("apiconfig.yaml") as f:
    apicfg = yaml.load(f, Loader=yaml.FullLoader)


def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.astimezone(pytz.utc).replace(tzinfo=None).isoformat(timespec='milliseconds')+'Z'
    raise TypeError("Type %s not serializable" % type(obj))


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

    response = requests.post(f"{apicfg['url']}/log/",
                            data=json.dumps([dict(device=dev,
                                                  timestamp=datetime.now(),
                                                  sequence=0,
                                                  data_id='connect',
                                                  value_text=new),], default=json_serial),
                            headers={"Content-Type": "application/json"},
                            auth=HTTPBasicAuth(apicfg['user'], apicfg['password']))
    response.raise_for_status()
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

                response = requests.get(f"{apicfg['url']}/log/last_instance",
                                        dict(device=dev),
                                        auth=HTTPBasicAuth(apicfg['user'], apicfg['password']) )
                response.raise_for_status()
                last_instance_res = response.json()
                if last_instance_res:
                    old_inst = last_instance_res["instance"]

                response = requests.get(f"{apicfg['url']}/log/find",
                                        dict(device=dev, before_count=1, name="connect"),
                                        auth=HTTPBasicAuth(apicfg['user'], apicfg['password']) )
                response.raise_for_status()
                find_res = response.json()
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
        djs = json.dumps(dx, default=json_serial)
        response = requests.post(f"{apicfg['url']}/log/",
                                 data=json.dumps(dx, default=json_serial),
                                 headers={"Content-Type": "application/json"},
                                 auth=HTTPBasicAuth(apicfg['user'], apicfg['password']))
        response.raise_for_status()

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
