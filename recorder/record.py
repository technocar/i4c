import sys
import datetime
import time
import urllib.request
import xml.etree.ElementTree as xmlet
from textwrap import dedent
# todo 1: remove psycopg2, even from requirements.txt
import psycopg2
import yaml
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

with open("dbconfig.yaml") as f:
    dbcfg = yaml.load(f, Loader=yaml.FullLoader)


def parsedt(s):
    d, _, t = s.partition("T")

    if t.endswith("Z"):
        t = t[:-1]
        z = "+00:00"
    else:
        t, sig, z = t.partition("+")
        if not sig:
            t, sig, z = t.partition("-")
        z = sig + z

    t = t.ljust(15, "0")

    return datetime.fromisoformat(f"{d}T{t}{z}")


def spec_attr(node):
    attrs = { k:v for (k, v) in node.attrib.items()
        if k not in ("dataItemId", "timestamp", "sequence", "name", "subType", "type")}
    if len(attrs) == 0:
        return None
    return json.dumps(attrs)


class db_row:
    def __init__(self):
        self.device = None
        self.instance = None
        self.timestamp = None
        self.sequence = None
        self.data_id = None
        self.value_num = None
        self.value_text = None
        self.value_extra = None
        self.value_aux = None

    def AsTuple(self):
        return (self.device,
                self.instance,
                self.timestamp,
                self.sequence,
                self.data_id,
                self.value_num,
                self.value_text,
                self.value_extra,
                self.value_aux)


class event_db_row(db_row):
    def __init__(self, device, instance, n):
        db_row.__init__(self)
        self.device = device
        self.instance = instance
        self.timestamp = parsedt(n.attrib["timestamp"])
        self.sequence = int(n.attrib["sequence"])
        self.data_id = n.attrib["dataItemId"]
        self.value_aux = spec_attr(n)
        self.value_text = n.text or ""


class sample_db_row(db_row):
    def __init__(self, device, instance, n):
        db_row.__init__(self)
        self.device = device
        self.instance = instance
        self.timestamp = parsedt(n.attrib["timestamp"])
        self.sequence = int(n.attrib["sequence"])
        self.data_id = n.attrib["dataItemId"]
        self.value_aux = spec_attr(n)
        try:
            self.value_num = float(n.text)
        except ValueError:
            pass


class condition_db_row(db_row):
    def __init__(self, device, instance, n, nsdrop):
        db_row.__init__(self)
        self.device = device
        self.instance = instance
        self.timestamp = parsedt(n.attrib["timestamp"])
        self.sequence = int(n.attrib["sequence"])
        self.data_id = n.attrib["dataItemId"]
        self.value_aux = spec_attr(n)
        self.value_text = n.tag[nsdrop:]
        self.value_extra = n.text or ""


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
    data = s + e + c

    return data, dict(next=next, last=last, first=first, inst=newinst)


def value_esc(v):
    return (v or "").replace("\n", "/").replace("\t", " ")


def update_connect_state(conn, old, new):
    if old == new:
        return old

    with conn.cursor() as cur:
        cur.execute(dedent("""\
                      insert into minimon_log
                      (
                         device,
                         instance,
                         "timestamp",
                         sequence,
                         data_id,
                         value_num,
                         value_text,
                         value_extra,
                         value_aux
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (device, "timestamp", sequence)
                        DO NOTHING"""), (dev, None, datetime.now(), 0, 'connect', None, new, None, None))
        conn.commit()
    return new


def main():
    conn = None
    inst = None
    old_inst = None
    start = None
    connect_state = None
    try:
        while True:
            try:
                if conn is None:
                    conn = psycopg2.connect(**dbcfg)

                    with conn.cursor() as cur:
                        last_state_sql = dedent("""\
                                           select l.instance, l.sequence 
                                           from minimon_log l 
                                           where 
                                             l.instance is not null
                                             and l.device = %s
                                           order by l.timestamp desc, l.sequence desc
                                           limit 1""")
                        cur.execute(last_state_sql, (dev,))
                        row = cur.fetchone()
                        if row:
                            old_inst = row[0]

                        connect_state_sql = dedent("""\
                                                select l.value_text
                                                from public.minimon_log l
                                                where 
                                                  l.device = %s -- */ 'lathe'
                                                  and l.data_id = 'connect'
                                                order by l.timestamp desc, l."sequence" desc
                                                limit 1                        
                                              """)

                        cur.execute(connect_state_sql, (dev,))
                        row = cur.fetchone()
                        if row is not None:
                            connect_state = row[0]

                    (_, stats) = mtsample(0, 1)
                    inst = stats["inst"]

                    if old_inst == inst:
                        start = row[1] + 1
                        if start < stats["first"]:
                            start = 0
                    else:
                        inst = None
                        start = 0

                (data, stats) = mtsample(start, 100, inst)
                connect_state = update_connect_state(conn, connect_state, 'Normal')
            except Exception as e:
                line = f"\t{datetime.now().astimezone()}\t:META\t{value_esc(str(e))}\n"
                connect_state = update_connect_state(conn, connect_state, 'Fault')
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

            with conn.cursor() as cur:
                x = [d.AsTuple() for d in data]
                cur.executemany(dedent("""\
                                  insert into minimon_log
                                  (
                                     device,
                                     instance,
                                     "timestamp",
                                     sequence,
                                     data_id,
                                     value_num,
                                     value_text,
                                     value_extra,
                                     value_aux
                                    )
                                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (device, "timestamp", sequence)
                                    DO NOTHING"""), x)
                conn.commit()

            data_line = [f"{d.sequence}\t{d.timestamp}\t{d.data_id}\t{value_esc(d.value_text)}\t{str(d.value_num)}" 
                         f"\t{value_esc(d.value_extra)}\t{value_esc(d.value_aux)}\n" for d in data]
            sys.stdout.writelines(data_line)

            start = stats["next"]
            if start > stats["last"]:
                if not poll:
                    break
                else:
                    time.sleep(sleeptime)
    finally:
        if conn is not None:
            conn.close()


if __name__ == '__main__':
    main()
