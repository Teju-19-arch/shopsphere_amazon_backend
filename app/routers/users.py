from fastapi import APIRouter, HTTPException, Depends
from ..schemas import AddressIn
from ..store import read, write, insert, next_id, get_by_id, update_by_id, delete_by_id
from ..security import current_user

router = APIRouter()


def _public(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != 'password_hash'}


@router.get('/me')
def get_me(user=Depends(current_user)):
    return _public(user)


@router.put('/me')
def update_me(payload: dict, user=Depends(current_user)):
    allowed = {k: v for k, v in payload.items() if k in ('name', 'phone')}
    updated = update_by_id('users', user['id'], allowed)
    return _public(updated)


@router.get('/addresses')
def list_addresses(user=Depends(current_user)):
    return [a for a in read('addresses') if a.get('user_id') == user['id']]


@router.post('/addresses')
def add_address(payload: AddressIn, user=Depends(current_user)):
    addr = payload.model_dump()
    addr['id'] = next_id('addresses')
    addr['user_id'] = user['id']
    if addr.get('is_default'):
        rows = read('addresses')
        for a in rows:
            if a.get('user_id') == user['id']:
                a['is_default'] = False
        write('addresses', rows)
    insert('addresses', addr)
    return addr


@router.put('/addresses/{address_id}')
def update_address(address_id: int, payload: AddressIn, user=Depends(current_user)):
    existing = get_by_id('addresses', address_id)
    if not existing or existing.get('user_id') != user['id']:
        raise HTTPException(status_code=404, detail='Address not found')
    data = payload.model_dump()
    if data.get('is_default'):
        rows = read('addresses')
        for a in rows:
            if a.get('user_id') == user['id'] and a.get('id') != address_id:
                a['is_default'] = False
        write('addresses', rows)
    return update_by_id('addresses', address_id, data)


@router.delete('/addresses/{address_id}')
def delete_address(address_id: int, user=Depends(current_user)):
    existing = get_by_id('addresses', address_id)
    if not existing or existing.get('user_id') != user['id']:
        raise HTTPException(status_code=404, detail='Address not found')
    delete_by_id('addresses', address_id)
    return {'deleted': True}
