/**
 * Error handling utilities
 */

export const getErrorMessage = (error) => {
  if (!error) return 'An unknown error occurred';
  
  // Network/connection errors
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return 'Request timeout. The server is taking too long to respond.';
  }
  
  if (error.message?.includes('Network Error') || error.message?.includes('Failed to fetch')) {
    return 'Cannot connect to server. Please make sure the backend is running on http://localhost:8000';
  }
  
  // HTTP errors
  if (error.response) {
    const status = error.response.status;
    const data = error.response.data;
    
    if (status === 400) {
      return data?.detail || data?.message || 'Invalid request. Please check your input.';
    }
    
    if (status === 401) {
      return 'Authentication failed. Please check your credentials.';
    }
    
    if (status === 403) {
      return 'You do not have permission to perform this action.';
    }
    
    if (status === 404) {
      return 'The requested resource was not found.';
    }
    
    if (status === 409) {
      return data?.detail || data?.message || 'This email is already registered.';
    }
    
    if (status >= 500) {
      return 'Server error. Please try again later or contact support.';
    }
    
    return data?.detail || data?.message || data?.error || `Server error (${status})`;
  }
  
  // Request errors (no response)
  if (error.request) {
    return 'Cannot connect to server. Please make sure the backend is running.';
  }
  
  // Other errors
  return error.message || 'An unexpected error occurred';
};

export const logError = (error, context = '') => {
  console.error(`[Error${context ? ` in ${context}` : ''}]:`, {
    message: error.message,
    response: error.response?.data,
    status: error.response?.status,
    config: {
      url: error.config?.url,
      method: error.config?.method,
      data: error.config?.data,
    },
  });
};



