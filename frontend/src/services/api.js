import axios from 'axios';
import toast from 'react-hot-toast';

// Create axios instance
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    
    if (error.response?.status >= 500) {
      toast.error('Server error. Please try again later.');
    }
    
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { username: email, password }),
  register: (userData) => api.post('/auth/register', userData),
  getCurrentUser: () => api.get('/auth/me'),
  changePassword: (passwordData) => api.post('/auth/change-password', passwordData),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) => api.post('/auth/reset-password', { token, new_password: newPassword }),
  logout: () => api.post('/auth/logout'),
};

// Products API
export const productsAPI = {
  getProducts: (params) => api.get('/products', { params }),
  getProduct: (id) => api.get(`/products/${id}`),
  createProduct: (productData) => api.post('/products', productData),
  updateProduct: (id, productData) => api.put(`/products/${id}`, productData),
  deleteProduct: (id) => api.delete(`/products/${id}`),
  getCategories: () => api.get('/products/categories'),
  searchProducts: (query, filters) => api.get('/products', { params: { search: query, ...filters } }),
};

// Cart API
export const cartAPI = {
  getCartItems: () => api.get('/products/cart/items'),
  addToCart: (itemData) => api.post('/products/cart/items', itemData),
  updateCartItem: (itemId, updates) => api.put(`/products/cart/items/${itemId}`, updates),
  removeFromCart: (itemId) => api.delete(`/products/cart/items/${itemId}`),
};

// Orders API
export const ordersAPI = {
  getOrders: (params) => api.get('/orders', { params }),
  getOrder: (id) => api.get(`/orders/${id}`),
  createOrder: (orderData) => api.post('/orders/checkout', orderData),
  updateOrderStatus: (id, status) => api.put(`/orders/${id}/status`, { status }),
  cancelOrder: (id) => api.post(`/orders/${id}/cancel`),
  getSellerOrders: (params) => api.get('/orders/seller/orders', { params }),
  getSellerOrder: (id) => api.get(`/orders/seller/orders/${id}`),
  fulfillOrder: (id, trackingNumber) => api.put(`/orders/seller/orders/${id}/fulfill`, { tracking_number: trackingNumber }),
};

// Payments API
export const paymentsAPI = {
  createStripePaymentIntent: (paymentData) => api.post('/payments/stripe/create-payment-intent', paymentData),
  createPayPalOrder: (paymentData) => api.post('/payments/paypal/create-order', paymentData),
  executePayPalPayment: (paymentId, payerId) => api.post('/payments/paypal/execute', { payment_id: paymentId, payer_id: payerId }),
  getPaymentHistory: (params) => api.get('/payments/history', { params }),
  getSellerPayouts: (params) => api.get('/payments/payouts', { params }),
  validateCoupon: (couponData) => api.post('/payments/coupons/validate', couponData),
};

// Users API
export const usersAPI = {
  getProfile: () => api.get('/users/profile'),
  updateProfile: (userData) => api.put('/users/profile', userData),
  getAddresses: () => api.get('/users/addresses'),
  createAddress: (addressData) => api.post('/users/addresses', addressData),
  updateAddress: (id, addressData) => api.put(`/users/addresses/${id}`, addressData),
  deleteAddress: (id) => api.delete(`/users/addresses/${id}`),
  getSellerProfile: () => api.get('/users/seller-profile'),
  createSellerProfile: (sellerData) => api.post('/users/seller-profile', sellerData),
  updateSellerProfile: (sellerData) => api.put('/users/seller-profile', sellerData),
};

// Wishlist API
export const wishlistAPI = {
  getWishlist: () => api.get('/products/wishlist'),
  addToWishlist: (productId) => api.post('/products/wishlist', { product_id: productId }),
  removeFromWishlist: (productId) => api.delete(`/products/wishlist/${productId}`),
};

// Reviews API
export const reviewsAPI = {
  getProductReviews: (productId, params) => api.get(`/products/${productId}/reviews`, { params }),
  createReview: (productId, reviewData) => api.post(`/products/${productId}/reviews`, reviewData),
  updateReview: (reviewId, reviewData) => api.put(`/reviews/${reviewId}`, reviewData),
  deleteReview: (reviewId) => api.delete(`/reviews/${reviewId}`),
};

// Analytics API
export const analyticsAPI = {
  getSellerAnalytics: (period) => api.get('/analytics/seller/overview', { params: { period } }),
  getSellerSalesChart: (period) => api.get('/analytics/seller/sales-chart', { params: { period } }),
  getSellerTopProducts: (period, limit) => api.get('/analytics/seller/top-products', { params: { period, limit } }),
  exportSellerAnalytics: (period, format) => api.get('/analytics/seller/export/csv', { 
    params: { period, format_type: format },
    responseType: 'blob'
  }),
  getPlatformAnalytics: (period) => api.get('/analytics/admin/platform-overview', { params: { period } }),
};

// Admin API
export const adminAPI = {
  getDashboardStats: () => api.get('/admin/dashboard/stats'),
  getUsers: (params) => api.get('/admin/users', { params }),
  getUser: (id) => api.get(`/admin/users/${id}`),
  activateUser: (id) => api.put(`/admin/users/${id}/activate`),
  deactivateUser: (id) => api.put(`/admin/users/${id}/deactivate`),
  updateUserRole: (id, role) => api.put(`/admin/users/${id}/role`, { new_role: role }),
  getSellers: (params) => api.get('/admin/sellers', { params }),
  verifySeller: (id) => api.put(`/admin/sellers/${id}/verify`),
  unverifySeller: (id) => api.put(`/admin/sellers/${id}/unverify`),
  getProducts: (params) => api.get('/admin/products', { params }),
  approveProduct: (id) => api.put(`/admin/products/${id}/approve`),
  rejectProduct: (id, reason) => api.put(`/admin/products/${id}/reject`, { reason }),
  getOrders: (params) => api.get('/admin/orders', { params }),
  getOrder: (id) => api.get(`/admin/orders/${id}`),
  getPayments: (params) => api.get('/admin/payments', { params }),
  getPayouts: (params) => api.get('/admin/payouts', { params }),
  processPayout: (id) => api.put(`/admin/payouts/${id}/process`),
  getAnalyticsEvents: (params) => api.get('/admin/analytics/events', { params }),
  getNotifications: (params) => api.get('/admin/notifications', { params }),
  getMessages: (params) => api.get('/admin/messages', { params }),
};

// AI Service API
export const aiAPI = {
  getRecommendations: (requestData) => api.post('/ai/recommendations/products', requestData),
  getTrendingProducts: (limit, categoryId) => api.get('/ai/recommendations/trending', { params: { limit, category_id: categoryId } }),
  getNewArrivals: (limit, categoryId) => api.get('/ai/recommendations/new-arrivals', { params: { limit, category_id: categoryId } }),
  getPersonalizedRecommendations: (userId, limit) => api.post('/ai/recommendations/personalized', { user_id: userId, limit }),
  sendChatMessage: (messageData) => api.post('/ai/chat/message', messageData),
  getChatSuggestions: (userId, sessionId) => api.get('/ai/chat/suggestions', { params: { user_id: userId, session_id: sessionId } }),
  getChatHistory: (userId, sessionId, limit) => api.get('/ai/chat/history', { params: { user_id: userId, session_id: sessionId, limit } }),
  classifyProduct: (productData) => api.post('/ai/classification/product', productData),
  autoTagProduct: (productData) => api.post('/ai/classification/auto-tag', productData),
  getCategorySuggestions: (query, limit) => api.get('/ai/classification/categories', { params: { query, limit } }),
};

export default api;






