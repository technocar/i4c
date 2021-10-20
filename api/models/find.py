from datetime import datetime
from typing import Optional

import asyncpg
from fastapi import HTTPException
from common import MyBaseModel, dbcfg, write_debug_sql

view_find_sql = open("models\\find.sql").read()


class DataPoint(MyBaseModel):
    timestamp: datetime
    sequence: int
    device: str
    data_id: str
    value_num: Optional[float]
    value_text: Optional[str]
    value_extra: Optional[str]
    value_add: Optional[str]


def get_find_sql(params, timestamp, sequence, before_count, after_count, categ, name, val, extra, rel):
    wheres = []
    rank_direction = 'desc'
    count = None
    if rel is None:
        rel = '='
    if rel not in ('=','<','>','<=','>=','!=','*=','*!='):
        raise HTTPException(status_code=400, detail=f"Invalid rel parameter")
    if rel == '*=':
        srel = 'like \'%\'||<val>||\'%\''
    elif rel == '*!=':
        srel = 'not like \'%\'||<val>||\'%\''
    else:
        srel = rel + " <val>"

    if before_count is None and after_count is None:
        before_count = 1

    if before_count is not None and after_count is not None:
        sql_before = get_find_sql(params, timestamp, sequence, before_count, None, categ, name, val, extra, rel)
        sql_after = get_find_sql(params, timestamp, sequence, None, after_count, categ, name, val, extra, rel)
        return f'with before as ({sql_before}), '\
               f'after as ({sql_after}) ' \
               f'select * from before ' \
               f'union all ' \
               f'select * from after ' \
               f'order by timestamp desc, "sequence" desc'

    if before_count is not None:
        count = before_count
        if timestamp is not None:
            params.append(timestamp)
            wheres.append(f'and {"( " if sequence is not None else ""}(l.timestamp < ${len(params)}::timestamp with time zone)')
            if sequence is not None:
                params.append(timestamp)
                params.append(sequence)
                wheres.append(f'      or ((l.timestamp = ${len(params)-1}::timestamp with time zone)'
                              f'           and (l.sequence < ${len(params)}::timestamp)))')
    if after_count is not None:
        rank_direction = 'asc'
        count = after_count
        if timestamp is not None:
            params.append(timestamp)
            wheres.append(f'and {"( " if sequence is not None else ""}(l.timestamp > ${len(params)}::timestamp with time zone)')
            if sequence is not None:
                params.append(timestamp)
                params.append(sequence)
                wheres.append(f'      or ((l.timestamp = ${len(params)-1}::timestamp with time zone)'
                              f'           and (l.sequence > ${len(params)}::timestamp)))')
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



async def get_find(credentials, device, timestamp, sequence, before_count, after_count, categ, name, val, extra, rel, *, pconn=None):
    params = [device]

    sql = get_find_sql(params, timestamp, sequence, before_count, after_count, categ, name, val, extra, rel)

    write_debug_sql('debug\\debug_get_find.sql', sql, params)

    try:
        conn = await asyncpg.connect(**dbcfg, user=credentials.username, password=credentials.password) if pconn is None else pconn
        rs = await conn.fetch(sql,*params)
        if pconn is None:
            await conn.close()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Sql error: {e}")

    if rs is None:
        raise HTTPException(status_code=404, detail="No log record found")
    return rs
