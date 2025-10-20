import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
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
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth endpoints
export const authAPI = {
  login: (email, password) => 
    api.post('/api/v1/auth/login', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }),
  register: (data) => api.post('/api/v1/auth/register', data),
  getMe: () => api.get('/api/v1/auth/me'),
};

// Receipt endpoints
export const receiptAPI = {
  upload: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/v1/receipts/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  list: (params) => api.get('/api/v1/receipts', { params }),
  get: (id) => api.get(`/api/v1/receipts/${id}`),
  update: (id, data) => api.put(`/api/v1/receipts/${id}`, data),
  delete: (id) => api.delete(`/api/v1/receipts/${id}`),
  reprocess: (id) => api.post(`/api/v1/receipts/${id}/reprocess`),
  download: (id) => api.get(`/api/v1/receipts/${id}/download`),
};

export default api;
