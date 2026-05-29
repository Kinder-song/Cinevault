import { initTheme } from './modules/theme.js';
import { initCards } from './modules/card.js';
import { initToast, showToast } from './modules/toast.js';
import { initFilter } from './modules/filter.js';

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initCards();
    initToast();
    initFilter();

    // Dynamic import player if on video page
    if (document.getElementById('video-player')) {
        import('./modules/player.js').then(m => m.initPlayer?.());
    }
});

window.showToast = showToast;