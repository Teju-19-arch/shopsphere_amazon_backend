from __future__ import annotations

import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from ..store import read

TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9+.#-]*")
STOP_WORDS = {
    "the","and","for","with","from","this","that","you","your","are","want","need",
    "show","find","give","best","good","product","products","buy","like","under","above",
    "below","between","a","an","to","of","in","on","is","it","my","me","i","or","as",
    "at","by","be","can","all","please","looking","lookingfor","item","items","one","some",
}

# Common e-commerce concepts and synonyms. These are used for query understanding before retrieval.
CATEGORY_ALIASES = {
    "phone": {"phone","phones","smartphone","smartphones","mobile","mobiles","cellphone","iphone","android"},
    "laptop": {"laptop","laptops","notebook","notebooks","computer","computers"},
    "shoes": {"shoe","shoes","footwear","sneaker","sneakers","running"},
    "fashion": {"fashion","clothing","clothes","dress","shirts","shoes","accessories"},
    "electronics": {"electronics","electronic","gadget","gadgets","device","devices"},
    "home": {"home","kitchen","furniture","appliance","appliances"},
}
FEATURE_ALIASES = {
    "5g": {"5g","5g-ready","5gnetwork"},
    "gaming": {"gaming","gamer","games"},
    "student": {"student","students","college","school"},
    "android": {"android"},
    "windows": {"windows"},
    "ssd": {"ssd"},
    "amoled": {"amoled"},
}


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "") if t.lower() not in STOP_WORDS]


def _normalize(text: str) -> str:
    return " ".join(_tokens(text))


