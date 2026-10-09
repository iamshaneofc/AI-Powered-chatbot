import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
});

// Add a response interceptor for unified error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Request Failed:', error);
    let errorMessage = 'An unexpected error occurred.';
    
    if (error.response) {
      // The server responded with a status code outside the 2xx range
      errorMessage = error.response.data?.message || error.response.data?.detail || `Server Error: ${error.response.status}`;
    } else if (error.request) {
      // The request was made but no response was received
      errorMessage = 'Network Error: Cannot connect to the server. Please ensure the backend is running.';
    } else {
      // Something happened in setting up the request that triggered an Error
      errorMessage = error.message;
    }
    
    // Return a normalized error that components can easily display
    return Promise.reject(new Error(errorMessage));
  }
);

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload/pdf', formData);
  return response.data;
};

export const uploadMedia = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload/media', formData);
  return response.data;
};

export const sendChat = async (question) => {
  const response = await api.post('/chat', {
    question,
    top_k: 5
  });
  return response.data;
};

export const fetchSummary = async (filename) => {
  // Mock endpoint as it wasn't strictly implemented in backend yet
  const response = await api.post('/summarize', { filename });
  return response.data;
};

export const resetApp = async () => {
  const response = await api.delete('/reset');
  return response.data;
};

// Settings API
export const getProviders = async () => {
  const response = await api.get('/settings/providers');
  return response.data;
};

export const getCurrentSettings = async () => {
  const response = await api.get('/settings/current');
  return response.data;
};

export const updateSettings = async (settings) => {
  const response = await api.put('/settings/update', settings);
  return response.data;
};

export const testProvider = async (provider, apiKey, baseUrl) => {
  const response = await api.post('/settings/test', {
    provider,
    api_key: apiKey,
    base_url: baseUrl,
  });
  return response.data;
};

export const getProviderModels = async (providerId) => {
  const response = await api.get(`/settings/models/${providerId}`);
  return response.data;
};

export default api;
