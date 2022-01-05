from datetime import datetime
from typing import Optional, List
from pydantic import Field
from common import I4cBaseModel, DatabaseConnection
from common.exceptions import I4cServerError
from ..enums import DeviceAuto


class SnapshotStatusStatus(I4cBaseModel):
    """Timed status field of the device in a snapshot."""
    value: Optional[str] = Field(None, title="Device status.")
    since: Optional[float] = Field(None, title="Not changed since, seconds.")


class SnapshotStatusNCS(I4cBaseModel):
    """Timed name and comment field in a snapshot."""
    name: Optional[str] = Field(None, title="Name.")
    comment: Optional[str] = Field(None, title="Comment.")
    since: Optional[float] = Field(None, title="Not changed since, seconds.")


class SnapshotStatusInt(I4cBaseModel):
    """Timed numeric (integer) field in a shapshot."""
    num: Optional[int] = Field(None, title="Number.")
    since: Optional[float] = Field(None, title="Not changed since, seconds.")


class SnapshotStatusStr(I4cBaseModel):
    """Timed string field in a snapshot."""
    status: Optional[str] = Field(None, title="String.")
    since: Optional[float] = Field(None, title="Not changed since, seconds.")


class SnapshotAxis(I4cBaseModel):
    """Axis information in a snapshot."""
    name: Optional[str] = Field(None, title="Axis name.")
    mode: Optional[str] = Field(None, title="Mode of operation.")
    pos: Optional[float] = Field(None, title="Position.")
    load: Optional[float] = Field(None, title="Load.")
    rate: Optional[float] = Field(None, title="Motion rate.")


class SnapshotStatus(I4cBaseModel):
    """The device status part of a snapshot."""
    status: SnapshotStatusStatus = Field(..., title="Device status.")
    program: SnapshotStatusNCS = Field(..., title="Active program.")
    subprogram: SnapshotStatusNCS = Field(..., title="Active subprogram.")
    unit: SnapshotStatusInt = Field(..., title="Active program unit.")
    sequence: SnapshotStatusInt = Field(..., title="Active program sequence.")
    tool: SnapshotStatusInt = Field(..., title="Selected tool.")
    door: SnapshotStatusStr = Field(..., title="Door state.")
    lin_axes: List[SnapshotAxis] = Field(..., title="Linear axes.")
    rot_axes: List[SnapshotAxis] = Field(..., title="Rotary axes.")


class SnapshotEvent(I4cBaseModel):
    """Event item of a snapshot."""
    data_id: str = Field(..., title="Event type.")
    name: Optional[str] = Field(..., title="Event name.")
    timestamp: Optional[datetime] = Field(..., title="Timestamp.")
    value: Optional[str] = Field(..., title="Value.")


class SnapshotCondition(I4cBaseModel):
    """Active condition in a snapshot"""
    severity: str = Field(..., title="Severity.")
    data_id: str = Field(..., title="Condition type.")
    name: Optional[str] = Field(..., title="Condition name.")
    message: Optional[str] = Field(..., title="Message.")
    since: Optional[float] = Field(..., title="Active since, seconds.")


class MazakSnapshot(I4cBaseModel):
    """Snapshot of a Mazak machine."""
    status: SnapshotStatus = Field(..., title="Status panel.")
    event_log: List[SnapshotEvent] = Field(..., title="Recent events")
    conditions: List[SnapshotCondition] = Field(..., title="Active conditions.")


class SimpleSnapshot(I4cBaseModel):
    """Simple snapshot."""
    event_log: List[SnapshotEvent]


class Snapshot(I4cBaseModel):
    """Snapshot of the cell at a given timestamp. Only one part is returned, based on the request."""
    mill: Optional[MazakSnapshot] = Field(None, title="Milling machine.")
    lathe: Optional[MazakSnapshot] = Field(None, title="Lathe.")
    gom: Optional[SimpleSnapshot] = Field(None, title="GOM scanner.")
    robot: Optional[SimpleSnapshot] = Field(None, title="Robot.")


view_snapshot_sql = open("models/log/snapshot.sql").read()
view_snapshot_fitered_events_sql = open("models/log/snapshot_fitered_events.sql").read()
view_snapshot_events_sql = open("models/log/snapshot_events.sql").read()
view_snapshot_auto_sql = open("models/log/snapshot_auto.sql").read()


def calc_secs(base, *data_times) -> float:
    return min(((base - i).total_seconds() for i in data_times if i), default=None) if base else None


