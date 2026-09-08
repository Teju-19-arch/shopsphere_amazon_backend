import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .store import get_by_id

SECRET_KEY = os.getenv('SECRET_KEY', 'shopsphere-demo-secret-change-me')
ALGORITHM = 'HS256'
EXPIRE = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '1440'))
pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')
bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return pwd.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd.verify(password, hashed)

def create_token(user_id: int, role: str):
    payload = {'sub': str(user_id), 'role': role, 'exp': datetime.now(timezone.utc) + timedelta(minutes=EXPIRE)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication required')
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user = get_by_id('users', int(payload['sub']))
        if not user: raise ValueError()
        return user
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or expired token')

def admin_user(user=Depends(current_user)):
    if user.get('role') != 'admin': raise HTTPException(status_code=403, detail='Admin access required')
    return user
