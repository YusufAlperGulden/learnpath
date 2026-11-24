import axios from 'axios';

export const ACCESS_TOKEN_STORAGE_KEY = 'learnpath_access_token';

const explicitBaseUrl = import.meta.env.VITE_API_BASE_URL;
const renderApiHost = import.meta.env.VITE_API_HOST;
const baseURL =
  explicitBaseUrl || (renderApiHost ? `https://${renderApiHost}/api/v1` : '/api/v1');

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
