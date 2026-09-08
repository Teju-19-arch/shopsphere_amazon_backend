import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .store import ensure_storage
from .seed import seed
from .routers import auth, catalog, cart, orders, payments, reviews, admin, users, wishlist, recommendations, activity

ensure_storage(); seed()
app = FastAPI(title='ShopSphere Amazon-Style E-Commerce API', version='1.0.0', description='Hybrid SQL-style and NoSQL-style JSON persistence for a full e-commerce backend.')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.include_router(auth.router, prefix='/auth', tags=['Authentication'])
app.include_router(users.router, prefix='/users', tags=['Users & Addresses'])
app.include_router(catalog.router, tags=['Catalog'])
app.include_router(cart.router, prefix='/cart', tags=['Cart'])
app.include_router(wishlist.router, prefix='/wishlist', tags=['Wishlist'])
app.include_router(orders.router, prefix='/orders', tags=['Orders & Checkout'])
app.include_router(payments.router, prefix='/payments', tags=['Payments'])
app.include_router(reviews.router, prefix='/reviews', tags=['Reviews'])
app.include_router(recommendations.router, prefix='/recommendations', tags=['Recommendations'])
app.include_router(admin.router, prefix='/admin', tags=['Admin'])
app.include_router(activity.router, prefix='/activity', tags=['Activity'])

@app.get('/')
def root(): return {'name':'ShopSphere','status':'running','docs':'/docs','storage':{'sql_style':'storage/sql/*.json','nosql_style':'storage/nosql/*.json'}}
@app.get('/health')
def health(): return {'status':'healthy','storage':'JSON','sql_style':'ready','nosql_style':'ready'}
