from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from ..schemas import CheckoutIn, ShipmentStatusIn
from ..store import read, write, insert, next_id, get_by_id, update_by_id
from ..security import current_user, admin_user

router = APIRouter()


def _cart_for(user_id: int):
    return next((c for c in read('carts') if c.get('user_id') == user_id), None)


@router.post('/checkout')
def checkout(payload: CheckoutIn, user=Depends(current_user)):
    cart = _cart_for(user['id'])
    if not cart or not cart.get('items'):
        raise HTTPException(status_code=400, detail='Cart is empty')

    address = get_by_id('addresses', payload.address_id)
    if not address or address.get('user_id') != user['id']:
        raise HTTPException(status_code=404, detail='Address not found')

    products = {p['id']: p for p in read('products')}
    inventory_rows = read('inventory')
    inv_by_product = {i['product_id']: i for i in inventory_rows}

    line_items = []
    subtotal = 0.0
    for item in cart['items']:
        product = products.get(item['product_id'])
        if not product or not product.get('active', True):
            raise HTTPException(status_code=400, detail=f"Product {item['product_id']} is unavailable")
        inv = inv_by_product.get(item['product_id'])
        available = inv['available'] if inv else product.get('stock', 0)
        if available < item['quantity']:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product['name']}")
        line_total = product['price'] * item['quantity']
        subtotal += line_total
        line_items.append({'product_id': product['id'], 'name': product['name'], 'price': product['price'], 'quantity': item['quantity'], 'line_total': line_total})

    discount = 0.0
    coupon = None
    if payload.coupon_code:
        coupons = read('coupons')
        coupon = next((c for c in coupons if c.get('code', '').upper() == payload.coupon_code.upper() and c.get('active', True)), None)
        if not coupon:
            raise HTTPException(status_code=400, detail='Invalid or inactive coupon')
        if subtotal < coupon.get('min_order_value', 0):
            raise HTTPException(status_code=400, detail=f"Order must be at least {coupon['min_order_value']} to use this coupon")
        if coupon.get('used_count', 0) >= coupon.get('max_uses', 0):
            raise HTTPException(status_code=400, detail='Coupon usage limit reached')
        discount = round(subtotal * coupon['discount_percent'] / 100, 2)

    total = round(subtotal - discount, 2)

    order = {
        'id': next_id('orders'), 'user_id': user['id'], 'address_id': address['id'],
        'subtotal': round(subtotal, 2), 'discount': discount, 'total': total,
        'coupon_code': payload.coupon_code, 'payment_method': payload.payment_method,
        'status': 'placed', 'created_at': datetime.now(timezone.utc).isoformat(),
    }
    insert('orders', order)

    for li in line_items:
        insert('order_items', {'id': next_id('order_items'), 'order_id': order['id'], **li})
        inv = inv_by_product.get(li['product_id'])
        if inv:
            inv['available'] = max(0, inv['available'] - li['quantity'])
            inv['updated_at'] = datetime.now(timezone.utc).isoformat()
        prod = products.get(li['product_id'])
        if prod:
            prod['stock'] = max(0, prod.get('stock', 0) - li['quantity'])
    write('inventory', inventory_rows)
    write('products', list(products.values()))

    insert('shipments', {
        'id': next_id('shipments'), 'order_id': order['id'], 'status': 'processing',
        'tracking_number': None, 'carrier': None, 'updated_at': datetime.now(timezone.utc).isoformat(),
    })

    if coupon:
        update_by_id('coupons', coupon['id'], {'used_count': coupon.get('used_count', 0) + 1})

    cart['items'] = []
    carts = read('carts')
    for i, c in enumerate(carts):
        if c['id'] == cart['id']:
            carts[i] = cart
    write('carts', carts)

    return {'order': order, 'items': line_items}


@router.get('/')
def list_orders(user=Depends(current_user)):
    orders = read('orders')
    if user.get('role') != 'admin':
        orders = [o for o in orders if o.get('user_id') == user['id']]
    return orders


@router.get('/{order_id}')
def get_order(order_id: int, user=Depends(current_user)):
    order = get_by_id('orders', order_id)
    if not order or (user.get('role') != 'admin' and order.get('user_id') != user['id']):
        raise HTTPException(status_code=404, detail='Order not found')
    items = [i for i in read('order_items') if i.get('order_id') == order_id]
    shipment = next((s for s in read('shipments') if s.get('order_id') == order_id), None)
    payment = next((p for p in read('payments') if p.get('order_id') == order_id), None)
    return {'order': order, 'items': items, 'shipment': shipment, 'payment': payment}


@router.put('/{order_id}/shipment')
def update_shipment(order_id: int, payload: ShipmentStatusIn, _=Depends(admin_user)):
    shipment = next((s for s in read('shipments') if s.get('order_id') == order_id), None)
    if not shipment:
        raise HTTPException(status_code=404, detail='Shipment not found')
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    updated = update_by_id('shipments', shipment['id'], updates)
    if payload.status == 'delivered':
        update_by_id('orders', order_id, {'status': 'delivered'})
    elif payload.status == 'shipped':
        update_by_id('orders', order_id, {'status': 'shipped'})
    return updated


@router.post('/{order_id}/cancel')
def cancel_order(order_id: int, user=Depends(current_user)):
    order = get_by_id('orders', order_id)
    if not order or (user.get('role') != 'admin' and order.get('user_id') != user['id']):
        raise HTTPException(status_code=404, detail='Order not found')
    if order.get('status') in ('shipped', 'delivered', 'cancelled'):
        raise HTTPException(status_code=400, detail=f"Cannot cancel an order that is {order.get('status')}")
    return update_by_id('orders', order_id, {'status': 'cancelled'})
