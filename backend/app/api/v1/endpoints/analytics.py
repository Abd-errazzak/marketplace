"""
Analytics endpoints for sellers and admin
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Any
from datetime import datetime, timedelta
import csv
import io
from app.core.database import get_db
from app.core.security import get_current_active_user, require_seller, require_admin
from app.models.user import User, UserRole, Seller
from app.models.product import Product
from app.models.order import Order, OrderItem, SellerPayout
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("/seller/overview")
async def get_seller_analytics_overview(
    period: str = "month",  # day, week, month, year
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    """Get seller analytics overview"""
    # Get seller profile
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    # Calculate date range
    now = datetime.utcnow()
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)
    
    # Get orders for this seller
    orders_query = db.query(Order).join(OrderItem).filter(
        OrderItem.seller_id == seller.id,
        Order.created_at >= start_date
    )
    
    # Total sales
    total_sales = db.query(func.sum(OrderItem.total_price)).filter(
        OrderItem.seller_id == seller.id,
        Order.created_at >= start_date,
        Order.status.in_(["paid", "processing", "shipped", "delivered"])
    ).scalar() or 0
    
    # Total orders
    total_orders = orders_query.filter(
        Order.status.in_(["paid", "processing", "shipped", "delivered"])
    ).count()
    
    # Total products sold
    total_products_sold = db.query(func.sum(OrderItem.quantity)).filter(
        OrderItem.seller_id == seller.id,
        Order.created_at >= start_date,
        Order.status.in_(["paid", "processing", "shipped", "delivered"])
    ).scalar() or 0
    
    # Average order value
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    # Commission paid
    total_commission = db.query(func.sum(SellerPayout.commission_amount)).filter(
        SellerPayout.seller_id == seller.id,
        SellerPayout.created_at >= start_date
    ).scalar() or 0
    
    # Net earnings
    net_earnings = total_sales - total_commission
    
    return {
        "period": period,
        "date_range": {
            "start": start_date.isoformat(),
            "end": now.isoformat()
        },
        "sales": {
            "total_sales": float(total_sales),
            "total_orders": total_orders,
            "total_products_sold": int(total_products_sold),
            "average_order_value": float(avg_order_value)
        },
        "earnings": {
            "gross_earnings": float(total_sales),
            "commission_paid": float(total_commission),
            "net_earnings": float(net_earnings)
        }
    }


@router.get("/seller/sales-chart")
async def get_seller_sales_chart(
    period: str = "month",
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    """Get seller sales chart data"""
    # Get seller profile
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    # Calculate date range
    now = datetime.utcnow()
    if period == "day":
        # Hourly data for the day
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        interval = "hour"
        format_str = "%Y-%m-%d %H:00:00"
    elif period == "week":
        # Daily data for the week
        start_date = now - timedelta(days=7)
        interval = "day"
        format_str = "%Y-%m-%d"
    elif period == "month":
        # Daily data for the month
        start_date = now - timedelta(days=30)
        interval = "day"
        format_str = "%Y-%m-%d"
    elif period == "year":
        # Monthly data for the year
        start_date = now - timedelta(days=365)
        interval = "month"
        format_str = "%Y-%m"
    else:
        start_date = now - timedelta(days=30)
        interval = "day"
        format_str = "%Y-%m-%d"
    
    # Get sales data grouped by time period
    if interval == "hour":
        sales_data = db.query(
            func.date_format(Order.created_at, format_str).label('period'),
            func.sum(OrderItem.total_price).label('sales'),
            func.count(func.distinct(Order.id)).label('orders')
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller.id,
            Order.created_at >= start_date,
            Order.status.in_(["paid", "processing", "shipped", "delivered"])
        ).group_by('period').order_by('period').all()
    elif interval == "day":
        sales_data = db.query(
            func.date_format(Order.created_at, format_str).label('period'),
            func.sum(OrderItem.total_price).label('sales'),
            func.count(func.distinct(Order.id)).label('orders')
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller.id,
            Order.created_at >= start_date,
            Order.status.in_(["paid", "processing", "shipped", "delivered"])
        ).group_by('period').order_by('period').all()
    else:  # month
        sales_data = db.query(
            func.date_format(Order.created_at, format_str).label('period'),
            func.sum(OrderItem.total_price).label('sales'),
            func.count(func.distinct(Order.id)).label('orders')
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller.id,
            Order.created_at >= start_date,
            Order.status.in_(["paid", "processing", "shipped", "delivered"])
        ).group_by('period').order_by('period').all()
    
    return {
        "period": period,
        "interval": interval,
        "data": [
            {
                "period": row.period,
                "sales": float(row.sales or 0),
                "orders": row.orders or 0
            }
            for row in sales_data
        ]
    }


@router.get("/seller/top-products")
async def get_seller_top_products(
    period: str = "month",
    limit: int = 10,
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    """Get seller's top-selling products"""
    # Get seller profile
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    # Calculate date range
    now = datetime.utcnow()
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)
    
    # Get top products
    top_products = db.query(
        Product.id,
        Product.title,
        Product.sku,
        func.sum(OrderItem.quantity).label('quantity_sold'),
        func.sum(OrderItem.total_price).label('revenue')
    ).join(OrderItem).join(Order).filter(
        Product.seller_id == seller.id,
        Order.created_at >= start_date,
        Order.status.in_(["paid", "processing", "shipped", "delivered"])
    ).group_by(Product.id).order_by(desc('quantity_sold')).limit(limit).all()
    
    return [
        {
            "product_id": row.id,
            "title": row.title,
            "sku": row.sku,
            "quantity_sold": int(row.quantity_sold or 0),
            "revenue": float(row.revenue or 0)
        }
        for row in top_products
    ]


