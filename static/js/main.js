import { initTheme } from './modules/theme.js';
import { initCards } from './modules/card.js';
import { initToast, showToast } from './modules/toast.js';
import './modules/tags.js';

// Auto-attach CSRF token to all fetch requests
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
const originalFetch = window.fetch;
window.fetch = (url, options = {}) => {
    options.headers = {
        ...(options.headers || {}),
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
    };
    if (options.method && options.method.toUpperCase() !== 'GET') {
        options.headers['X-CSRF-Token'] = csrfToken || '';
    }
    return originalFetch(url, options);
};

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initCards();
    initToast();

    if (document.getElementById('video-player')) {
        import('./modules/player.js').then(m => m.initPlayer?.());
    }
});

window.showToast = showToast;
