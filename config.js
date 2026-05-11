// Backend URLs to try in order.
// Keep the production HTTPS API first so Vercel pages don't fall back to same-origin static hosting.
window.API_BASE_URLS = [
  'https://loyola-rvgj.onrender.com',
  'http://127.0.0.1:8002',
  'http://127.0.0.1:8001',
  'http://127.0.0.1:8000'
];

window.API_BASE_URL = window.API_BASE_URLS[0] || '';
