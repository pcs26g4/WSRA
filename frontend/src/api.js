import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    headers: { 'Content-Type': 'application/json' }
});


export const startScan = async (url) => {
  const response = await api.post('/scan/start', { url });
  return response.data;
};

export const getScanStatus = async (scanId) => {
  const response = await api.get(`/scan/${scanId}/status`);
  return response.data;
};

export const getScanSummary = async (scanId) => {
  const response = await api.get(`/scan/${scanId}/summary`);
  return response.data;
};

export const getScans = async (limit = 50) => {
  const response = await api.get(`/scans?limit=${limit}`);
  return response.data;
};

export const deleteScan = async (scanId) => {
  const response = await api.delete(`/scan/${scanId}`);
  return response.data;
};

export const exportScan = async (scanId, format) => {
    // format: 'json', 'markdown', 'burp', 'csv'
    const response = await api.get(`/scan/${scanId}/export/${format}`, {
        responseType: 'blob'
    });
    return response.data;
}

export const analyzeVulnerabilities = async (scanId) => {
    const response = await api.post(`/scan/${scanId}/analyze-vulnerabilities`);
    return response.data;
}

export const getVulnerabilityHints = async (scanId) => {
    const response = await api.get(`/scan/${scanId}/hints`);
    return response.data;
}

export default api;
