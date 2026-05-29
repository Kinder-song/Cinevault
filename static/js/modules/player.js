import { refreshIcons } from './toast.js';

let progressSyncTimer = null;

export function initPlayer() {
    const video = document.getElementById('video-player');
    if (!video) return;

    initFullscreenListener();

    const playBtn = document.getElementById('play-btn');
    const muteBtn = document.getElementById('mute-btn');
    const volumeSlider = document.querySelector('.volume-slider');
    const speedSelect = document.getElementById('speed-select');
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    const progressBar = document.getElementById('progress-bar');
    const progressPlayed = document.getElementById('progress-played');
    const currentTimeEl = document.getElementById('current-time');
    const totalTimeEl = document.getElementById('total-time');

    video.addEventListener('loadedmetadata', () => {
        if (totalTimeEl) totalTimeEl.textContent = formatTime(video.duration);
        const saved = video.dataset.progress;
        if (saved && parseInt(saved) > 0) {
            video.currentTime = parseInt(saved);
        }
    });

    // RAF-batched timeupdate: avoid DOM mutations on every event (~4/sec)
    let timeUpdateDirty = false;
    video.addEventListener('timeupdate', () => {
        if (!timeUpdateDirty) {
            timeUpdateDirty = true;
            requestAnimationFrame(() => {
                timeUpdateDirty = false;
                if (progressPlayed && video.duration) {
                    progressPlayed.style.width = ((video.currentTime / video.duration) * 100) + '%';
                }
                if (currentTimeEl) {
                    currentTimeEl.textContent = formatTime(video.currentTime);
                }
            });
        }

        clearTimeout(progressSyncTimer);
        progressSyncTimer = setTimeout(() => {
            saveProgress(video);
        }, 5000);
    });

    // Save progress on pause/ended
    video.addEventListener('pause', () => saveProgress(video));
    video.addEventListener('ended', () => saveProgress(video));

    playBtn?.addEventListener('click', () => togglePlay(video, playBtn));
    muteBtn?.addEventListener('click', () => toggleMute(video, muteBtn));
    volumeSlider?.addEventListener('input', (e) => setVolume(video, e.target.value));
    speedSelect?.addEventListener('change', (e) => setSpeed(video, e.target.value));
    fullscreenBtn?.addEventListener('click', () => toggleFullscreen(video));
    progressBar?.addEventListener('click', (e) => seek(video, e));

    // Enhanced keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;

        switch(e.code) {
            case 'Space':
                e.preventDefault();
                togglePlay(video, playBtn);
                break;
            case 'ArrowLeft':
                e.preventDefault();
                video.currentTime = Math.max(0, video.currentTime - 5);
                break;
            case 'ArrowRight':
                e.preventDefault();
                video.currentTime = Math.min(video.duration || 0, video.currentTime + 5);
                break;
            case 'KeyJ':
                e.preventDefault();
                video.currentTime = Math.max(0, video.currentTime - 10);
                break;
            case 'KeyL':
                e.preventDefault();
                video.currentTime = Math.min(video.duration || 0, video.currentTime + 10);
                break;
            case 'KeyK':
                e.preventDefault();
                togglePlay(video, playBtn);
                break;
            case 'ArrowUp':
                e.preventDefault();
                setVolume(video, Math.min(100, (video.volume || 1) * 100 + 10));
                break;
            case 'ArrowDown':
                e.preventDefault();
                setVolume(video, Math.max(0, (video.volume || 1) * 100 - 10));
                break;
            case 'KeyF':
                e.preventDefault();
                toggleFullscreen(video);
                break;
            case 'KeyT':
                e.preventDefault();
                document.getElementById('theater-btn')?.click();
                break;
            case 'KeyP':
                e.preventDefault();
                document.getElementById('pip-btn')?.click();
                break;
            case 'KeyM':
                e.preventDefault();
                toggleMute(video, muteBtn);
                break;
            case 'Digit0': case 'Digit1': case 'Digit2': case 'Digit3': case 'Digit4':
            case 'Digit5': case 'Digit6': case 'Digit7': case 'Digit8': case 'Digit9':
                e.preventDefault();
                const pct = parseInt(e.code.replace('Digit', '')) * 10;
                if (video.duration) video.currentTime = (pct / 100) * video.duration;
                break;
        }
    });
}

export function saveProgress(video) {
    if (!video || !video.dataset.filename || !video.duration) return;
    const current = Math.floor(video.currentTime);
    if (current <= 0) return;
    if (current < video.duration * 0.03) return;
    fetch('/api/video/' + encodeURIComponent(video.dataset.filename) + '/progress', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({progress: current})
    }).catch(() => {});
}

