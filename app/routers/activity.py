from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from ..store import read, write, insert, next_id
from ..security import current_user

router = APIRouter()


@router.post('/')
def log_activity(payload: dict, user=Depends(current_user)):
    entry = {
        'id': next_id('user_activity', nosql=True), 'user_id': user['id'],
        'action': payload.get('action', 'unknown'), 'product_id': payload.get('product_id'),
        'meta': payload.get('meta', {}), 'created_at': datetime.now(timezone.utc).isoformat(),
    }
    insert('user_activity', entry, nosql=True)
    return entry


@router.get('/')
def my_activity(user=Depends(current_user)):
    rows = [a for a in read('user_activity', nosql=True) if a.get('user_id') == user['id']]
    rows.sort(key=lambda a: a.get('created_at', ''), reverse=True)
    return rows


@router.get('/notifications')
def my_notifications(user=Depends(current_user)):
    rows = [n for n in read('notifications', nosql=True) if n.get('user_id') == user['id']]
    rows.sort(key=lambda n: n.get('created_at', ''), reverse=True)
    return rows


@router.put('/notifications/{notification_id}/read')
def mark_read(notification_id: int, user=Depends(current_user)):
    rows = read('notifications', nosql=True)
    for n in rows:
        if n.get('id') == notification_id and n.get('user_id') == user['id']:
            n['read'] = True
            write('notifications', rows, nosql=True)
            return n
    return {'error': 'Notification not found'}
