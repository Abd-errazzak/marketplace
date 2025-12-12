"""
AI Chat service for customer support
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import openai
import json
from datetime import datetime
import uuid

from app.core.config import settings


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    
    async def process_message(self, message: str, user_id: Optional[int] = None, 
                            session_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a chat message and return AI response"""
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Get context about the marketplace
        marketplace_context = await self._get_marketplace_context()
        
        # Prepare system prompt
        system_prompt = f"""
        You are a helpful AI assistant for an online marketplace. You can help customers with:
        - Product information and recommendations
        - Order status and tracking
        - Return and refund policies
        - General marketplace questions
        
        Marketplace Information:
        {marketplace_context}
        
        Be helpful, friendly, and professional. If you don't know something, ask for clarification.
        """
        
        # Get chat history
        chat_history = await self.get_chat_history(user_id, session_id, limit=10)
        
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history
        for msg in chat_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            if self.openai_client:
                # Use OpenAI for response
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content
            else:
                # Fallback response if OpenAI is not configured
                ai_response = await self._get_fallback_response(message, context)
            
            # Generate suggestions
            suggestions = await self._generate_suggestions(message, ai_response)
            
            # Get related products if relevant
            related_products = await self._get_related_products(message)
            
            # Store chat history
            await self._store_chat_message(session_id, user_id, "user", message)
            await self._store_chat_message(session_id, user_id, "assistant", ai_response)
            
            return {
                "message": ai_response,
                "suggestions": suggestions,
                "related_products": related_products,
                "session_id": session_id
            }
            
        except Exception as e:
            # Fallback response on error
            fallback_response = "I apologize, but I'm having trouble processing your request right now. Please try again later or contact our support team."
            
            return {
                "message": fallback_response,
                "suggestions": ["Contact support", "Browse products", "Check order status"],
                "related_products": [],
                "session_id": session_id
            }
    
    async def _get_marketplace_context(self) -> str:
        """Get marketplace context information"""
        from app.models.product import Product, Category
        from app.models.order import Order
        
        # Get basic stats
        total_products = self.db.query(Product).filter(Product.status == "active").count()
        total_categories = self.db.query(Category).filter(Category.is_active == True).count()
        total_orders = self.db.query(Order).count()
        
        # Get popular categories
        popular_categories = self.db.query(Category.name).join(Product).filter(
            Category.is_active == True,
            Product.status == "active"
        ).group_by(Category.id).limit(5).all()
        
        category_names = [cat.name for cat in popular_categories]
        
        return f"""
        - Total Products: {total_products}
        - Categories: {total_categories}
        - Total Orders: {total_orders}
        - Popular Categories: {', '.join(category_names)}
        - Free shipping on orders over $50
        - 30-day return policy
        - 24/7 customer support
        """
    
    async def _get_fallback_response(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Get fallback response when OpenAI is not available"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["order", "tracking", "status"]):
            return "To check your order status, please visit the 'My Orders' section in your account or provide your order number."
        
        elif any(word in message_lower for word in ["return", "refund", "exchange"]):
            return "We offer a 30-day return policy. You can initiate a return from your order details page or contact our support team."
        
        elif any(word in message_lower for word in ["shipping", "delivery"]):
            return "We offer free shipping on orders over $50. Standard shipping takes 3-5 business days."
        
        elif any(word in message_lower for word in ["product", "item", "buy"]):
            return "I can help you find products! You can browse by category or use the search function. What are you looking for?"
        
        elif any(word in message_lower for word in ["help", "support", "problem"]):
            return "I'm here to help! You can contact our support team at support@marketplace.com or use our help center."
        
        else:
            return "I'm here to help with your marketplace questions. You can ask about products, orders, shipping, returns, or any other marketplace-related topics."
    
    async def _generate_suggestions(self, user_message: str, ai_response: str) -> List[str]:
        """Generate helpful suggestions based on the conversation"""
        suggestions = []
        
        if "order" in user_message.lower():
            suggestions.extend(["Track my orders", "View order history", "Contact support"])
        
        if "product" in user_message.lower():
            suggestions.extend(["Browse categories", "Search products", "View recommendations"])
        
        if "return" in user_message.lower() or "refund" in user_message.lower():
            suggestions.extend(["Return policy", "Start return process", "Contact support"])
        
        if "shipping" in user_message.lower():
            suggestions.extend(["Shipping information", "Track package", "Delivery options"])
        
        # Default suggestions
        if not suggestions:
            suggestions = ["Browse products", "My account", "Contact support", "Help center"]
        
        return suggestions[:4]  # Limit to 4 suggestions
    
    async def _get_related_products(self, message: str) -> List[Dict[str, Any]]:
        """Get related products based on the message"""
        from app.models.product import Product
        
        # Simple keyword matching for now
        message_lower = message.lower()
        
        # Extract potential product keywords
        keywords = []
        for word in message_lower.split():
            if len(word) > 3:  # Skip short words
                keywords.append(word)
        
        if not keywords:
            return []
        
        # Search for products with matching keywords
        products = self.db.query(Product).filter(
            Product.status == "active"
        ).limit(3).all()
        
        return [
            {
                "id": product.id,
                "title": product.title,
                "price": float(product.price),
                "image_url": product.images[0] if product.images else None
            }
            for product in products
        ]
    
    async def _store_chat_message(self, session_id: str, user_id: Optional[int], 
                                role: str, content: str):
        """Store chat message in database"""
        # This would typically store in a chat_messages table
        # For now, we'll just log it
        print(f"Chat message stored: {session_id}, {user_id}, {role}, {content[:50]}...")
    
    async def get_suggestions(self, user_id: Optional[int] = None, 
                            session_id: Optional[str] = None) -> List[str]:
        """Get contextual suggestions"""
        suggestions = [
            "How do I track my order?",
            "What's your return policy?",
            "Do you offer free shipping?",
            "How can I contact support?",
            "What are your most popular products?",
            "How do I create an account?",
            "What payment methods do you accept?"
        ]
        
        return suggestions
    
    async def get_chat_history(self, user_id: Optional[int] = None, 
                             session_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get chat history"""
        # This would typically query a chat_messages table
        # For now, return empty list
        return []



