// Backend URLs to try in order. Put your public URL first when deployed.
// Example:
// window.API_BASE_URLS = ['https://loyola-admissions-api.onrender.com', 'http://10.179.54.212:8000'];
window.API_BASE_URLS = [
	'http://10.179.54.212:8000'
];

// Backward compatibility: if old code reads API_BASE_URL, keep first value.
window.API_BASE_URL = window.API_BASE_URLS[0] || '';