export function togglePlay(video, btn) {
    if (!btn) return;
    if (video.paused) {
        video.play();
        const playIcon = btn.querySelector('.play-icon');
        const pauseIcon = btn.querySelector('.pause-icon');
        if (playIcon) playIcon.classList.add('hidden');
        if (pauseIcon) pauseIcon.classList.remove('hidden');
    } else {
        video.pause();
        const playIcon = btn.querySelector('.play-icon');
        const pauseIcon = btn.querySelector('.pause-icon');
        if (playIcon) playIcon.classList.remove('hidden');
        if (pauseIcon) pauseIcon.classList.add('hidden');
    }
}

export function toggleMute(video, btn) {
    if (!btn) return;
    video.muted = !video.muted;
    const icon = btn.querySelector('i');
    if (icon) icon.setAttribute('data-lucide', video.muted ? 'volume-x' : 'volume-2');
    refreshIcons();
}

export function setVolume(video, val) {
    video.volume = val / 100;
    const slider = document.querySelector('.volume-slider');
    if (slider) slider.value = val;
}

export function setSpeed(video, speed) {
    video.playbackRate = parseFloat(speed);
}

export function toggleFullscreen(video) {
    const wrapper = video.closest('.video-wrapper');
    if (!wrapper) return;
    const isFullscreen = document.fullscreenElement || document.webkitFullscreenElement;
    if (isFullscreen) {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        }
    } else {
        if (wrapper.requestFullscreen) {
            wrapper.requestFullscreen();
        } else if (wrapper.webkitRequestFullscreen) {
            wrapper.webkitRequestFullscreen();
        }
    }
}

export function initFullscreenListener() {
    const video = document.getElementById('video-player');
    if (!video) return;
    const fsBtn = document.getElementById('fullscreen-btn');
    if (!fsBtn) return;
    const onFsChange = () => {
        const icon = fsBtn.querySelector('i');
        const isFullscreen = document.fullscreenElement || document.webkitFullscreenElement;
        icon?.setAttribute('data-lucide', isFullscreen ? 'minimize' : 'maximize');
        refreshIcons();
    };
    document.addEventListener('fullscreenchange', onFsChange);
    document.addEventListener('webkitfullscreenchange', onFsChange);
}

export function seek(video, e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    video.currentTime = pct * video.duration;
}

export function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return h + ':' + m.toString().padStart(2, '0') + ':' + s.toString().padStart(2, '0');
    return m + ':' + s.toString().padStart(2, '0');
}

// ==================== Player Page Tag Management ====================
export function handlePlayerTagInput(event) {
    if (event.key === 'Enter') {
        addTagToVideo();
    }
}

export async function addTagToVideo() {
    const input = document.getElementById('new-tag-input');
    const video = document.getElementById('video-player');
    if (!input || !video?.dataset?.filename) return;
    const tagName = input.value.trim();
    if (!tagName) return;
    const filename = video.dataset.filename;
    try {
        const res = await fetch('/api/video/' + encodeURIComponent(filename) + '/tags', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({tag: tagName})
        });
        const data = await res.json();
        if (data.success) {
            const tagColors = ['#7b9cff', '#D4A373', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444'];
            const color = tagColors[Math.floor(Math.random() * tagColors.length)];
            window.currentTags.push({name: tagName, color: color});
            renderPlayerTags(window.currentTags);
            input.value = '';
        }
    } catch (err) {
        console.error('Add tag error:', err);
    }
}

export function renderPlayerTags(tags) {
    const container = document.getElementById('tags-container');
    if (!container) return;
    container.innerHTML = '';
    tags.forEach(tag => {
        const pill = document.createElement('span');
        pill.className = 'tag-pill';
        pill.style.cssText = 'background: ' + tag.color + '20; color: ' + tag.color + '; border-color: ' + tag.color + '40;';
        pill.textContent = tag.name;
        const btn = document.createElement('button');
        btn.className = 'tag-delete';
        btn.onclick = (evt) => deletePlayerTag(evt, tag.name);
        const icon = document.createElement('i');
        icon.setAttribute('data-lucide', 'x');
        icon.className = 'w-3 h-3';
        btn.appendChild(icon);
        pill.appendChild(btn);
        container.appendChild(pill);
    });
    refreshIcons();
}

export async function deletePlayerTag(event, tagName) {
    event.stopPropagation();
    const video = document.getElementById('video-player');
    if (!video?.dataset?.filename) return;
    const filename = video.dataset.filename;
    try {
        const res = await fetch('/api/video/' + encodeURIComponent(filename) + '/tags/' + encodeURIComponent(tagName), {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            window.currentTags = window.currentTags.filter(t => t.name !== tagName);
            renderPlayerTags(window.currentTags);
        }
    } catch (err) {
        console.error('Delete tag error:', err);
    }
}