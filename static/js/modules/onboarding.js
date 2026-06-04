const STORAGE_KEY = 'cinevault-onboarded';

export function maybeShowOnboarding() {
    if (localStorage.getItem(STORAGE_KEY)) return;
    const overlay = document.createElement('div');
    overlay.className = 'onboarding-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'onboarding-title');
    overlay.innerHTML = `
        <div class="onboarding-modal">
            <h2 id="onboarding-title">快速上手 CineVault</h2>
            <ul class="onboarding-tips">
                <li><kbd>Space</kbd> 播放/暂停</li>
                <li><kbd>J</kbd> / <kbd>L</kbd> 后退/前进 10 秒</li>
                <li><kbd>↑</kbd> / <kbd>↓</kbd> 音量 ±10%</li>
                <li><kbd>0</kbd>-<kbd>9</kbd> 跳到 0%–90%</li>
                <li><kbd>F</kbd> 全屏，<kbd>T</kbd> 影院模式，<kbd>M</kbd> 静音</li>
            </ul>
            <p>把视频放进 <code>video/</code> 目录，刷新页面即自动入库。</p>
            <button class="onboarding-close">开始</button>
        </div>
    `;
    document.body.appendChild(overlay);
    overlay.querySelector('.onboarding-close').addEventListener('click', () => {
        localStorage.setItem(STORAGE_KEY, '1');
        overlay.remove();
    });
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            localStorage.setItem(STORAGE_KEY, '1');
            overlay.remove();
        }
    });
    document.addEventListener('keydown', function escClose(e) {
        if (e.key === 'Escape') {
            localStorage.setItem(STORAGE_KEY, '1');
            overlay.remove();
            document.removeEventListener('keydown', escClose);
        }
    });
}
