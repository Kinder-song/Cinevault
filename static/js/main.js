// ==================== Icon Refresh Debounce ====================
let iconRefreshTimer = null;
function refreshIcons() {
    clearTimeout(iconRefreshTimer);
    iconRefreshTimer = setTimeout(() => {
        if (window.lucide) lucide.createIcons();
    }, 30);
}

// ==================== Toast Notifications ====================
function showToast(message, type = 'info', duration = 3000) {
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

// ==================== Theme Toggle ====================
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    if (newTheme === 'dark') {
        html.removeAttribute('data-theme');
    } else {
        html.setAttribute('data-theme', 'light');
    }

    localStorage.setItem('cinevault-theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    if (!sunIcon || !moonIcon) return;
    if (theme === 'light') {
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
    } else {
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
    }
}

function initTheme() {
    const savedTheme = localStorage.getItem('cinevault-theme') || 'dark';
    if (savedTheme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    }
    updateThemeIcon(savedTheme);
}

document.addEventListener('DOMContentLoaded', initTheme);

// ==================== Lazy Hover Preview ====================
let previewTimeout = null;
let activePreviews = [];
const MAX_CONCURRENT_PREVIEWS = 3;

function createPreviewVideo(card) {
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

function destroyPreviewVideo(card) {
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

// ==================== Card Setup ====================
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

// ==================== Tag Management ====================
function toggleTagEditor(event, el) {
    event.stopPropagation();
    const card = el.closest('.video-card');
    if (!card) return;
    const editor = card.querySelector('.tag-editor');
    if (!editor) return;
    const isHidden = editor.classList.contains('hidden');
    document.querySelectorAll('.tag-editor').forEach(e => e.classList.add('hidden'));
    if (isHidden) {
        editor.classList.remove('hidden');
        editor.querySelector('input')?.focus();
    }
}

function handleTagInput(event, filename) {
    if (event.key === 'Enter') {
        const input = event.target;
        const tagName = input.value.trim();
        if (!tagName) return;
        addTag(filename, tagName, input);
    }
}

async function addTag(filename, tagName, inputEl) {
    try {
        const res = await fetch('/api/video/' + encodeURIComponent(filename) + '/tags', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({tag: tagName})
        });
        const data = await res.json();
        if (data.success) {
            const card = inputEl.closest('.video-card');
            const tagsContainer = card.querySelector('.card-tags');
            const addBtn = tagsContainer.querySelector('.tag-add-btn');
            const tagColors = ['#7b9cff', '#D4A373', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444'];
            const color = tagColors[Math.floor(Math.random() * tagColors.length)];
            const pill = document.createElement('span');
            pill.className = 'tag-pill';
            pill.style.cssText = 'background: ' + color + '20; color: ' + color + '; border-color: ' + color + '40;';
            pill.textContent = tagName;
            const btn = document.createElement('button');
            btn.className = 'tag-delete';
            btn.onclick = (evt) => deleteTag(evt, filename, tagName);
            const icon = document.createElement('i');
            icon.setAttribute('data-lucide', 'x');
            icon.className = 'w-3 h-3';
            btn.appendChild(icon);
            pill.appendChild(btn);
            tagsContainer.insertBefore(pill, addBtn);

            // Update dataset for search
            const existing = card.dataset.tags ? card.dataset.tags.split(',') : [];
            existing.push(tagName);
            card.dataset.tags = existing.join(',');

            refreshIcons();
            inputEl.value = '';
            inputEl.closest('.tag-editor').classList.add('hidden');
        }
    } catch (err) {
        console.error('Add tag error:', err);
    }
}

async function deleteTag(event, filename, tagName) {
    event.stopPropagation();
    const pill = event.target.closest('.tag-pill');
    try {
        const res = await fetch('/api/video/' + encodeURIComponent(filename) + '/tags/' + encodeURIComponent(tagName), {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success && pill) {
            // Update dataset for search
            const card = pill.closest('.video-card');
            if (card && card.dataset.tags) {
                const tags = card.dataset.tags.split(',').filter(t => t !== tagName);
                card.dataset.tags = tags.join(',');
            }
            pill.style.animation = 'tagPop 0.2s ease reverse';
            setTimeout(() => pill.remove(), 200);
        }
    } catch (err) {
        console.error('Delete tag error:', err);
    }
}

// ==================== Video Player ====================
let progressSyncTimer = null;
let progressRafId = null;

function initVideoPlayer() {
    const video = document.getElementById('video-player');
    if (!video) return;

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

function saveProgress(video) {
    if (!video || !video.dataset.filename || !video.duration) return;
    const current = Math.floor(video.currentTime);
    if (current <= 0) return;
    // Only save if > 3% into the video
    if (current < video.duration * 0.03) return;
    fetch('/api/video/' + encodeURIComponent(video.dataset.filename) + '/progress', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({progress: current})
    }).catch(() => {});
}

function togglePlay(video, btn) {
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

function toggleMute(video, btn) {
    if (!btn) return;
    video.muted = !video.muted;
    const icon = btn.querySelector('i');
    if (icon) icon.setAttribute('data-lucide', video.muted ? 'volume-x' : 'volume-2');
    refreshIcons();
}

function setVolume(video, val) {
    video.volume = val / 100;
    const slider = document.querySelector('.volume-slider');
    if (slider) slider.value = val;
}

function setSpeed(video, speed) {
    video.playbackRate = parseFloat(speed);
}

function toggleFullscreen(video) {
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

function initFullscreenListener() {
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

function seek(video, e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    video.currentTime = pct * video.duration;
}

function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return h + ':' + m.toString().padStart(2, '0') + ':' + s.toString().padStart(2, '0');
    return m + ':' + s.toString().padStart(2, '0');
}

// ==================== Player Page Tag Management ====================
function handlePlayerTagInput(event) {
    if (event.key === 'Enter') {
        addTagToVideo();
    }
}

async function addTagToVideo() {
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

function renderPlayerTags(tags) {
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

async function deletePlayerTag(event, tagName) {
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

// ==================== Init on player page ====================
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('video-player')) {
        initFullscreenListener();
    }
});
