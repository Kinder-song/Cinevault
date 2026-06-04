let commentsLoaded = false;

export async function loadComments() {
    if (commentsLoaded) return;
    const video = document.getElementById('video-player');
    if (!video?.dataset?.filename) return;
    try {
        const res = await fetch(`/api/video/${encodeURIComponent(video.dataset.filename)}/comments`);
        const data = await res.json();
        renderComments(data.comments || []);
        commentsLoaded = true;
    } catch (err) {
        console.error('Load comments error:', err);
    }
}

function renderComments(comments) {
    const list = document.getElementById('comments-list');
    if (!list) return;
    list.innerHTML = comments.length
        ? comments.map(c => `
            <div class="comment-item">
                <div class="comment-meta">
                    <span>${escape(c.username || 'anonymous')}</span>
                    <span>${new Date(c.created_at).toLocaleString('zh-CN')}</span>
                </div>
                <div class="comment-content">${escape(c.content)}</div>
            </div>
        `).join('')
        : '<p class="empty-state">还没有评论</p>';
}

function escape(s) {
    return String(s).replace(/[&<>'"]/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[c]));
}

window.postComment = async function() {
    const input = document.getElementById('comment-input');
    const content = input.value.trim();
    if (!content) return;
    const video = document.getElementById('video-player');
    try {
        const res = await fetch(`/api/video/${encodeURIComponent(video.dataset.filename)}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        });
        const data = await res.json();
        if (data.success) {
            input.value = '';
            commentsLoaded = false;
            await loadComments();
            if (window.showToast) window.showToast('评论已发表', 'success');
        } else {
            if (window.showToast) window.showToast(data.error || '发表失败', 'error');
        }
    } catch (err) {
        if (window.showToast) window.showToast('网络错误', 'error');
    }
};

// Attach submit listener only after the form exists in the DOM.
// We use DOMContentLoaded instead of the IIFE top-level so this module
// can be safely imported on pages that don't have a comment form
// (e.g. the home page). The `onsubmit` attribute on the form is also
// kept as a defense-in-depth fallback.
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('comment-form');
    if (!form) return;
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        window.postComment();
    });
});
