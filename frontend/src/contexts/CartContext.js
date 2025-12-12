import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { cartAPI } from '../services/api';
import { useAuth } from './AuthContext';
import toast from 'react-hot-toast';

const CartContext = createContext();

const initialState = {
  items: [],
  total: 0,
  itemCount: 0,
  loading: false,
};

const cartReducer = (state, action) => {
  switch (action.type) {
    case 'SET_LOADING':
      return {
        ...state,
        loading: action.payload,
      };
    case 'SET_CART':
      return {
        ...state,
        items: action.payload.items || [],
        total: action.payload.total || 0,
        itemCount: action.payload.itemCount || 0,
      };
    case 'ADD_ITEM':
      return {
        ...state,
        items: [...state.items, action.payload],
        itemCount: state.itemCount + action.payload.quantity,
        total: state.total + (action.payload.price * action.payload.quantity),
      };
    case 'UPDATE_ITEM':
      return {
        ...state,
        items: state.items.map(item =>
          item.id === action.payload.id
            ? { ...item, ...action.payload.updates }
            : item
        ),
        itemCount: state.items.reduce((total, item) => 
          total + (item.id === action.payload.id ? action.payload.updates.quantity : item.quantity), 0
        ),
        total: state.items.reduce((total, item) => 
          total + (item.price * (item.id === action.payload.id ? action.payload.updates.quantity : item.quantity)), 0
        ),
      };
    case 'REMOVE_ITEM':
      return {
        ...state,
        items: state.items.filter(item => item.id !== action.payload),
        itemCount: state.items.reduce((total, item) => 
          total + (item.id === action.payload ? 0 : item.quantity), 0
        ),
        total: state.items.reduce((total, item) => 
          total + (item.id === action.payload ? 0 : item.price * item.quantity), 0
        ),
      };
    case 'CLEAR_CART':
      return {
        ...state,
        items: [],
        total: 0,
        itemCount: 0,
      };
    default:
      return state;
  }
};

export const CartProvider = ({ children }) => {
  const [state, dispatch] = useReducer(cartReducer, initialState);
  const { isAuthenticated, user } = useAuth();

  // Load cart on mount and when authentication changes
  useEffect(() => {
    loadCart();
  }, [isAuthenticated, user]);

  const loadCart = async () => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await cartAPI.getCartItems();
      const items = response.data || [];
      
      const total = items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
      const itemCount = items.reduce((sum, item) => sum + item.quantity, 0);
      
      dispatch({
        type: 'SET_CART',
        payload: { items, total, itemCount },
      });
    } catch (error) {
      console.error('Failed to load cart:', error);
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const addToCart = async (productId, quantity = 1, variationId = null) => {
    try {
      const response = await cartAPI.addToCart({
        product_id: productId,
        quantity,
        variation_id: variationId,
      });
      
      const newItem = response.data;
      
      // Check if item already exists in cart
      const existingItem = state.items.find(
        item => item.product_id === productId && item.variation_id === variationId
      );
      
      if (existingItem) {
        dispatch({
          type: 'UPDATE_ITEM',
          payload: {
            id: existingItem.id,
            updates: { quantity: existingItem.quantity + quantity },
          },
        });
      } else {
        dispatch({
          type: 'ADD_ITEM',
          payload: newItem,
        });
      }
      
      toast.success('Added to cart!');
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.message || 'Failed to add to cart';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const updateCartItem = async (itemId, quantity) => {
    if (quantity <= 0) {
      return removeFromCart(itemId);
    }
    
    try {
      await cartAPI.updateCartItem(itemId, { quantity });
      
      dispatch({
        type: 'UPDATE_ITEM',
        payload: {
          id: itemId,
          updates: { quantity },
        },
      });
      
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.message || 'Failed to update cart item';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const removeFromCart = async (itemId) => {
    try {
      await cartAPI.removeFromCart(itemId);
      
      dispatch({
        type: 'REMOVE_ITEM',
        payload: itemId,
      });
      
      toast.success('Item removed from cart');
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.message || 'Failed to remove item';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const clearCart = () => {
    dispatch({ type: 'CLEAR_CART' });
  };

  const getCartItemCount = () => {
    return state.itemCount;
  };

  const getCartTotal = () => {
    return state.total;
  };

  const isInCart = (productId, variationId = null) => {
    return state.items.some(
      item => item.product_id === productId && item.variation_id === variationId
    );
  };

  const getCartItem = (productId, variationId = null) => {
    return state.items.find(
      item => item.product_id === productId && item.variation_id === variationId
    );
  };

  const value = {
    ...state,
    addToCart,
    updateCartItem,
    removeFromCart,
    clearCart,
    loadCart,
    getCartItemCount,
    getCartTotal,
    isInCart,
    getCartItem,
  };

  return (
    <CartContext.Provider value={value}>
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};