@router.get("/seller/export/csv")
async def export_seller_analytics_csv(
    period: str = "month",
    format_type: str = "sales",  # sales, orders, products
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    """Export seller analytics data as CSV"""
    # Get seller profile
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    # Calculate date range
    now = datetime.utcnow()
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    if format_type == "sales":
        # Sales data
        writer.writerow(['Date', 'Order ID', 'Product ID', 'Product Title', 'SKU', 'Quantity', 'Unit Price', 'Total Price', 'Buyer ID'])
        
        sales_data = db.query(
            Order.created_at,
            Order.id.label('order_id'),
            Product.id.label('product_id'),
            Product.title,
            Product.sku,
            OrderItem.quantity,
            OrderItem.unit_price,
            OrderItem.total_price,
            Order.buyer_id
        ).join(OrderItem).join(Product).filter(
            Product.seller_id == seller.id,
            Order.created_at >= start_date,
            Order.status.in_(["paid", "processing", "shipped", "delivered"])
        ).order_by(Order.created_at.desc()).all()
        
        for row in sales_data:
            writer.writerow([
                row.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                row.order_id,
                row.product_id,
                row.title,
                row.sku,
                row.quantity,
                float(row.unit_price),
                float(row.total_price),
                row.buyer_id
            ])
    
    elif format_type == "orders":
        # Orders data
        writer.writerow(['Date', 'Order ID', 'Order Number', 'Buyer ID', 'Status', 'Subtotal', 'Tax', 'Shipping', 'Total'])
        
        orders_data = db.query(Order).join(OrderItem).filter(
            OrderItem.seller_id == seller.id,
            Order.created_at >= start_date
        ).order_by(Order.created_at.desc()).all()
        
        for order in orders_data:
            writer.writerow([
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.id,
                order.order_number,
                order.buyer_id,
                order.status,
                float(order.subtotal),
                float(order.tax_amount),
                float(order.shipping_amount),
                float(order.total_amount)
            ])
    
    elif format_type == "products":
        # Products data
        writer.writerow(['Product ID', 'Title', 'SKU', 'Price', 'Stock', 'Status', 'Views', 'Sales Count', 'Rating', 'Created Date'])
        
        products_data = db.query(Product).filter(
            Product.seller_id == seller.id
        ).order_by(Product.created_at.desc()).all()
        
        for product in products_data:
            writer.writerow([
                product.id,
                product.title,
                product.sku,
                float(product.price),
                product.stock,
                product.status,
                product.view_count,
                product.sales_count,
                float(product.rating),
                product.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
    
    # Prepare response
    csv_content = output.getvalue()
    output.close()
    
    # Create response with CSV content
    response = Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=seller_analytics_{format_type}_{period}_{now.strftime('%Y%m%d')}.csv"
        }
    )
    
    return response


# Admin analytics endpoints
@router.get("/admin/platform-overview")
async def get_platform_analytics_overview(
    period: str = "month",
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get platform analytics overview (admin only)"""
    # Calculate date range
    now = datetime.utcnow()
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)
    
    # Platform statistics
    total_users = db.query(User).count()
    new_users = db.query(User).filter(User.created_at >= start_date).count()
    active_sellers = db.query(Seller).filter(Seller.is_active == True).count()
    
    total_products = db.query(Product).count()
    active_products = db.query(Product).filter(Product.status == "active").count()
    
    total_orders = db.query(Order).count()
    recent_orders = db.query(Order).filter(Order.created_at >= start_date).count()
    
    # Revenue statistics
    total_gmv = db.query(func.sum(Order.total_amount)).filter(
        Order.status.in_(["paid", "processing", "shipped", "delivered"])
    ).scalar() or 0
    
    recent_gmv = db.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= start_date,
        Order.status.in_(["paid", "processing", "shipped", "delivered"])
    ).scalar() or 0
    
    total_commission = db.query(func.sum(SellerPayout.commission_amount)).filter(
        SellerPayout.status == "completed"
    ).scalar() or 0
    
    return {
        "period": period,
        "date_range": {
            "start": start_date.isoformat(),
            "end": now.isoformat()
        },
        "users": {
            "total": total_users,
            "new_last_period": new_users,
            "active_sellers": active_sellers
        },
        "products": {
            "total": total_products,
            "active": active_products
        },
        "orders": {
            "total": total_orders,
            "recent_last_period": recent_orders
        },
        "revenue": {
            "total_gmv": float(total_gmv),
            "recent_gmv": float(recent_gmv),
            "total_commission": float(total_commission)
        }
    }



