import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from ..schemas import PaymentIn
from ..store import read, insert, next_id, get_by_id, update_by_id
from ..security import current_user

router = APIRouter()


@router.post('/')
def create_payment(payload: PaymentIn, user=Depends(current_user)):
    order = get_by_id('orders', payload.order_id)
    if not order or (user.get('role') != 'admin' and order.get('user_id') != user['id']):
        raise HTTPException(status_code=404, detail='Order not found')
    existing = next((p for p in read('payments') if p.get('order_id') == payload.order_id and p.get('status') == 'success'), None)
    if existing:
        raise HTTPException(status_code=400, detail='Order already paid')

    payment = {
        'id': next_id('payments'), 'order_id': payload.order_id, 'method': payload.method,
        'amount': order['total'], 'status': 'success', 'transaction_id': f'TXN{uuid.uuid4().hex[:12].upper()}',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    insert('payments', payment)
    update_by_id('orders', payload.order_id, {'status': 'paid'})
    return payment


@router.get('/{payment_id}')
def get_payment(payment_id: int, user=Depends(current_user)):
    payment = get_by_id('payments', payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail='Payment not found')
    order = get_by_id('orders', payment['order_id'])
    if user.get('role') != 'admin' and (not order or order.get('user_id') != user['id']):
        raise HTTPException(status_code=404, detail='Payment not found')
    return payment
