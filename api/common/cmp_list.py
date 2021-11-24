from typing import List, Any, Tuple


class Result:
    insert: List[Any]
    delete: List[Any]
    equal:  List[Any]
    update: List[Tuple[Any, Any]]

    def __iter__(self):
        return iter((self.insert, self.delete, self.equal, self.update))


def cmp_list(old_list, new_list, key=None):
    has_key = key is not None
    if not has_key:
        def key(x):
            return x

    old_list = list(old_list)
    new_list = list(new_list)

    upd_list = []
    eq_list = []

    oi = 0
    while oi < len(old_list):
        o = old_list[oi]
        ni, match_found = 0, False
        while ni < len(new_list):
            n = new_list[ni]
            if key(o) == key(n):
                if (not has_key) or (o == n):
                    eq_list.append(o)
                else:
                    upd_list.append((o,n))
                match_found = True
                del new_list[ni]
                del old_list[oi]
                break
            ni += 1
        if match_found:
            break
        oi += 1
    res = Result()
    res.insert = new_list
    res.delete = old_list
    res.update = upd_list
    res.equal = eq_list
    return res
