# ShopSphere RAG

This module implements the recommendation pipeline without requiring a vector database.

- Knowledge base: products + metadata/tags + reviews.
- User context: activity + wishlist + orders + positive reviews.
- Retrieval: lightweight token/cosine similarity with personalization, price, rating and stock signals.
- Generation: Gemini when `GEMINI_API_KEY` is present; otherwise a grounded local fallback.

This keeps the existing JSON SQL-style/NoSQL-style storage and API intact while adding a real retrieval + generation layer.
