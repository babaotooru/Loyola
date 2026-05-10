// Backend URLs to try in order.
// Keep localhost first for development so the latest local backend is used.
window.API_BASE_URLS = [
  'http://127.0.0.1:8002',
  'http://127.0.0.1:8001',
  'http://127.0.0.1:8000',
  'http://10.179.54.212:8002',
  'https://loyola-rvgj.onrender.com'
];

window.API_BASE_URL = window.API_BASE_URLS[0] || '';
