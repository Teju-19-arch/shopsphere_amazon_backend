from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
r=c.get('/health'); assert r.status_code==200 and r.json()['storage']=='JSON'
r=c.post('/auth/login',json={'email':'admin@shopsphere.com','password':'Admin@123'}); assert r.status_code==200
t=r.json()['access_token']; h={'Authorization':f'Bearer {t}'}
r=c.get('/products',headers=h); assert r.status_code==200 and len(r.json())>=1
r=c.get('/admin/dashboard',headers=h); assert r.status_code==200
print('SMOKE TEST PASSED')
