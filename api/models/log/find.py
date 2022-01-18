from datetime import datetime
from typing import Optional, List, Dict
from pydantic import Field
from common import I4cBaseModel, write_debug_sql, DatabaseConnection, log
from common.db_tools import asyncpg_rows_process_json
from common.exceptions import I4cClientError

view_find_sql = open("models/log/find.sql").read()


class DataPointKey(I4cBaseModel):
    """Unique identifier of a data point in the log."""
    timestamp: datetime = Field(..., title="Exact time the data was collected.")
    sequence: int = Field(..., title="Sequence, used to determine order when the timestamp is identical.")
    device: str = Field(..., title="Originating device.")
    data_id: str = Field(..., title="Data type.")


class DataPoint(I4cBaseModel):
    """One data point in the log."""
    timestamp: datetime = Field(..., title="Exact time the data was collected.")
    sequence: int = Field(..., title="Sequence, used to determine order when the timestamp is identical.")
    device: str = Field(..., title="Originating device.")
    instance: Optional[str] = Field(None, title="Identifies a session on a device. Changes when turned off.")
    data_id: str = Field(..., title="Data type.")
    value: Optional[str]
    value_num: Optional[float] = Field(None, title="Numeric value")
    value_text: Optional[str] = Field(None, title="Text value")
    value_extra: Optional[str] = Field(None, title="Additional text value")
    value_add: Optional[Dict[str,str]] = Field(None, title="Other information")


def get_find_sql(params, timestamp, sequence, before_count, after_count, categ, name, val, extra, rel, *,
                 allow_exact_ts_match: bool = True, seq_part: Optional[str] = None):
    wheres = []
    rank_direction = 'desc'
    count = None
    comp_rel = None
    if rel is None:
        rel = '='
    if rel not in ('=','<','>','<=','>=','!=','*=','*!='):
        raise I4cClientError(f"Invalid rel parameter")
    if rel == '*=':
        srel = 'like \'%\'||<val>||\'%\''
    elif rel == '*!=':
        srel = 'not like \'%\'||<val>||\'%\''
    else:
        srel = rel + " <val>"

    if before_count is None and after_count is None:
        before_count = 1

    if before_count is not None and after_count is not None:
        sql_before = get_find_sql(params, timestamp, sequence, before_count, None, categ, name, val, extra, rel, allow_exact_ts_match=allow_exact_ts_match)
        sql_after = get_find_sql(params, timestamp, sequence, None, after_count, categ, name, val, extra, rel, allow_exact_ts_match=False)
        return f'with before as ({sql_before}), '\
               f'after as ({sql_after}) ' \
               f'select * from before ' \
               f'union all ' \
               f'select * from after ' \
               f'order by timestamp desc, "sequence" desc'

    if before_count is not None:
        count = before_count
        comp_rel = '<'

    if after_count is not None:
        rank_direction = 'asc'
        count = after_count
        comp_rel = '>'

    if sequence is not None and seq_part is None:
        sql_ts = get_find_sql(params, timestamp, sequence, before_count, after_count, categ, name, val, extra, rel, allow_exact_ts_match=allow_exact_ts_match, seq_part="ts")
        sql_seq = get_find_sql(params, timestamp, sequence, before_count, after_count, categ, name, val, extra, rel, allow_exact_ts_match=False, seq_part="seq")
        return f'with ts as ({sql_ts}), '\
               f'seq as ({sql_seq}) ' \
               f'select * from ts ' \
               f'union all ' \
               f'select * from seq ' \
               f'order by timestamp {rank_direction}, "sequence" {rank_direction} ' \
               f'limit {count}'

    if comp_rel is not None:
        if timestamp is not None and (seq_part is None or seq_part == 'ts'):
            params.append(timestamp)
            wheres.append(f'and (l.timestamp {comp_rel}{"=" if allow_exact_ts_match and sequence is None else ""} '
                          f'${len(params)}::timestamp with time zone)')
        if sequence is not None and seq_part == 'seq':
            params.append(timestamp)
            params.append(sequence)
            wheres.append(f'and (l.timestamp = ${len(params)-1}::timestamp with time zone)\n'
                          f'and (l.sequence {comp_rel}{"=" if allow_exact_ts_match else ""} ${len(params)}::integer)')

    if categ is not None:
        params.append(categ)
        wheres.append(f'and (m.category = ${len(params)})')
    if name is not None:
        params.append(name)
        wheres.append(f'and (m.data_id = ${len(params)})')
    if val is not None:
        wheres.append('and ((0=1)')
        for vi in val:
            if rel not in ('*=','*!='):
                try:
                    params.append(float(vi))
                    wheres.append(f'      or ((m.category = \'SAMPLE\') and (l.value_num '
                                  f'{srel.replace("<val>",f"${len(params)}::double precision")}))')
                except ValueError:
                    pass
            params.append(vi)
            wheres.append(f'      or ((m.category = \'EVENT\') and (l.value_text {srel.replace("<val>",f"${len(params)}")}))')
            params.append(vi)
            wheres.append(f'      or ((m.category = \'CONDITION\') and (l.value_text = ${len(params)}))')
        wheres.append('    )')
    if extra is not None:
        params.append(extra)
        wheres.append(f'and ((m.category = \'CONDITION\') and (l.value_extra {srel.replace("<val>",f"${len(params)}")}))')

    sql = view_find_sql.replace("<rank_direction>", rank_direction)\
                       .replace("<wheres>", '\n'.join(wheres)) \
                       .replace("<count>", str(count))

    return sql



async def get_find(credentials, device, timestamp=None, sequence=None, before_count=None, after_count=None, categ=None,
                   data_id=None, val=None, extra=None, rel=None, *, pconn=None) -> List[DataPoint]:
    if sequence is not None and timestamp is None:
        raise I4cClientError("sequence allowed only when timestamp is not empty")

    params = [device]
    sql = get_find_sql(params, timestamp, sequence, before_count, after_count, categ, data_id, val, extra, rel)
    write_debug_sql('get_find.sql', sql, *params)

    async with DatabaseConnection(pconn) as conn:
        log.debug('before sql run')
        rs = await conn.fetch(sql,*params)
        log.debug('after sql run')
    return [DataPoint(**r) for r in asyncpg_rows_process_json(rs, 'value_add')]
