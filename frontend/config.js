// Backend URLs to try in order.
// 1) Put your PUBLIC backend URL first (required for all devices on any network).
// 2) Keep LAN and localhost as fallback for local testing.
// Replace the first value below with your deployed backend URL.
window.API_BASE_URLS = [
	'https://loyola-rvgj.onrender.com',
	'http://10.179.54.212:8000',
	'http://127.0.0.1:8000'
];

// Backward compatibility: if old code reads API_BASE_URL, keep first value.
window.API_BASE_URL = window.API_BASE_URLS[0] || '';
