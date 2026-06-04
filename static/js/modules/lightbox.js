// Keyboard-accessible screenshot lightbox.
// - Escape closes
// - Tab focuses close button (dialog is focusable, close button is the first focusable child)
// - role=dialog, aria-modal=true
//
// Wiring (open-on-click / open-on-Enter-Space) lives in lightbox_wiring.js so this
// module stays single-purpose (create / dismiss the dialog).

let activeLightbox = null;

export function openLightbox(src, alt = '') {
    closeLightbox();
    const lb = document.createElement('div');
    lb.className = 'screenshot-lightbox';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.setAttribute('aria-label', alt || '图片预览');
    lb.tabIndex = -1;
    lb.innerHTML = `
        <button class="lightbox-close" aria-label="关闭预览">
            <i data-lucide="x" aria-hidden="true"></i>
        </button>
        <img src="${escapeAttr(src)}" alt="${escapeAttr(alt)}">
    `;
    document.body.appendChild(lb);
    if (window.lucide) window.lucide.createIcons();

    // Close handlers
    const closeBtn = lb.querySelector('.lightbox-close');
    closeBtn.addEventListener('click', closeLightbox);
    lb.addEventListener('click', (e) => {
        if (e.target === lb) closeLightbox();
    });
    document.addEventListener('keydown', onKey);

    // Focus the close button so the first Tab keeps the user inside the dialog
    // and Enter/Space activates closing (keyboard-only users get an obvious exit).
    closeBtn.focus();

    activeLightbox = lb;
}

function onKey(e) {
    if (e.key === 'Escape') closeLightbox();
}

export function closeLightbox() {
    if (!activeLightbox) return;
    document.removeEventListener('keydown', onKey);
    activeLightbox.remove();
    activeLightbox = null;
}

function escapeAttr(s) {
    return String(s).replace(/[&<>'"]/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[c]));
}

// Backwards compat for any legacy inline callers / window.openLightbox usage.
window.openLightbox = openLightbox;
window.closeLightbox = closeLightbox;
