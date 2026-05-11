// Backend URLs to try in order.
// Keep the production HTTPS API first so Vercel pages don't fall back to same-origin static hosting.
window.API_BASE_URLS = [
  'https://loyola-rvgj.onrender.com',
  'http://127.0.0.1:8002',
  'http://127.0.0.1:8001',
  'http://127.0.0.1:8000'
];

window.API_BASE_URL = window.API_BASE_URLS[0] || '';

window.API_DEBUG_ENABLED = /[?&]apiDebug=1\b/.test(window.location.search) || (() => {
  try {
    return window.localStorage.getItem('LOYOLA_API_DEBUG') === '1';
  } catch {
    return false;
  }
})();

window.showApiDebug = function showApiDebug(baseUrl, mode) {
  if (!window.API_DEBUG_ENABLED) return;

  const label = (baseUrl || 'not resolved').trim() || 'not resolved';
  const suffix = mode ? ` (${mode})` : '';
  const text = `API ${label}${suffix}`;
  let badge = document.getElementById('loyola-api-debug-badge');

  if (!badge) {
    badge = document.createElement('div');
    badge.id = 'loyola-api-debug-badge';
    badge.style.position = 'fixed';
    badge.style.right = '10px';
    badge.style.bottom = '10px';
    badge.style.zIndex = '2147483647';
    badge.style.maxWidth = '80vw';
    badge.style.padding = '6px 10px';
    badge.style.borderRadius = '999px';
    badge.style.background = 'rgba(17, 37, 26, 0.9)';
    badge.style.color = '#ffffff';
    badge.style.fontSize = '12px';
    badge.style.fontFamily = 'Segoe UI, Verdana, sans-serif';
    badge.style.lineHeight = '1.2';
    badge.style.whiteSpace = 'nowrap';
    badge.style.overflow = 'hidden';
    badge.style.textOverflow = 'ellipsis';
    badge.style.boxShadow = '0 6px 18px rgba(0, 0, 0, 0.25)';
    badge.style.border = '1px solid rgba(255, 255, 255, 0.2)';
    badge.title = 'Append ?apiDebug=1 to URL to force API debug badge';
    document.body.appendChild(badge);
  }

  badge.textContent = text;
};
