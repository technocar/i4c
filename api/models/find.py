from datetime import datetime

import asyncpg
from fastapi import HTTPException
from common import MyBaseModel, dbcfg

view_find_sql = open("models\\find.sql").read()


class FindResult(MyBaseModel):
    timestamp: datetime


async def get_find(credentials, device, before, after, categ, name, val, extra, rel, *, pconn=None):
    wheres = []
    params = [device]
    rank_direction = 'desc'
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

    if categ is None and name is None:
        raise HTTPException(status_code=400, detail=f"categ or name parameter must be sent")

    if before is not None and after is not None:
        raise HTTPException(status_code=400, detail=f"before and after parameters exclude each other")

    if before is not None:
        params.append(before)
        wheres.append(f'and (l.timestamp <= ${len(params)}::timestamp with time zone)')
    if after is not None:
        params.append(after)
        wheres.append(f'and (l.timestamp >= ${len(params)}::timestamp with time zone)')
        rank_direction = 'asc'
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
                       .replace("<wheres>", '\n'.join(wheres))

    try:
        conn = await asyncpg.connect(**dbcfg, user=credentials.username, password=credentials.password) if pconn is None else pconn
        rs = await conn.fetchrow(sql,*params)
        if pconn is None:
            await conn.close()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Sql error: {e}")

    if rs is None:
        raise HTTPException(status_code=404, detail="No log record found")
    return rs
