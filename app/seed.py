from datetime import datetime, timezone
from .store import ensure_storage, read, write, insert, next_id
from .security import hash_password

def seed():
    ensure_storage()
    if not read('users'):
        insert('users', {'id':1,'name':'ShopSphere Admin','email':'admin@shopsphere.com','password_hash':hash_password('Admin@123'),'phone':'9999999999','role':'admin','status':'active','created_at':datetime.now(timezone.utc).isoformat()})
        insert('users', {'id':2,'name':'Demo Customer','email':'customer@shopsphere.com','password_hash':hash_password('Customer@123'),'phone':'8888888888','role':'customer','status':'active','created_at':datetime.now(timezone.utc).isoformat()})
    if not read('categories'):
        write('categories', [
            {'id':1,'name':'Electronics','description':'Phones, laptops and electronics','parent_id':None},
            {'id':2,'name':'Fashion','description':'Clothing, shoes and accessories','parent_id':None},
            {'id':3,'name':'Home','description':'Home and kitchen products','parent_id':None},
        ])
    if not read('sellers'):
        write('sellers', [{'id':1,'name':'ShopSphere Retail','email':'seller@shopsphere.com','phone':'7777777777','status':'active'}])
    if not read('products'):
        products=[
            {'id':1,'name':'Samsung Galaxy S25','description':'Premium 5G smartphone','category_id':1,'seller_id':1,'price':74999,'mrp':84999,'sku':'SAM-S25-256','brand':'Samsung','image_url':'','stock':25,'active':True,'created_at':datetime.now(timezone.utc).isoformat()},
            {'id':2,'name':'HP Pavilion 14','description':'14-inch performance laptop','category_id':1,'seller_id':1,'price':65999,'mrp':72999,'sku':'HP-PAV14-I5','brand':'HP','image_url':'','stock':15,'active':True,'created_at':datetime.now(timezone.utc).isoformat()},
            {'id':3,'name':'Running Shoes','description':'Lightweight everyday running shoes','category_id':2,'seller_id':1,'price':2499,'mrp':3999,'sku':'RUN-SHOE-01','brand':'ShopSphere','image_url':'','stock':50,'active':True,'created_at':datetime.now(timezone.utc).isoformat()},
        ]
        write('products', products)
        write('inventory', [{'id':i+1,'product_id':p['id'],'available':p['stock'],'reserved':0,'updated_at':datetime.now(timezone.utc).isoformat()} for i,p in enumerate(products)])
        write('product_metadata', [
            {'id':1,'product_id':1,'attributes':{'display':'6.2 inch AMOLED','ram':'12GB','storage':'256GB','camera':'50MP','network':'5G'},'tags':['smartphone','android','5g','samsung']},
            {'id':2,'product_id':2,'attributes':{'processor':'Intel Core i5','ram':'16GB','storage':'512GB SSD','display':'14 inch','os':'Windows 11'},'tags':['laptop','hp','student','windows']},
            {'id':3,'product_id':3,'attributes':{'sizes':['7','8','9','10'],'material':'Mesh','gender':'Unisex'},'tags':['shoes','running','sports']},
        ], nosql=True)
        write('search_index', [{'id':i+1,'product_id':p['id'],'tokens':(p['name']+' '+p['description']+' '+str(p.get('brand',''))).lower().split()} for i,p in enumerate(products)], nosql=True)
