let iconRefreshTimer = null;

export function refreshIcons() {
    clearTimeout(iconRefreshTimer);
    iconRefreshTimer = setTimeout(() => {
        if (window.lucide) window.lucide.createIcons();
    }, 30);
}

export function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

export function initToast() {}

window.showToast = showToast;