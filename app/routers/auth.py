from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from ..schemas import RegisterIn, LoginIn
from ..store import read, insert, next_id
from ..security import hash_password, verify_password, create_token, current_user

router = APIRouter()


def _public(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != 'password_hash'}


@router.post('/register')
def register(payload: RegisterIn):
    existing = [u for u in read('users') if u.get('email', '').lower() == payload.email.lower()]
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')
    user = {
        'id': next_id('users'),
        'name': payload.name,
        'email': payload.email,
        'password_hash': hash_password(payload.password),
        'phone': payload.phone,
        'role': 'customer',
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    insert('users', user)
    token = create_token(user['id'], user['role'])
    return {'access_token': token, 'token_type': 'bearer', 'user': _public(user)}


@router.post('/login')
def login(payload: LoginIn):
    user = next((u for u in read('users') if u.get('email', '').lower() == payload.email.lower()), None)
    if not user or not verify_password(payload.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Invalid email or password')
    if user.get('status') != 'active':
        raise HTTPException(status_code=403, detail='Account is not active')
    token = create_token(user['id'], user['role'])
    return {'access_token': token, 'token_type': 'bearer', 'user': _public(user)}


@router.get('/me')
def me(user=Depends(current_user)):
    return _public(user)
