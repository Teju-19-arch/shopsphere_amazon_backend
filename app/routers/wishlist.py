from fastapi import APIRouter, HTTPException, Depends
from ..schemas import WishlistIn
from ..store import read, write, insert, next_id, get_by_id
from ..security import current_user

router = APIRouter()


def _get_or_create(user_id: int) -> dict:
    rows = read('wishlists')
    row = next((w for w in rows if w.get('user_id') == user_id), None)
    if row:
        return row
    row = {'id': next_id('wishlists'), 'user_id': user_id, 'product_ids': []}
    insert('wishlists', row)
    return row


def _save(row: dict):
    rows = read('wishlists')
    for i, w in enumerate(rows):
        if w['id'] == row['id']:
            rows[i] = row
            write('wishlists', rows)
            return
    insert('wishlists', row)


def _enrich(row: dict) -> dict:
    products = {p['id']: p for p in read('products')}
    items = [products[pid] for pid in row.get('product_ids', []) if pid in products]
    return {'id': row['id'], 'items': items}


@router.get('/')
def get_wishlist(user=Depends(current_user)):
    return _enrich(_get_or_create(user['id']))


@router.post('/')
def add_to_wishlist(payload: WishlistIn, user=Depends(current_user)):
    if not get_by_id('products', payload.product_id):
        raise HTTPException(status_code=404, detail='Product not found')
    row = _get_or_create(user['id'])
    if payload.product_id not in row['product_ids']:
        row['product_ids'].append(payload.product_id)
    _save(row)
    return _enrich(row)


@router.delete('/{product_id}')
def remove_from_wishlist(product_id: int, user=Depends(current_user)):
    row = _get_or_create(user['id'])
    row['product_ids'] = [pid for pid in row['product_ids'] if pid != product_id]
    _save(row)
    return _enrich(row)
