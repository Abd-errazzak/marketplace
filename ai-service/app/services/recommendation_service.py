"""
Product recommendation service
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os
from datetime import datetime, timedelta

from app.core.config import settings


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.vector_db_path = settings.VECTOR_DB_PATH
        self._load_or_create_vector_db()
    
    def _load_or_create_vector_db(self):
        """Load or create vector database for product embeddings"""
        os.makedirs(self.vector_db_path, exist_ok=True)
        
        vector_file = os.path.join(self.vector_db_path, "product_embeddings.pkl")
        index_file = os.path.join(self.vector_db_path, "product_index.faiss")
        
        if os.path.exists(vector_file) and os.path.exists(index_file):
            # Load existing vector database
            with open(vector_file, 'rb') as f:
                self.product_embeddings = pickle.load(f)
            
            self.index = faiss.read_index(index_file)
        else:
            # Create new vector database
            self._build_vector_db()
    
    def _build_vector_db(self):
        """Build vector database from products"""
        # Get all active products
        from app.models.product import Product
        
        products = self.db.query(Product).filter(
            Product.status == "active"
        ).all()
        
        if not products:
            self.product_embeddings = {}
            self.index = None
            return
        
        # Create embeddings for products
        product_texts = []
        product_ids = []
        
        for product in products:
            # Combine title, description, and tags for embedding
            text = f"{product.title}"
            if product.description:
                text += f" {product.description}"
            if product.tags:
                text += f" {' '.join(product.tags)}"
            
            product_texts.append(text)
            product_ids.append(product.id)
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(product_texts)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        
        # Store product embeddings mapping
        self.product_embeddings = {pid: emb for pid, emb in zip(product_ids, embeddings)}
        
        # Save to disk
        self._save_vector_db()
    
    def _save_vector_db(self):
        """Save vector database to disk"""
        vector_file = os.path.join(self.vector_db_path, "product_embeddings.pkl")
        index_file = os.path.join(self.vector_db_path, "product_index.faiss")
        
        with open(vector_file, 'wb') as f:
            pickle.dump(self.product_embeddings, f)
        
        if self.index:
            faiss.write_index(self.index, index_file)
    
    async def get_user_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recommendations based on user's purchase history"""
        from app.models.order import Order, OrderItem
        from app.models.product import Product
        
        # Get user's purchase history
        purchased_products = self.db.query(Product.id).join(OrderItem).join(Order).filter(
            Order.buyer_id == user_id,
            Order.status.in_(["paid", "processing", "shipped", "delivered"])
        ).all()
        
        if not purchased_products:
            # If no purchase history, return popular products
            return await self.get_popular_products(limit)
        
        # Get similar products based on purchase history
        purchased_ids = [p.id for p in purchased_products]
        similar_products = []
        
        for product_id in purchased_ids:
            if product_id in self.product_embeddings:
                similar = await self.get_similar_products(product_id, limit=5)
                similar_products.extend(similar)
        
        # Remove duplicates and already purchased products
        seen = set(purchased_ids)
        unique_recommendations = []
        
        for rec in similar_products:
            if rec['product_id'] not in seen:
                unique_recommendations.append(rec)
                seen.add(rec['product_id'])
        
        return unique_recommendations[:limit]
    
    async def get_similar_products(self, product_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get products similar to the given product"""
        from app.models.product import Product
        
        if product_id not in self.product_embeddings or not self.index:
            return []
        
        # Get product embedding
        product_embedding = self.product_embeddings[product_id].reshape(1, -1)
        
        # Search for similar products
        scores, indices = self.index.search(product_embedding, limit + 1)  # +1 to exclude self
        
        # Get product details
        similar_products = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # Invalid index
                continue
            
            # Find product ID by index
            product_ids = list(self.product_embeddings.keys())
            if idx < len(product_ids):
                similar_product_id = product_ids[idx]
                
                # Skip the same product
                if similar_product_id == product_id:
                    continue
                
                product = self.db.query(Product).filter(Product.id == similar_product_id).first()
                if product:
                    similar_products.append({
                        "product_id": product.id,
                        "title": product.title,
                        "price": float(product.price),
                        "image_url": product.images[0] if product.images else None,
                        "score": float(score),
                        "reason": "Similar product"
                    })
        
        return similar_products[:limit]
    
    async def get_category_recommendations(self, category_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recommendations within a specific category"""
        from app.models.product import Product
        
        products = self.db.query(Product).filter(
            Product.category_id == category_id,
            Product.status == "active"
        ).order_by(desc(Product.rating), desc(Product.sales_count)).limit(limit).all()
        
        return [
            {
                "product_id": product.id,
                "title": product.title,
                "price": float(product.price),
                "image_url": product.images[0] if product.images else None,
                "score": float(product.rating),
                "reason": "Top rated in category"
            }
            for product in products
        ]
    
    async def get_popular_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular products"""
        from app.models.product import Product
        
        products = self.db.query(Product).filter(
            Product.status == "active"
        ).order_by(desc(Product.sales_count), desc(Product.rating)).limit(limit).all()
        
        return [
            {
                "product_id": product.id,
                "title": product.title,
                "price": float(product.price),
                "image_url": product.images[0] if product.images else None,
                "score": float(product.sales_count),
                "reason": "Popular product"
            }
            for product in products
        ]
    
    async def get_trending_products(self, limit: int = 10, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get trending products (recent sales)"""
        from app.models.product import Product
        from app.models.order import Order, OrderItem
        
        # Get products with recent sales (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        query = self.db.query(
            Product.id,
            Product.title,
            Product.price,
            Product.images,
            func.sum(OrderItem.quantity).label('recent_sales')
        ).join(OrderItem).join(Order).filter(
            Order.created_at >= week_ago,
            Order.status.in_(["paid", "processing", "shipped", "delivered"]),
            Product.status == "active"
        )
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        trending = query.group_by(Product.id).order_by(desc('recent_sales')).limit(limit).all()
        
        return [
            {
                "product_id": row.id,
                "title": row.title,
                "price": float(row.price),
                "image_url": row.images[0] if row.images else None,
                "score": float(row.recent_sales),
                "reason": "Trending product"
            }
            for row in trending
        ]
    
    async def get_new_arrivals(self, limit: int = 10, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get new arrival products"""
        from app.models.product import Product
        
        query = self.db.query(Product).filter(Product.status == "active")
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        products = query.order_by(desc(Product.created_at)).limit(limit).all()
        
        return [
            {
                "product_id": product.id,
                "title": product.title,
                "price": float(product.price),
                "image_url": product.images[0] if product.images else None,
                "score": 1.0,
                "reason": "New arrival"
            }
            for product in products
        ]
    
    async def get_personalized_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get personalized recommendations combining multiple strategies"""
        # Combine user-based and popular recommendations
        user_recs = await self.get_user_recommendations(user_id, limit // 2)
        popular_recs = await self.get_popular_products(limit // 2)
        
        # Merge and deduplicate
        all_recs = user_recs + popular_recs
        seen = set()
        unique_recs = []
        
        for rec in all_recs:
            if rec['product_id'] not in seen:
                unique_recs.append(rec)
                seen.add(rec['product_id'])
        
        return unique_recs[:limit]



