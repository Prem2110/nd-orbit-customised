import axios from 'axios';

const api = axios.create({ baseURL: `${import.meta.env.VITE_API_BASE_URL || ''}/api` });

export const getDashboardKpis = () => api.get('/dashboard/kpis');
export const getProcessHealth = () => api.get('/dashboard/process-health');
export const getLogDetail = (id) => api.get(`/logs/${id}/detail`);
export const startIngestion = () => api.post('/ingest/start');
export const getIngestionStatus = () => api.get('/ingest/status');
