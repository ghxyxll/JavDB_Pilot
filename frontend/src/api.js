import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper to get local stored JavDB cookie
export function getSavedCookie() {
  return localStorage.getItem('javdb_cookie') || '';
}

export function setSavedCookie(cookie) {
  if (cookie) {
    localStorage.setItem('javdb_cookie', cookie);
  } else {
    localStorage.removeItem('javdb_cookie');
  }
}

export const saveCookieToStorage = setSavedCookie;

// Helper to get local stored System Auth token
export function getAuthToken() {
  return localStorage.getItem('sys_auth_token') || '';
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('sys_auth_token', token);
  } else {
    localStorage.removeItem('sys_auth_token');
  }
}

export function removeAuthToken() {
  localStorage.removeItem('sys_auth_token');
}

// Request interceptor to automatically attach cookies & Auth token
api.interceptors.request.use((config) => {
  const cookie = getSavedCookie();
  const token = getAuthToken();
  const method = (config.method || '').toLowerCase();
  
  if (token) {
    if (config.headers.set) {
      config.headers.set('Authorization', `Bearer ${token}`);
    } else {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
  }

  if (['post', 'put', 'patch'].includes(method)) {
    if (!config.data) {
      config.data = {};
    }
    if (cookie && typeof config.data === 'object' && !config.data.cookies) {
      config.data.cookies = cookie;
    }
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Helper for formatting error messages safely
export function formatApiError(err) {
  if (!err.response) return err.message || '网络连接失败，请检查后端服务';
  const detail = err.response.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(d => `${d.loc ? d.loc.join('.') : ''}: ${d.msg}`).join('; ');
  }
  if (typeof detail === 'object' && detail !== null) {
    return JSON.stringify(detail);
  }
  return err.response.data?.message || err.message || '请求处理异常';
}

export default api;
