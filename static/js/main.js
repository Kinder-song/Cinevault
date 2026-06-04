import { initTheme } from './modules/theme.js';
import { initCards } from './modules/card.js';
import { initToast, showToast } from './modules/toast.js';
import './modules/tags.js';

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initCards();
    initToast();

    // Dynamic import player if on video page
    if (document.getElementById('video-player')) {
        import('./modules/player.js').then(m => m.initPlayer?.());
    }
});

window.showToast = showToast;