from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from ..schemas import CartItemIn
from ..store import read, write, insert, next_id, get_by_id
from ..security import current_user

router = APIRouter()


def _get_or_create_cart(user_id: int) -> dict:
    carts = read('carts')
    cart = next((c for c in carts if c.get('user_id') == user_id), None)
    if cart:
        return cart
    cart = {'id': next_id('carts'), 'user_id': user_id, 'items': [], 'updated_at': datetime.now(timezone.utc).isoformat()}
    insert('carts', cart)
    return cart


def _save_cart(cart: dict):
    carts = read('carts')
    for i, c in enumerate(carts):
        if c['id'] == cart['id']:
            cart['updated_at'] = datetime.now(timezone.utc).isoformat()
            carts[i] = cart
            write('carts', carts)
            return
    insert('carts', cart)


def _enrich(cart: dict) -> dict:
    products = {p['id']: p for p in read('products')}
    lines = []
    subtotal = 0.0
    for item in cart.get('items', []):
        product = products.get(item['product_id'])
        if not product:
            continue
        line_total = product['price'] * item['quantity']
        subtotal += line_total
        lines.append({
            'product_id': item['product_id'], 'name': product['name'], 'price': product['price'],
            'quantity': item['quantity'], 'line_total': line_total, 'in_stock': product.get('stock', 0) >= item['quantity'],
        })
    return {'id': cart['id'], 'items': lines, 'subtotal': round(subtotal, 2)}


@router.get('/')
def get_cart(user=Depends(current_user)):
    return _enrich(_get_or_create_cart(user['id']))


@router.post('/items')
def add_item(payload: CartItemIn, user=Depends(current_user)):
    product = get_by_id('products', payload.product_id)
    if not product or not product.get('active', True):
        raise HTTPException(status_code=404, detail='Product not found')
    cart = _get_or_create_cart(user['id'])
    items = cart.get('items', [])
    existing = next((i for i in items if i['product_id'] == payload.product_id), None)
    if existing:
        existing['quantity'] += payload.quantity
    else:
        items.append({'product_id': payload.product_id, 'quantity': payload.quantity})
    cart['items'] = items
    _save_cart(cart)
    return _enrich(cart)


@router.put('/items/{product_id}')
def update_item(product_id: int, payload: CartItemIn, user=Depends(current_user)):
    cart = _get_or_create_cart(user['id'])
    items = cart.get('items', [])
    existing = next((i for i in items if i['product_id'] == product_id), None)
    if not existing:
        raise HTTPException(status_code=404, detail='Item not in cart')
    existing['quantity'] = payload.quantity
    cart['items'] = items
    _save_cart(cart)
    return _enrich(cart)


@router.delete('/items/{product_id}')
def remove_item(product_id: int, user=Depends(current_user)):
    cart = _get_or_create_cart(user['id'])
    cart['items'] = [i for i in cart.get('items', []) if i['product_id'] != product_id]
    _save_cart(cart)
    return _enrich(cart)


@router.delete('/')
def clear_cart(user=Depends(current_user)):
    cart = _get_or_create_cart(user['id'])
    cart['items'] = []
    _save_cart(cart)
    return _enrich(cart)
