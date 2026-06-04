import { initTheme } from './modules/theme.js';
import { initCards } from './modules/card.js';
import { initToast, showToast } from './modules/toast.js';
import { loadComments } from './modules/comments.js';
import { toggleTagEditor, deleteTag } from './modules/tags.js';
import { initVideoErrorHandling } from './modules/video_errors.js';
import { initLightboxDelegation } from './modules/lightbox_wiring.js';
import { maybeShowOnboarding } from './modules/onboarding.js';
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

// Event delegation for tag add/remove (replaces inline onclick on .tag-delete / .tag-add-btn).
// Video cards are now <a> elements — these clicks must prevent the anchor navigation
// and stop propagation so the card itself doesn't also fire.
document.addEventListener('click', (e) => {
    const tagDelete = e.target.closest('.tag-delete');
    if (tagDelete) {
        e.preventDefault();
        e.stopPropagation();
        const card = tagDelete.closest('.video-card');
        const filename = card?.dataset?.filename;
        const tagName = tagDelete.dataset?.tag;
        if (filename && tagName) deleteTag({ stopPropagation: () => {} }, filename, tagName);
        return;
    }
    const tagAdd = e.target.closest('.tag-add-btn');
    if (tagAdd) {
        e.preventDefault();
        e.stopPropagation();
        const card = tagAdd.closest('.video-card');
        if (card) toggleTagEditor({ stopPropagation: () => {} }, card);
    }
});

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initCards();
    initToast();

    if (document.getElementById('video-player')) {
        import('./modules/player.js').then(m => m.initPlayer?.());
        loadComments();
        initVideoErrorHandling();
        initLightboxDelegation();
    }

    // Show onboarding on first visit (not first-login forced password change)
    if (!window.location.search.includes('first_login=1')) {
        maybeShowOnboarding();
    }
});

window.showToast = showToast;
