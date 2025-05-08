/**
 * Datify API Client
 * 
 * This module provides a client for interacting with the Datify API.
 * It handles authentication, request formatting, and response parsing.
 */

// API base URL - this would be different in production
const API_BASE_URL = 'http://localhost:5000/api';

// Default headers for all requests
const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
};

/**
 * Get auth token from local storage
 */
const getToken = () => {
  const auth = JSON.parse(localStorage.getItem('datify_auth') || '{}');
  return auth.token || null;
};

/**
 * Add authorization header if token exists
 */
const getAuthHeaders = () => {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

/**
 * Basic API request with error handling
 */
const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers = {
    ...DEFAULT_HEADERS,
    ...getAuthHeaders(),
    ...options.headers,
  };
  
  const config = {
    ...options,
    headers,
  };
  
  try {
    const response = await fetch(url, config);
    
    // Parse JSON response
    const data = await response.json();
    
    // Handle API errors
    if (!response.ok) {
      throw {
        status: response.status,
        message: data.message || 'An error occurred',
        data,
      };
    }
    
    return data;
  } catch (error) {
    // Handle network errors
    if (!error.status) {
      console.error('Network error:', error);
      throw {
        status: 0,
        message: 'Network error. Please check your connection.',
      };
    }
    
    // Handle token expiration
    if (error.status === 401) {
      // Clear auth token and redirect to login
      localStorage.removeItem('datify_auth');
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    
    throw error;
  }
};

/**
 * API client with methods for different endpoints
 */
const api = {
  // Authentication
  auth: {
    login: (credentials) => apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    }),
    
    register: (userData) => apiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    }),
    
    logout: () => apiRequest('/auth/logout', {
      method: 'POST',
    }),
    
    refreshToken: () => apiRequest('/auth/refresh-token', {
      method: 'POST',
    }),
  },
  
  // User profile
  user: {
    getProfile: () => apiRequest('/users/me'),
    
    updateProfile: (profileData) => apiRequest('/user/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    }),
    
    uploadProfilePicture: (formData) => apiRequest('/user/profile/picture', {
      method: 'POST',
      headers: {}, // Remove Content-Type to let browser set it with boundary
      body: formData,
    }),
    
    getUserById: (userId) => apiRequest(`/users/${userId}`),
    
    blockUser: (userId) => apiRequest(`/user/block/${userId}`, {
      method: 'POST',
    }),
    
    unblockUser: (userId) => apiRequest(`/user/block/${userId}`, {
      method: 'DELETE',
    }),
    
    getBlockedUsers: () => apiRequest('/user/blocked'),
    
    verifyAccount: (formData) => apiRequest('/user/verify', {
      method: 'POST',
      headers: {}, // Remove Content-Type for file uploads
      body: formData,
    }),
  },
  
  // Discovery and matching
  discovery: {
    getUsers: () => apiRequest('/match/discover'),
    
    likeUser: (userId, isSuperLike = false) => apiRequest(`/match/like/${userId}`, {
      method: 'POST',
      body: JSON.stringify({ is_super_like: isSuperLike }),
    }),
    
    dislikeUser: (userId) => apiRequest(`/match/dislike/${userId}`, {
      method: 'POST',
    }),
    
    getMatches: () => apiRequest('/matches'),
    
    getMatch: (matchId) => apiRequest(`/matches/${matchId}`),
    
    unmatch: (matchId) => apiRequest(`/matches/${matchId}/unmatch`, {
      method: 'POST',
    }),
  },
  
  // Messaging
  chat: {
    getMessages: (matchId, page = 1) => apiRequest(`/matches/${matchId}/messages?page=${page}`),
    
    sendMessage: (matchId, content) => apiRequest(`/matches/${matchId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
    
    sendAttachment: (matchId, formData) => apiRequest(`/matches/${matchId}/messages`, {
      method: 'POST',
      headers: {}, // Remove Content-Type for file uploads
      body: formData,
    }),
    
    markAsRead: (messageId) => apiRequest(`/messages/${messageId}/read`, {
      method: 'POST',
    }),
    
    sendTypingIndicator: (matchId) => apiRequest(`/matches/${matchId}/typing`, {
      method: 'POST',
    }),
    
    getUnreadCount: () => apiRequest('/messages/unread'),
  },
  
  // Reels
  reels: {
    getReels: (page = 1) => apiRequest(`/reels?page=${page}`),
    
    getReel: (reelId) => apiRequest(`/reels/${reelId}`),
    
    createReel: (formData) => apiRequest('/reels', {
      method: 'POST',
      headers: {}, // Remove Content-Type for file uploads
      body: formData,
    }),
    
    deleteReel: (reelId) => apiRequest(`/reels/${reelId}`, {
      method: 'DELETE',
    }),
    
    likeReel: (reelId) => apiRequest(`/reels/${reelId}/like`, {
      method: 'POST',
    }),
    
    unlikeReel: (reelId) => apiRequest(`/reels/${reelId}/like`, {
      method: 'DELETE',
    }),
    
    getComments: (reelId, page = 1) => apiRequest(`/reels/${reelId}/comments?page=${page}`),
    
    addComment: (reelId, content, parentId = null) => apiRequest(`/reels/${reelId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content, parent_id: parentId }),
    }),
    
    deleteComment: (commentId) => apiRequest(`/reels/comments/${commentId}`, {
      method: 'DELETE',
    }),
    
    reportReel: (reelId, reason, description = '') => apiRequest(`/reels/${reelId}/report`, {
      method: 'POST',
      body: JSON.stringify({ reason, description }),
    }),
    
    getTrendingReels: (page = 1) => apiRequest(`/reels/trending?page=${page}`),
  },
  
  // Subscriptions
  subscriptions: {
    getPlans: () => apiRequest('/subscriptions/plans'),
    
    getCurrentSubscription: () => apiRequest('/subscriptions/current'),
    
    getTransactions: (page = 1) => apiRequest(`/transactions?page=${page}`),
  },
};

export default api;
