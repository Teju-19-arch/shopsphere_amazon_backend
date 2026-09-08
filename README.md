# ShopSphere Amazon-Style E-Commerce Backend

A complete FastAPI e-commerce backend designed for learning/demo use. It uses **JSON files as the physical persistence layer**, while separating data into **SQL-style structured JSON** and **NoSQL-style document JSON**.

## Architecture

- SQL-style JSON: users, addresses, sellers, categories, products, inventory, carts, orders, order_items, payments, shipments, coupons.
- NoSQL-style JSON: product_metadata, reviews, recommendations, search_index, user_activity, notifications.
- FastAPI REST API with Swagger docs.
- JWT authentication and bcrypt password hashing.
- Search, filters, cart, checkout, payment simulation, shipping, reviews, wishlist, recommendations, coupons, admin dashboard.

> This is not a real PostgreSQL/MongoDB deployment. The project deliberately stores everything in JSON so you can inspect the files directly. The SQL/NoSQL split is represented by separate JSON collections and relational IDs.

## Run on Windows PowerShell

```powershell
cd shopsphere_amazon_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000/docs

## Quick test

1. `POST /auth/register`
2. `POST /auth/login` and copy the token.
3. Click **Authorize** in Swagger and enter `Bearer YOUR_TOKEN`.
4. Create/list products, add to cart, checkout, create payment, update shipment, add review.
5. Inspect `storage/sql/*.json` and `storage/nosql/*.json`.

A demo admin account is seeded:
- email: `admin@shopsphere.com`
- password: `Admin@123`

Change this before real deployment.

## RAG Recommendation System

The recommendation API now uses a Retrieval-Augmented Generation (RAG) pipeline:

1. **Ingestion/context** — products, descriptions, brands, metadata/tags and review text are treated as the knowledge base.
2. **User context** — views/activity, wishlist items, purchases and positive reviews are used to build a preference profile.
3. **Retrieval** — ShopSphere ranks catalog documents using token/cosine similarity plus price, rating, stock and personalization signals.
4. **Generation** — if `GEMINI_API_KEY` is configured, Gemini generates a concise grounded explanation from only the retrieved products. Without a key, a deterministic local generator is used, so the API still works offline.

### RAG endpoints

- `GET /recommendations/` — personalized RAG recommendations.
- `GET /recommendations/rag?q=gaming laptop under 70000&top_k=5` — natural-language RAG search + recommendation.

### Enable Gemini generation (optional)

Copy `.env.example` to `.env`, set `GEMINI_API_KEY`, then restart the server. The backend remains fully usable without the key.
