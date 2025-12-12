"""
Product classification and auto-tagging service
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any, Optional
import re
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import pickle
import os

from app.core.config import settings


class ClassificationService:
    def __init__(self, db: Session):
        self.db = db
        self.vector_db_path = settings.VECTOR_DB_PATH
        self._load_classification_models()
    
    def _load_classification_models(self):
        """Load or create classification models"""
        os.makedirs(self.vector_db_path, exist_ok=True)
        
        category_model_file = os.path.join(self.vector_db_path, "category_classifier.pkl")
        tag_model_file = os.path.join(self.vector_db_path, "tag_classifier.pkl")
        
        if os.path.exists(category_model_file):
            with open(category_model_file, 'rb') as f:
                self.category_classifier = pickle.load(f)
        else:
            self.category_classifier = None
        
        if os.path.exists(tag_model_file):
            with open(tag_model_file, 'rb') as f:
                self.tag_classifier = pickle.load(f)
        else:
            self.tag_classifier = None
        
        # Build models if they don't exist
        if not self.category_classifier or not self.tag_classifier:
            self._build_classification_models()
    
    def _build_classification_models(self):
        """Build classification models from existing products"""
        from app.models.product import Product
        from app.models.product import Category
        
        # Get all products with categories
        products = self.db.query(Product).filter(
            Product.status == "active",
            Product.category_id.isnot(None)
        ).all()
        
        if not products:
            return
        
        # Prepare training data
        texts = []
        categories = []
        tags_list = []
        
        for product in products:
            # Combine title and description
            text = f"{product.title}"
            if product.description:
                text += f" {product.description}"
            
            texts.append(text)
            categories.append(product.category_id)
            
            if product.tags:
                tags_list.append(product.tags)
        
        # Train category classifier
        if texts and categories:
            self.category_classifier = Pipeline([
                ('tfidf', TfidfVectorizer(max_features=1000, stop_words='english')),
                ('classifier', MultinomialNB())
            ])
            self.category_classifier.fit(texts, categories)
        
        # Train tag classifier (simplified approach)
        if texts and tags_list:
            # Flatten all tags
            all_tags = []
            for tags in tags_list:
                all_tags.extend(tags)
            
            # Get most common tags
            tag_counter = Counter(all_tags)
            common_tags = [tag for tag, count in tag_counter.most_common(50)]
            
            # Create binary features for each tag
            tag_features = []
            for text in texts:
                features = []
                for tag in common_tags:
                    features.append(1 if tag.lower() in text.lower() else 0)
                tag_features.append(features)
            
            self.tag_classifier = {
                'tags': common_tags,
                'features': np.array(tag_features)
            }
        
        # Save models
        self._save_classification_models()
    
    def _save_classification_models(self):
        """Save classification models to disk"""
        category_model_file = os.path.join(self.vector_db_path, "category_classifier.pkl")
        tag_model_file = os.path.join(self.vector_db_path, "tag_classifier.pkl")
        
        if self.category_classifier:
            with open(category_model_file, 'wb') as f:
                pickle.dump(self.category_classifier, f)
        
        if self.tag_classifier:
            with open(tag_model_file, 'wb') as f:
                pickle.dump(self.tag_classifier, f)
    
    async def classify_product(self, title: str, description: Optional[str] = None, 
                             images: Optional[List[str]] = None) -> Dict[str, Any]:
        """Classify a product and suggest category, tags, and price range"""
        from app.models.product import Category, Product
        
        # Combine title and description
        text = title
        if description:
            text += f" {description}"
        
        # Predict category
        predicted_category_id = None
        confidence = 0.0
        
        if self.category_classifier:
            try:
                predicted_category_id = self.category_classifier.predict([text])[0]
                confidence = self.category_classifier.predict_proba([text]).max()
            except:
                pass
        
        # Get category name
        category_name = "Unknown"
        if predicted_category_id:
            category = self.db.query(Category).filter(Category.id == predicted_category_id).first()
            if category:
                category_name = category.name
        
        # Generate tags
        tags_result = await self.generate_tags(title, description, predicted_category_id)
        
        # Suggest price range
        price_range = await self._suggest_price_range(title, description, predicted_category_id)
        
        return {
            "category_id": predicted_category_id or 1,  # Default to first category
            "category_name": category_name,
            "confidence": float(confidence),
            "suggested_tags": tags_result["tags"],
            "suggested_price_range": price_range
        }
    
    async def generate_tags(self, title: str, description: Optional[str] = None, 
                          category_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate automatic tags for a product"""
        # Combine title and description
        text = title
        if description:
            text += f" {description}"
        
        # Extract keywords from text
        keywords = self._extract_keywords(text)
        
        # Get category-specific tags
        category_tags = []
        if category_id:
            category_tags = await self._get_category_tags(category_id)
        
        # Combine and score tags
        all_tags = keywords + category_tags
        tag_scores = {}
        
        for tag in all_tags:
            if tag in tag_scores:
                tag_scores[tag] += 1
            else:
                tag_scores[tag] = 1
        
        # Sort by score and return top tags
        sorted_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)
        top_tags = [tag for tag, score in sorted_tags[:10]]
        
        return {
            "tags": top_tags,
            "confidence_scores": dict(sorted_tags[:10])
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into words
        words = text.split()
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        # Filter words
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword)
        
        return unique_keywords
    
    async def _get_category_tags(self, category_id: int) -> List[str]:
        """Get common tags for a category"""
        from app.models.product import Product
        
        # Get products in this category
        products = self.db.query(Product).filter(
            Product.category_id == category_id,
            Product.tags.isnot(None)
        ).limit(100).all()
        
        # Collect all tags
        all_tags = []
        for product in products:
            if product.tags:
                all_tags.extend(product.tags)
        
        # Get most common tags
        tag_counter = Counter(all_tags)
        return [tag for tag, count in tag_counter.most_common(10)]
    
    async def _suggest_price_range(self, title: str, description: Optional[str] = None, 
                                 category_id: Optional[int] = None) -> Optional[Dict[str, float]]:
        """Suggest price range based on similar products"""
        from app.models.product import Product
        
        if not category_id:
            return None
        
        # Get products in the same category
        products = self.db.query(Product.price).filter(
            Product.category_id == category_id,
            Product.status == "active",
            Product.price.isnot(None)
        ).all()
        
        if not products:
            return None
        
        prices = [float(product.price) for product in products]
        
        # Calculate price statistics
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # Suggest range around average
        suggested_min = max(min_price, avg_price * 0.7)
        suggested_max = min(max_price, avg_price * 1.3)
        
        return {
            "min_price": suggested_min,
            "max_price": suggested_max,
            "average_price": avg_price
        }
    
    async def bulk_classify_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bulk classify multiple products"""
        results = []
        
        for product in products:
            result = await self.classify_product(
                title=product["title"],
                description=product.get("description"),
                images=product.get("images")
            )
            results.append(result)
        
        return results
    
    async def get_category_suggestions(self, query: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get category suggestions based on query"""
        from app.models.product import Category
        
        if query:
            # Search categories by name
            categories = self.db.query(Category).filter(
                Category.name.contains(query),
                Category.is_active == True
            ).limit(limit).all()
        else:
            # Get popular categories
            categories = self.db.query(Category).filter(
                Category.is_active == True
            ).limit(limit).all()
        
        return [
            {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "product_count": 0  # Would need to count products
            }
            for category in categories
        ]



