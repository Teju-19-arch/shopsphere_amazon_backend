from fastapi import APIRouter, Depends, Query
from ..schemas import RecommendationIn
from ..store import read, insert, next_id, get_by_id
from ..security import current_user, admin_user
from ..rag.engine import rag_recommend

router = APIRouter()


@router.get('/')
def get_recommendations(user=Depends(current_user), q: str = Query(default='', description='Optional natural-language shopping request')):
    # RAG is now the default recommendation path. The admin-created recommendation
    # endpoint below is retained for backward compatibility with the original API.
    result = rag_recommend(user['id'], q, top_k=10)
    return result


@router.get('/rag')
def rag_search(
    q: str = Query(default='', description='Natural-language shopping request'),
    top_k: int = Query(default=5, ge=1, le=20),
    user=Depends(current_user),
):
    """Retrieve relevant catalog context and generate a grounded recommendation."""
    return rag_recommend(user['id'], q, top_k=top_k)


@router.post('/')
def create_recommendation(payload: RecommendationIn, user_id: int, _=Depends(admin_user)):
    rec = {
        'id': next_id('recommendations', nosql=True), 'user_id': user_id,
        'product_ids': payload.product_ids, 'reason': payload.reason,
    }
    insert('recommendations', rec, nosql=True)
    return rec
