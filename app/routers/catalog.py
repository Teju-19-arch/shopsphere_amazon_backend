from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from ..schemas import CategoryIn, SellerIn, ProductIn, ProductUpdate
from ..store import read, write, insert, next_id, get_by_id, update_by_id, delete_by_id
from ..security import current_user, admin_user

router = APIRouter()


# ---------- Categories ----------
@router.get('/categories')
def list_categories():
    return read('categories')


@router.post('/categories')
def create_category(payload: CategoryIn, _=Depends(admin_user)):
    cat = payload.model_dump()
    cat['id'] = next_id('categories')
    insert('categories', cat)
    return cat


@router.put('/categories/{category_id}')
def update_category(category_id: int, payload: CategoryIn, _=Depends(admin_user)):
    updated = update_by_id('categories', category_id, payload.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail='Category not found')
    return updated


@router.delete('/categories/{category_id}')
def delete_category(category_id: int, _=Depends(admin_user)):
    if not delete_by_id('categories', category_id):
        raise HTTPException(status_code=404, detail='Category not found')
    return {'deleted': True}


# ---------- Sellers ----------
@router.get('/sellers')
def list_sellers():
    return read('sellers')


@router.post('/sellers')
def create_seller(payload: SellerIn, _=Depends(admin_user)):
    seller = payload.model_dump()
    seller['id'] = next_id('sellers')
    seller['status'] = 'active'
    insert('sellers', seller)
    return seller


# ---------- Products ----------
def _attach_metadata(product: dict) -> dict:
    meta = next((m for m in read('product_metadata', nosql=True) if m.get('product_id') == product['id']), None)
    out = dict(product)
    out['attributes'] = meta.get('attributes', {}) if meta else {}
    out['tags'] = meta.get('tags', []) if meta else []
    inv = next((i for i in read('inventory') if i.get('product_id') == product['id']), None)
    out['available_stock'] = inv.get('available', product.get('stock', 0)) if inv else product.get('stock', 0)
    return out


@router.get('/products')
def list_products(
    category_id: Optional[int] = None,
    seller_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    brand: Optional[str] = None,
    q: Optional[str] = Query(default=None, description='Search text'),
    active_only: bool = True,
):
    products = read('products')
    if active_only:
        products = [p for p in products if p.get('active', True)]
    if category_id is not None:
        products = [p for p in products if p.get('category_id') == category_id]
    if seller_id is not None:
        products = [p for p in products if p.get('seller_id') == seller_id]
    if min_price is not None:
        products = [p for p in products if p.get('price', 0) >= min_price]
    if max_price is not None:
        products = [p for p in products if p.get('price', 0) <= max_price]
    if brand:
        products = [p for p in products if (p.get('brand') or '').lower() == brand.lower()]
    if q:
        tokens = q.lower().split()
        index = read('search_index', nosql=True)
        matching_ids = {
            e['product_id'] for e in index
            if any(any(t in tok for tok in e.get('tokens', [])) for t in tokens)
        }
        products = [p for p in products if p['id'] in matching_ids]
    return [_attach_metadata(p) for p in products]


@router.get('/products/{product_id}')
def get_product(product_id: int):
    product = get_by_id('products', product_id)
    if not product:
        raise HTTPException(status_code=404, detail='Product not found')
    return _attach_metadata(product)


@router.post('/products')
def create_product(payload: ProductIn, user=Depends(current_user)):
    if user.get('role') not in ('admin', 'seller'):
        raise HTTPException(status_code=403, detail='Only admin or seller can create products')
    data = payload.model_dump()
    metadata = data.pop('metadata', {}) or {}
    product = {**data, 'id': next_id('products'), 'created_at': datetime.now(timezone.utc).isoformat()}
    insert('products', product)
    insert('inventory', {
        'id': next_id('inventory'), 'product_id': product['id'],
        'available': product.get('stock', 0), 'reserved': 0,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    })
    if metadata:
        insert('product_metadata', {
            'id': next_id('product_metadata', nosql=True), 'product_id': product['id'],
            'attributes': metadata, 'tags': [],
        }, nosql=True)
    tokens = (product['name'] + ' ' + product.get('description', '') + ' ' + str(product.get('brand', ''))).lower().split()
    insert('search_index', {'id': next_id('search_index', nosql=True), 'product_id': product['id'], 'tokens': tokens}, nosql=True)
    return _attach_metadata(product)


@router.put('/products/{product_id}')
def update_product(product_id: int, payload: ProductUpdate, user=Depends(current_user)):
    product = get_by_id('products', product_id)
    if not product:
        raise HTTPException(status_code=404, detail='Product not found')
    if user.get('role') != 'admin' and product.get('seller_id') != user.get('seller_id'):
        raise HTTPException(status_code=403, detail='Not authorized to edit this product')
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = update_by_id('products', product_id, updates)
    if 'stock' in updates:
        inv_rows = read('inventory')
        for inv in inv_rows:
            if inv.get('product_id') == product_id:
                inv['available'] = updates['stock']
                inv['updated_at'] = datetime.now(timezone.utc).isoformat()
        write('inventory', inv_rows)
    return _attach_metadata(updated)


@router.delete('/products/{product_id}')
def delete_product(product_id: int, _=Depends(admin_user)):
    if not delete_by_id('products', product_id):
        raise HTTPException(status_code=404, detail='Product not found')
    return {'deleted': True}
