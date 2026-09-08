import json
from pathlib import Path
from threading import RLock
from typing import Any

BASE = Path(__file__).resolve().parent.parent
SQL_DIR = BASE / 'storage' / 'sql'
NOSQL_DIR = BASE / 'storage' / 'nosql'
LOCK = RLock()

SQL_COLLECTIONS = ['users','addresses','sellers','categories','products','inventory','carts','wishlists','orders','order_items','payments','shipments','coupons']
NOSQL_COLLECTIONS = ['product_metadata','reviews','recommendations','search_index','user_activity','notifications']


def ensure_storage():
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    NOSQL_DIR.mkdir(parents=True, exist_ok=True)
    for c in SQL_COLLECTIONS:
        p = SQL_DIR / f'{c}.json'
        if not p.exists(): p.write_text('[]', encoding='utf-8')
    for c in NOSQL_COLLECTIONS:
        p = NOSQL_DIR / f'{c}.json'
        if not p.exists(): p.write_text('[]', encoding='utf-8')


def path(collection: str, nosql=False) -> Path:
    ensure_storage()
    return (NOSQL_DIR if nosql else SQL_DIR) / f'{collection}.json'


def read(collection: str, nosql=False) -> list[dict[str, Any]]:
    with LOCK:
        try:
            data = json.loads(path(collection, nosql).read_text(encoding='utf-8'))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError):
            return []


def write(collection: str, rows: list[dict[str, Any]], nosql=False):
    with LOCK:
        p = path(collection, nosql)
        tmp = p.with_suffix('.tmp')
        tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        tmp.replace(p)


def next_id(collection: str, nosql=False) -> int:
    rows = read(collection, nosql)
    return max([int(x.get('id', 0)) for x in rows] or [0]) + 1


def insert(collection: str, item: dict, nosql=False):
    rows = read(collection, nosql)
    rows.append(item)
    write(collection, rows, nosql)
    return item


def get_by_id(collection: str, item_id: int, nosql=False):
    return next((x for x in read(collection, nosql) if int(x.get('id', -1)) == item_id), None)


def update_by_id(collection: str, item_id: int, updates: dict, nosql=False):
    rows = read(collection, nosql)
    for row in rows:
        if int(row.get('id', -1)) == item_id:
            row.update(updates)
            write(collection, rows, nosql)
            return row
    return None


def delete_by_id(collection: str, item_id: int, nosql=False):
    rows = read(collection, nosql)
    new = [x for x in rows if int(x.get('id', -1)) != item_id]
    if len(new) == len(rows): return False
    write(collection, new, nosql)
    return True
