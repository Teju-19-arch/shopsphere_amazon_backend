from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from ..schemas import ReviewIn
from ..store import read, write, insert, next_id, get_by_id, delete_by_id
from ..security import current_user

router = APIRouter()


@router.post('/')
def create_review(payload: ReviewIn, user=Depends(current_user)):
    if not get_by_id('products', payload.product_id):
        raise HTTPException(status_code=404, detail='Product not found')
    reviews = read('reviews', nosql=True)
    existing = next((r for r in reviews if r.get('product_id') == payload.product_id and r.get('user_id') == user['id']), None)
    if existing:
        raise HTTPException(status_code=400, detail='You have already reviewed this product')
    review = {
        'id': next_id('reviews', nosql=True), 'product_id': payload.product_id, 'user_id': user['id'],
        'user_name': user.get('name'), 'rating': payload.rating, 'title': payload.title,
        'comment': payload.comment, 'created_at': datetime.now(timezone.utc).isoformat(),
    }
    insert('reviews', review, nosql=True)
    return review


@router.get('/product/{product_id}')
def list_reviews(product_id: int):
    reviews = [r for r in read('reviews', nosql=True) if r.get('product_id') == product_id]
    avg = round(sum(r['rating'] for r in reviews) / len(reviews), 2) if reviews else None
    return {'average_rating': avg, 'count': len(reviews), 'reviews': reviews}


@router.delete('/{review_id}')
def delete_review(review_id: int, user=Depends(current_user)):
    review = get_by_id('reviews', review_id, nosql=True)
    if not review or (user.get('role') != 'admin' and review.get('user_id') != user['id']):
        raise HTTPException(status_code=404, detail='Review not found')
    delete_by_id('reviews', review_id, nosql=True)
    return {'deleted': True}
