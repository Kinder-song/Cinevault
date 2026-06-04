// Event delegation that opens the lightbox for any `[data-lightbox-src]` element.
// Handles both click and Enter/Space activation so thumbs are keyboard-reachable
// when they are non-button elements (e.g. an <img tabindex="0" role="button">).

import { openLightbox } from './lightbox.js';

let wired = false;

export function initLightboxDelegation() {
    // Guard against double-wiring if this is ever called more than once.
    if (wired) return;
    wired = true;

    document.addEventListener('click', (e) => {
        const thumb = e.target.closest('[data-lightbox-src]');
        if (thumb) {
            openLightbox(thumb.dataset.lightboxSrc, thumb.alt || '');
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        const thumb = e.target.closest('[data-lightbox-src]');
        if (thumb) {
            e.preventDefault();
            openLightbox(thumb.dataset.lightboxSrc, thumb.alt || '');
        }
    });
}