def _flatten_attributes(attrs: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in (attrs or {}).items():
        parts.append(str(key))
        if isinstance(value, (list, tuple, set)):
            parts.extend(map(str, value))
        else:
            parts.append(str(value))
    return " ".join(parts)


def _product_documents() -> list[dict[str, Any]]:
    products = {int(p["id"]): p for p in read("products") if p.get("active", True)}
    metadata = {int(m.get("product_id")): m for m in read("product_metadata", nosql=True) if m.get("product_id") is not None}
    categories = {int(c["id"]): c for c in read("categories") if c.get("id") is not None}
    reviews = defaultdict(list)
    for review in read("reviews", nosql=True):
        if review.get("product_id") is not None:
            reviews[int(review["product_id"])].append(review)

    docs = []
    for pid, product in products.items():
        meta = metadata.get(pid, {})
        attrs = meta.get("attributes", {}) or {}
        tags = meta.get("tags", []) or []
        category = categories.get(int(product.get("category_id", -1)), {}).get("name", "")
        product_reviews = reviews.get(pid, [])
        ratings = [float(r.get("rating", 0)) for r in product_reviews if r.get("rating") is not None]
        rating = sum(ratings) / len(ratings) if ratings else 0.0
        review_text = " ".join(f"{r.get('title','')} {r.get('comment','')}" for r in product_reviews)
        searchable = " ".join([
            str(product.get("name", "")), str(product.get("description", "")), str(product.get("brand", "")),
            category, " ".join(map(str, tags)), _flatten_attributes(attrs), review_text,
        ])
        docs.append({
            "product": product,
            "text": searchable,
            "tokens": Counter(_tokens(searchable)),
            "normalized": _normalize(searchable),
            "name_tokens": set(_tokens(str(product.get("name", "")))),
            "brand_tokens": set(_tokens(str(product.get("brand", "")))),
            "category": category.lower(),
            "tags": {str(x).lower() for x in tags},
            "attributes": {str(k).lower(): str(v).lower() for k, v in attrs.items()},
            "rating": rating,
            "review_count": len(product_reviews),
        })
    return docs


def _cosine(query_tokens: Counter, doc_tokens: Counter) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    common = set(query_tokens) & set(doc_tokens)
    dot = sum(query_tokens[t] * doc_tokens[t] for t in common)
    qn = math.sqrt(sum(v * v for v in query_tokens.values()))
    dn = math.sqrt(sum(v * v for v in doc_tokens.values()))
    return dot / (qn * dn) if qn and dn else 0.0


def _user_profile(user_id: int) -> tuple[Counter, set[int], list[str]]:
    products = {int(p["id"]): p for p in read("products")}
    metadata = {int(m.get("product_id")): m for m in read("product_metadata", nosql=True) if m.get("product_id") is not None}
    profile_tokens: Counter = Counter()
    seen: set[int] = set()
    reasons: list[str] = []

    def add_product(pid: int, weight: int, reason: str):
        product = products.get(pid)
        if not product:
            return
        seen.add(pid)
        meta = metadata.get(pid, {})
        text = " ".join([
            str(product.get("name", "")), str(product.get("description", "")), str(product.get("brand", "")),
            " ".join(map(str, meta.get("tags", []) or [])), _flatten_attributes(meta.get("attributes", {}) or {}),
        ])
        profile_tokens.update({t: weight for t in _tokens(text)})
        reasons.append(reason)

    for activity in read("user_activity", nosql=True):
        if int(activity.get("user_id", -1)) != user_id or not activity.get("product_id"):
            continue
        action = str(activity.get("action", "view")).lower()
        weight = {"purchase":5,"order":5,"wishlist":4,"add_to_cart":4,"cart":3,"view":1,"search":1}.get(action,1)
        add_product(int(activity["product_id"]), weight, action)

    wishlist = next((w for w in read("wishlists") if int(w.get("user_id", -1)) == user_id), None)
    for pid in (wishlist or {}).get("product_ids", []):
        add_product(int(pid), 4, "wishlist")

    orders = [o for o in read("orders") if int(o.get("user_id", -1)) == user_id]
    order_ids = {int(o["id"]) for o in orders if o.get("id") is not None}
    for item in read("order_items"):
        if int(item.get("order_id", -1)) in order_ids and item.get("product_id"):
            add_product(int(item["product_id"]), 5, "purchase")

    for review in read("reviews", nosql=True):
        if int(review.get("user_id", -1)) == user_id and float(review.get("rating", 0)) >= 4 and review.get("product_id"):
            add_product(int(review["product_id"]), 5, "positive review")

    return profile_tokens, seen, reasons


def _parse_query(query: str) -> dict[str, Any]:
    q = (query or "").lower().strip()
    tokens = set(_tokens(q))
    parsed: dict[str, Any] = {"tokens": tokens, "brands": set(), "categories": set(), "features": set(), "max_price": None, "min_price": None}

    # Known brand extraction from the actual catalog prevents hard-coding brand names.
    for p in read("products"):
        brand = str(p.get("brand", "")).strip().lower()
        if brand and (brand in q or brand in tokens):
            parsed["brands"].add(brand)

    for category, aliases in CATEGORY_ALIASES.items():
        if tokens & aliases:
            parsed["categories"].add(category)
    for feature, aliases in FEATURE_ALIASES.items():
        if tokens & aliases:
            parsed["features"].add(feature)

    price_patterns = [
        ("max", r"(?:under|below|less than|upto|up to|within)\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)"),
        ("min", r"(?:above|over|more than|greater than)\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)"),
    ]
    for kind, pattern in price_patterns:
        m = re.search(pattern, q)
        if m:
            value = float(m.group(1).replace(",", ""))
            if kind == "max": parsed["max_price"] = value
            else: parsed["min_price"] = value
    return parsed


def _category_match(doc: dict[str, Any], categories: set[str]) -> bool:
    if not categories:
        return False
    text = f"{doc['category']} {doc['normalized']}"
    for category in categories:
        aliases = CATEGORY_ALIASES.get(category, {category})
        if any(alias in doc["tags"] or alias in text for alias in aliases):
            return True
    return False


def _feature_match(doc: dict[str, Any], feature: str) -> bool:
    haystack = doc["normalized"]
    aliases = FEATURE_ALIASES.get(feature, {feature})
    return any(a in doc["tags"] or a in haystack for a in aliases)


def _retrieve(user_id: int, query: str, top_k: int) -> list[dict[str, Any]]:
    docs = _product_documents()
    profile, seen, _ = _user_profile(user_id)
    parsed = _parse_query(query)
    query_tokens = Counter(parsed["tokens"])

    # Profile context is deliberately low-weight so it cannot overpower an explicit request.
    if profile and not query.strip():
        query_tokens.update({t: min(c, 4) * 0.6 for t, c in profile.most_common(40)})

    ranked: list[tuple[float, dict[str, Any]]] = []
    constrained = bool(parsed["brands"] or parsed["categories"] or parsed["features"] or parsed["max_price"] is not None or parsed["min_price"] is not None)

    for doc in docs:
        p = doc["product"]
        score = _cosine(query_tokens, doc["tokens"])
        reasons: list[str] = []

        # Exact/name/brand matches carry much more weight than generic lexical overlap.
        name_lower = str(p.get("name", "")).lower()
        brand_lower = str(p.get("brand", "")).lower()
        if parsed["brands"]:
            if brand_lower in parsed["brands"]:
                score += 0.55; reasons.append("brand")
            else:
                score -= 0.45
        if parsed["categories"]:
            if _category_match(doc, parsed["categories"]):
                score += 0.45; reasons.append("category")
            else:
                score -= 0.40
        for feature in parsed["features"]:
            if _feature_match(doc, feature):
                score += 0.35; reasons.append(feature)
            else:
                score -= 0.30

        # Phrase/name matches help short product queries.
        for token in parsed["tokens"]:
            if token in doc["name_tokens"]:
                score += 0.12
        if parsed["brands"] and any(b in name_lower for b in parsed["brands"]):
            score += 0.08

        price = float(p.get("price", 0) or 0)
        if parsed["max_price"] is not None:
            if price <= parsed["max_price"]:
                score += 0.22; reasons.append("within budget")
            else:
                score -= 0.65
        if parsed["min_price"] is not None:
            if price >= parsed["min_price"]:
                score += 0.12
            else:
                score -= 0.50

        # Quality signals are tie-breakers, not substitutes for relevance.
        score += min(doc["rating"] / 5.0, 1.0) * 0.10
        score += min(float(p.get("stock", 0)) / 100.0, 1.0) * 0.02
        if p["id"] in seen and query.strip():
            score += 0.02  # familiarity is useful, but tiny compared with explicit intent

        # Hard constraints: if the query explicitly specifies a brand/category/feature/budget,
        # unrelated products should not fill the top-k list merely because they share a word.
        valid = True
        if parsed["brands"] and brand_lower not in parsed["brands"]:
            valid = False
        if parsed["categories"] and not _category_match(doc, parsed["categories"]):
            valid = False
        if parsed["max_price"] is not None and price > parsed["max_price"]:
            valid = False
        if parsed["min_price"] is not None and price < parsed["min_price"]:
            valid = False
        if any(not _feature_match(doc, f) for f in parsed["features"]):
            valid = False

        if valid or not constrained:
            doc_copy = dict(doc)
            doc_copy["match_reasons"] = reasons
            ranked.append((score, doc_copy))

    ranked.sort(key=lambda x: (x[0], x[1]["rating"], x[1]["product"].get("stock", 0)), reverse=True)

    # If a constrained query has no exact candidates, relax only the least important feature,
    # never the explicit brand or budget. This keeps the endpoint useful on small catalogs.
    if not ranked and constrained:
        relaxed: list[tuple[float, dict[str, Any]]] = []
        for doc in docs:
            p = doc["product"]
            brand_ok = not parsed["brands"] or str(p.get("brand", "")).lower() in parsed["brands"]
            price_ok = parsed["max_price"] is None or float(p.get("price", 0) or 0) <= parsed["max_price"]
            min_ok = parsed["min_price"] is None or float(p.get("price", 0) or 0) >= parsed["min_price"]
            if brand_ok and price_ok and min_ok:
                relaxed_score = _cosine(query_tokens, doc["tokens"]) + min(doc["rating"] / 5.0, 1.0) * 0.1
                relaxed.append((relaxed_score, doc))
        ranked = sorted(relaxed, key=lambda x: x[0], reverse=True)

    results = []
    for score, doc in ranked[:max(top_k, 1)]:
        p = doc["product"]
        results.append({
            **p,
            "rag_score": round(float(score), 4),
            "retrieval_rating": round(float(doc["rating"]), 2),
            "retrieval_review_count": doc["review_count"],
            "match_reasons": doc.get("match_reasons", []),
        })
    return results


def _fallback_generation(query: str, products: list[dict[str, Any]], reasons: list[str]) -> str:
    if not products:
        return "I could not find a suitable active product matching your request in the current ShopSphere catalog."
    if query.strip():
        details = []
        for p in products[:3]:
            price = p.get("price")
            rating = p.get("retrieval_rating", 0)
            detail = f"{p.get('name', 'this product')}"
            if price is not None: detail += f" (₹{float(price):,.0f}"
            else: detail += " ("
            if rating: detail += f", {rating:.1f}/5"
            detail += ")"
            details.append(detail)
        return f"For '{query}', the most relevant matches are " + ", ".join(details) + ". These results are grounded in the ShopSphere catalog and ranked using query intent, product metadata, reviews, price and availability."
    names = [p.get("name", "this product") for p in products[:3]]
    intro = "Based on your recent activity, wishlist, purchases and reviews," if reasons else "Based on the current ShopSphere catalog,"
    return f"{intro} the strongest matches are {', '.join(names)}."


def _gemini_generation(query: str, products: list[dict[str, Any]], profile_summary: list[str]) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        context = [{
            "id": p.get("id"), "name": p.get("name"), "description": p.get("description"), "brand": p.get("brand"),
            "price": p.get("price"), "rating": p.get("retrieval_rating"), "stock": p.get("stock"),
            "match_reasons": p.get("match_reasons", []), "tags": p.get("tags", []), "attributes": p.get("attributes", {}),
        } for p in products]
        prompt = (
            "You are ShopSphere's recommendation assistant. Use ONLY the retrieved product context. "
            "Recommend up to 3 products. Explain briefly why each matches the request. Do not invent specifications, ratings, prices, or products. "
            f"User request: {query or 'personalized recommendations'}\n"
            f"Preference signals: {', '.join(profile_summary[:8]) or 'none'}\n"
            f"Retrieved context: {json.dumps(context, ensure_ascii=False)}"
        )
        response = client.models.generate_content(model=model, contents=prompt)
        text = getattr(response, "text", None)
        return text.strip() if text else None
    except Exception:
        return None


def rag_recommend(user_id: int, query: str = "", top_k: int = 5) -> dict[str, Any]:
    top_k = min(max(top_k, 1), 20)
    products = _retrieve(user_id, query, top_k)
    _, _, reasons = _user_profile(user_id)
    answer = _gemini_generation(query, products, reasons) or _fallback_generation(query, products, reasons)
    return {
        "mode": "rag",
        "query": query,
        "answer": answer,
        "products": products,
        "retrieved_count": len(products),
        "generated_with": "gemini" if (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) else "local_fallback",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
