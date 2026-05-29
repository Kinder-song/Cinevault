import { refreshIcons } from './toast.js';

let previewTimeout = null;
const activePreviews = [];
const MAX_CONCURRENT_PREVIEWS = 3;

export function createPreviewVideo(card) {
    const container = card.querySelector('.preview-container');
    if (!container) return null;
    let video = container.querySelector('video');
    if (video) return video;
    const filename = card.dataset.filename;
    if (!filename) return null;
    video = document.createElement('video');
    video.className = 'preview-video';
    video.muted = true;
    video.loop = true;
    video.playsInline = true;
    video.preload = 'none';
    video.src = '/stream/' + encodeURIComponent(filename);
    container.appendChild(video);
    return video;
}

export function destroyPreviewVideo(card) {
    const container = card.querySelector('.preview-container');
    if (!container) return;
    const video = container.querySelector('video');
    if (video) {
        video.pause();
        video.src = '';
        video.load();
        video.remove();
    }
}

export function initCards() {
    document.querySelectorAll('.video-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            previewTimeout = setTimeout(() => {
                if (activePreviews.length >= MAX_CONCURRENT_PREVIEWS) {
                    const oldest = activePreviews.shift();
                    oldest.pause();
                    oldest.closest('.video-card')?.classList.remove('previewing');
                    destroyPreviewVideo(oldest.closest('.video-card'));
                }
                const video = createPreviewVideo(card);
                if (!video) return;
                video.currentTime = 0;
                video.play().catch(() => {});
                card.classList.add('previewing');
                activePreviews.push(video);
            }, 600);
        });

        card.addEventListener('mouseleave', () => {
            clearTimeout(previewTimeout);
            card.classList.remove('previewing');
            const container = card.querySelector('.preview-container');
            if (container) {
                const video = container.querySelector('video');
                if (video) {
                    const idx = activePreviews.indexOf(video);
                    if (idx > -1) activePreviews.splice(idx, 1);
                    video.pause();
                }
            }
            setTimeout(() => destroyPreviewVideo(card), 300);
        });

        // RAF-throttled flow light
        const flowLight = card.querySelector('.flow-light');
        if (flowLight) {
            let ticking = false;
            let lastX = 0, lastY = 0;
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                lastX = e.clientX - rect.left;
                lastY = e.clientY - rect.top;
                if (!ticking) {
                    requestAnimationFrame(() => {
                        flowLight.style.left = lastX + 'px';
                        flowLight.style.top = lastY + 'px';
                        ticking = false;
                    });
                    ticking = true;
                }
            });
        }
    });
}