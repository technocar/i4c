from typing import Dict, Set, Any, List, Union
from common import DatabaseConnection
import json


async def get_user_customer(user_id, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql = """select customer from "user" where "id" = $1"""
        res = await conn.fetchrow(sql, user_id)
        if not res:
            return None
        return res[0]


def dict2asyncpg_param(d: Dict[str,str]):
    # todo 5: maybe this can be done smarter
    return json.dumps(d)


def asyncpg_row_process_json(d: Dict[str,Any], json_fields: Union[str, Set[str]]):
    if not isinstance(json_fields, set):
        json_fields = set((json_fields, ))
    res = {k: (v if k not in json_fields else json.loads(v) if v is not None else None) for (k, v) in d.items()}
    return res


def asyncpg_rows_process_json(l: List[Dict[str,Any]], json_fields: Union[str, Set[str]]):
    return [asyncpg_row_process_json(r, json_fields) for r in l]
