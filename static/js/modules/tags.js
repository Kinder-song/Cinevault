import { refreshIcons } from './toast.js';

export function toggleTagEditor(event, el) {
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

export function handleTagInput(event, filename) {
    if (event.key === 'Enter') {
        const input = event.target;
        const tagName = input.value.trim();
        if (!tagName) return;
        addTag(filename, tagName, input);
    }
}

export async function addTag(filename, tagName, inputEl) {
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

export async function deleteTag(event, filename, tagName) {
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