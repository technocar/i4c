from datetime import datetime
from typing import Optional, List
from common import MyBaseModel, DatabaseConnection
from fastapi import HTTPException
from .enums import DeviceAuto


class SnapshotStatusStatus(MyBaseModel):
    value: Optional[str]
    since: Optional[float]


class SnapshotStatusNCS(MyBaseModel):
    name: Optional[str]
    comment: Optional[str]
    since: Optional[float]


class SnapshotStatusInt(MyBaseModel):
    num: Optional[int]
    since: Optional[float]


class SnapshotStatusStr(MyBaseModel):
    status: Optional[str]
    since: Optional[float]


class SnapshotAxis(MyBaseModel):
    name: Optional[str]
    mode: Optional[str]
    pos: Optional[float]
    load: Optional[float]
    rate: Optional[float]


class SnapshotStatus(MyBaseModel):
    status: SnapshotStatusStatus
    program: SnapshotStatusNCS
    subprogram: SnapshotStatusNCS
    unit: SnapshotStatusInt
    sequence: SnapshotStatusInt
    tool: SnapshotStatusInt
    door: SnapshotStatusStr
    lin_axes: List[SnapshotAxis]
    rot_axes: List[SnapshotAxis]


class SnapshotEvent(MyBaseModel):
    data_id: str
    name: Optional[str]
    timestamp: Optional[datetime]
    value: Optional[str]


class SnapshotCondition(MyBaseModel):
    severity: str
    data_id: str
    name: Optional[str]
    message: Optional[str]
    since: Optional[float]


class MazakSnapshot(MyBaseModel):
    status: SnapshotStatus
    event_log: List[SnapshotEvent]
    conditions: List[SnapshotCondition]


class SimpleSnapshot(MyBaseModel):
    event_log: List[SnapshotEvent]


class Snapshot(MyBaseModel):
    mill: Optional[MazakSnapshot]
    lathe: Optional[MazakSnapshot]
    gom: Optional[SimpleSnapshot]
    robot: Optional[SimpleSnapshot]


view_snapshot_sql = open("models\\snapshot.sql").read()
view_snapshot_events_sql = open("models\\snapshot_events.sql").read()
view_snapshot_auto_mazak_sql = open("models\\snapshot_auto_mazak.sql").read()


def calc_secs(base, *data_times) -> float:
    return min(((base - i).total_seconds() for i in data_times if i), default=None) if base else None


async def get_mazak_snapshot(credentials, ts, device, *, pconn=None):
    try:
        async with DatabaseConnection(pconn) as conn:
            rs = await conn.fetch(view_snapshot_sql, device, ts)
            rse = await conn.fetch(view_snapshot_events_sql, device, ts)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Sql error: {e}")

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
        raise HTTPException(status_code=500, detail=f"Data process error: {e}")


async def get_simple_snapshot(credentials, ts, device, *, pconn=None):
    try:
        async with DatabaseConnection(pconn) as conn:
            rse = await conn.fetch(view_snapshot_events_sql, device, ts)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Sql error: {e}")

    try:
        e = [SnapshotEvent(data_id=e['data_id'], name=e['name'], timestamp=e['timestamp'], value=e['value']) for e in rse]
        return SimpleSnapshot(event_log=e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data process error: {e}")


async def get_snapshot(credentials, ts, device: DeviceAuto, *, pconn=None):
    allowed_devices = set()
    s = Snapshot()
    async with DatabaseConnection(pconn) as conn:
        if device == 'auto':
            rs = await conn.fetch(view_snapshot_auto_mazak_sql, ts)
            if rs:
                for r in rs:
                    allowed_devices.add(r['device'])
            else:
                # todo 1: device == 'auto' / robot, gom
                pass
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
