import datetime
from pydantic.schema import datetime


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
    return attrs


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
        self.value_add = None

    def AsDict(self):
        return dict(device=self.device,
                    instance=self.instance,
                    timestamp=self.timestamp,
                    sequence=self.sequence,
                    data_id=self.data_id,
                    value_num=self.value_num,
                    value_text=self.value_text,
                    value_extra=self.value_extra,
                    value_add=self.value_add)


class event_db_row(db_row):
    def __init__(self, device, instance, n):
        db_row.__init__(self)
        self.device = device
        self.instance = instance
        self.timestamp = parsedt(n.attrib["timestamp"])
        self.sequence = int(n.attrib["sequence"])
        self.data_id = n.attrib["dataItemId"]
        self.value_add = spec_attr(n)
        self.value_text = n.text or ""


class sample_db_row(db_row):
    def __init__(self, device, instance, n):
        db_row.__init__(self)
        self.device = device
        self.instance = instance
        self.timestamp = parsedt(n.attrib["timestamp"])
        self.sequence = int(n.attrib["sequence"])
        self.data_id = n.attrib["dataItemId"]
        self.value_add = spec_attr(n)
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
        self.value_add = spec_attr(n)
        self.value_text = n.tag[nsdrop:]
        self.value_extra = n.text or ""
