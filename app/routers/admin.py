from fastapi import APIRouter, HTTPException, Depends
from ..schemas import CouponIn
from ..store import read, insert, next_id, get_by_id, update_by_id, delete_by_id
from ..security import admin_user

router = APIRouter()


@router.get('/dashboard')
def dashboard(_=Depends(admin_user)):
    users = read('users')
    products = read('products')
    orders = read('orders')
    payments = read('payments')
    reviews = read('reviews', nosql=True)

    revenue = round(sum(p['amount'] for p in payments if p.get('status') == 'success'), 2)
    orders_by_status = {}
    for o in orders:
        orders_by_status[o.get('status', 'unknown')] = orders_by_status.get(o.get('status', 'unknown'), 0) + 1

    low_stock = [p for p in products if p.get('active', True) and p.get('stock', 0) <= 5]

    return {
        'total_users': len(users),
        'total_customers': len([u for u in users if u.get('role') == 'customer']),
        'total_products': len(products),
        'active_products': len([p for p in products if p.get('active', True)]),
        'total_orders': len(orders),
        'orders_by_status': orders_by_status,
        'total_revenue': revenue,
        'total_reviews': len(reviews),
        'low_stock_products': [{'id': p['id'], 'name': p['name'], 'stock': p['stock']} for p in low_stock],
    }


@router.get('/users')
def list_users(_=Depends(admin_user)):
    return [{k: v for k, v in u.items() if k != 'password_hash'} for u in read('users')]


@router.put('/users/{user_id}/status')
def set_user_status(user_id: int, status: str, _=Depends(admin_user)):
    updated = update_by_id('users', user_id, {'status': status})
    if not updated:
        raise HTTPException(status_code=404, detail='User not found')
    return {k: v for k, v in updated.items() if k != 'password_hash'}


# ---------- Coupons ----------
@router.get('/coupons')
def list_coupons(_=Depends(admin_user)):
    return read('coupons')


@router.post('/coupons')
def create_coupon(payload: CouponIn, _=Depends(admin_user)):
    coupon = payload.model_dump()
    coupon['id'] = next_id('coupons')
    coupon['used_count'] = 0
    coupon['code'] = coupon['code'].upper()
    insert('coupons', coupon)
    return coupon


@router.put('/coupons/{coupon_id}')
def update_coupon(coupon_id: int, payload: CouponIn, _=Depends(admin_user)):
    data = payload.model_dump()
    data['code'] = data['code'].upper()
    updated = update_by_id('coupons', coupon_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail='Coupon not found')
    return updated


@router.delete('/coupons/{coupon_id}')
def delete_coupon(coupon_id: int, _=Depends(admin_user)):
    if not delete_by_id('coupons', coupon_id):
        raise HTTPException(status_code=404, detail='Coupon not found')
    return {'deleted': True}