async def get_mazak_snapshot(credentials, ts, device, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        rs = await conn.fetch(view_snapshot_sql, device, ts)
        rse = await conn.fetch(view_snapshot_fitered_events_sql, device, ts)

    try:
        params = {r['data_id']: r for r in rs}

        def value(col: str):
            r = params[col]['value_num'] if params[col]["category"] == 'SAMPLE' else params[col]['value_text']
            return r if r != "UNAVAILABLE" else None

        def timstamp(col: str):
            return params[col]['timestamp']

        if value('connect') != "Normal":
            status = SnapshotStatusStatus(value="NOT CONNECTED", since=calc_secs(ts, timstamp('connect')))
        elif value('avail') == "UNAVAILABLE":
            status = SnapshotStatusStatus(value="UNAVAILABLE", since=calc_secs(ts, timstamp('avail')))
        else:
            status = SnapshotStatusStatus(value=value('exec'), since=calc_secs(ts, timstamp('exec')))

        def add_axis(name, mode, pos, rate, load):
            return SnapshotAxis(name=name, mode=value(mode), pos=value(pos), rate=value(rate), load=value(load))

        lin_axes = []
        rot_axes = []
        if device == 'lathe':
            lin_axes.append(add_axis('X', 'xaxisstate', 'xpw', 'xf', 'xl'))
            lin_axes.append(add_axis('Z', 'zaxisstate', 'zpw', 'zf', 'zl'))
            rot_axes.append(add_axis('C', 'caxisstate', 'cposw', 'cs', 'sl'))
        elif device == 'mill':
            lin_axes.append(add_axis('X', 'xaxisstate', 'xpw', 'xf', 'xl'))
            lin_axes.append(add_axis('Y', 'yaxisstate', 'ypw', 'yf', 'yl'))
            lin_axes.append(add_axis('Z', 'zaxisstate', 'zpw', 'zf', 'zl'))
            rot_axes.append(add_axis('B', 'baxisstate', 'aposw', 'af', 'al'))
            rot_axes.append(add_axis('C', 'caxisstate', 'cposw', 'cs', 'sl'))

        s = SnapshotStatus(
                status=status,
                program=SnapshotStatusNCS(name=value('pgm'),
                                          comment=value('pcmt'),
                                          since=calc_secs(ts, timstamp('pgm'), timstamp('pcmt'))),
                subprogram=SnapshotStatusNCS(name=value('spgm'),
                                          comment=value('spcmt'),
                                          since=calc_secs(ts, timstamp('spgm'), timstamp('spcmt'))),
                unit=SnapshotStatusInt(num=value("unit"), since=calc_secs(ts, timstamp('unit'))),
                sequence=SnapshotStatusInt(num=value("seq"), since=calc_secs(ts, timstamp('seq'))),
                tool=SnapshotStatusInt(num=value("tid"), since=calc_secs(ts, timstamp('tid'))),
                door=SnapshotStatusStr(status=value("door"), since=calc_secs(ts, timstamp('door'))),
                lin_axes=lin_axes,
                rot_axes=rot_axes)
        e = [SnapshotEvent(data_id=e['data_id'], name=e['name'], timestamp=e['timestamp'], value=e['value']) for e in rse]
        c = [SnapshotCondition(severity=r['value_text'], data_id=r['data_id'], name=r['name'], message=r['value_extra'], since=calc_secs(ts, r['timestamp']))
             for r in rs if r["category"] == 'CONDITION' and r["value_text"] is not None and r["value_text"] not in ('Unavailable', 'Normal')]

        return MazakSnapshot(status=s, event_log=e, conditions=c)
    except Exception as e:
        raise I4cServerError(f"Data process error: {e}")


async def get_simple_snapshot(credentials, ts, device, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        rse = await conn.fetch(view_snapshot_events_sql, device, ts)

    try:
        e = [SnapshotEvent(data_id=e['data_id'], name=e['name'], timestamp=e['timestamp'], value=e['value']) for e in rse]
        return SimpleSnapshot(event_log=e)
    except Exception as e:
        raise I4cServerError(f"Data process error: {e}")


async def get_snapshot(credentials, ts, device: DeviceAuto, *, pconn=None):
    allowed_devices = set()
    s = Snapshot()
    async with DatabaseConnection(pconn) as conn:
        if device == 'auto':
            active_device_order = []

            rs = await conn.fetch(view_snapshot_auto_sql, ts)
            for r in rs:
                active_device_order.append((r['timestamp'], r['sequence'], r['device']))

            if len(active_device_order) > 0:
                allowed_devices.add(min(active_device_order, key=lambda x: x[:2])[2])
        else:
            allowed_devices.add(device)
        if DeviceAuto.mill in allowed_devices:
            s.mill = await get_mazak_snapshot(credentials, ts, DeviceAuto.mill, pconn=conn)
        if DeviceAuto.lathe in allowed_devices:
            s.lathe = await get_mazak_snapshot(credentials, ts, DeviceAuto.lathe, pconn=conn)
        if DeviceAuto.gom in allowed_devices:
            s.gom = await get_simple_snapshot(credentials, ts, DeviceAuto.gom, pconn=conn)
        if DeviceAuto.robot in allowed_devices:
            s.robot = await get_simple_snapshot(credentials, ts, DeviceAuto.robot, pconn=conn)
    return s
