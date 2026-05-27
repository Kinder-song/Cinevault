// ==================== Hover Preview ====================
let previewTimeout = null;
let activePreviews = [];
const MAX_CONCURRENT_PREVIEWS = 3;

document.querySelectorAll('.video-card').forEach(card => {
    const video = card.querySelector('.preview-video');
    if (!video) return;

    card.addEventListener('mouseenter', () => {
        previewTimeout = setTimeout(() => {
            if (activePreviews.length >= MAX_CONCURRENT_PREVIEWS) {
                const oldest = activePreviews.shift();
                oldest.pause();
                oldest.currentTime = 0;
                oldest.closest('.video-card')?.classList.remove('previewing');
            }

            video.currentTime = 0;
            video.play().catch(() => {});
            card.classList.add('previewing');
            activePreviews.push(video);
        }, 500);
    });

    card.addEventListener('mouseleave', () => {
        clearTimeout(previewTimeout);
        video.pause();
        video.currentTime = 0;
        card.classList.remove('previewing');
        const idx = activePreviews.indexOf(video);
        if (idx > -1) activePreviews.splice(idx, 1);
    });
});

// ==================== Flow Light Effect ====================
document.querySelectorAll('.video-card').forEach(card => {
    const flowLight = card.querySelector('.flow-light');
    if (!flowLight) return;

    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        flowLight.style.left = x + 'px';
        flowLight.style.top = y + 'px';
    });
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
        const res = await fetch(`/api/video/${filename}/tags`, {
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
            pill.style.cssText = `background: ${color}20; color: ${color}; border-color: ${color}40;`;
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
            lucide.createIcons();

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
        const res = await fetch(`/api/video/${filename}/tags/${tagName}`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (data.success && pill) {
            pill.style.animation = 'tagPop 0.2s ease reverse';
            setTimeout(() => pill.remove(), 200);
        }
    } catch (err) {
        console.error('Delete tag error:', err);
    }
}

// ==================== Video Player ====================
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
    });

    video.addEventListener('timeupdate', () => {
        if (progressPlayed && video.duration) {
            const pct = (video.currentTime / video.duration) * 100;
            progressPlayed.style.width = pct + '%';
        }
        if (currentTimeEl) currentTimeEl.textContent = formatTime(video.currentTime);
    });

    playBtn?.addEventListener('click', () => togglePlay(video, playBtn));
    muteBtn?.addEventListener('click', () => toggleMute(video, muteBtn));
    volumeSlider?.addEventListener('input', (e) => setVolume(video, e.target.value));
    speedSelect?.addEventListener('change', (e) => setSpeed(video, e.target.value));
    fullscreenBtn?.addEventListener('click', () => toggleFullscreen(video));
    progressBar?.addEventListener('click', (e) => seek(video, e));

    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT') return;

        switch(e.code) {
            case 'Space':
                e.preventDefault();
                togglePlay(video, playBtn);
                break;
            case 'ArrowLeft':
                video.currentTime = Math.max(0, video.currentTime - 5);
                break;
            case 'ArrowRight':
                video.currentTime = Math.min(video.duration, video.currentTime + 5);
                break;
            case 'ArrowUp':
                e.preventDefault();
                setVolume(video, Math.min(100, video.volume * 100 + 10));
                break;
            case 'ArrowDown':
                e.preventDefault();
                setVolume(video, Math.max(0, video.volume * 100 - 10));
                break;
        }
    });
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
    lucide.createIcons();
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
    if (document.fullscreenElement) {
        document.exitFullscreen();
    } else {
        video.parentElement.requestFullscreen();
    }
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

    lucide.createIcons();
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