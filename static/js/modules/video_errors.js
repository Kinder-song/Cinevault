export function initVideoErrorHandling() {
    const video = document.getElementById('video-player');
    if (!video) return;

    // Network status
    const offline = document.createElement('div');
    offline.className = 'offline-banner hidden';
    offline.setAttribute('role', 'status');
    offline.innerHTML = '<i data-lucide="wifi-off"></i> 网络已断开，正在尝试恢复...';
    document.body.appendChild(offline);

    function showOffline(show) {
        offline.classList.toggle('hidden', !show);
        if (window.lucide) window.lucide.createIcons();
    }

    window.addEventListener('online', () => showOffline(false));
    window.addEventListener('offline', () => showOffline(true));
    if (!navigator.onLine) showOffline(true);

    // Video error handling
    video.addEventListener('error', () => {
        const error = video.error;
        let msg = '视频加载失败';
        if (error) {
            switch (error.code) {
                case 1: msg = '视频加载被中止'; break;
                case 2: msg = '网络错误，无法加载视频'; break;
                case 3: msg = '视频解码失败（格式可能不受支持）'; break;
                case 4: msg = '视频源不可用或已损坏'; break;
            }
        }
        const overlay = document.createElement('div');
        overlay.className = 'video-error-overlay';
        overlay.setAttribute('role', 'alert');
        overlay.innerHTML = `
            <div class="video-error-content">
                <i data-lucide="alert-triangle" aria-hidden="true"></i>
                <p>${msg}</p>
                <button type="button" class="video-error-retry">重试</button>
            </div>
        `;
        // Use addEventListener (not inline onclick) to keep a11y lint clean.
        overlay.querySelector('.video-error-retry').addEventListener('click', () => location.reload());
        video.parentElement.appendChild(overlay);
        if (window.lucide) window.lucide.createIcons();
    });
}
