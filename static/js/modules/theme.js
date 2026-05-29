import { refreshIcons } from './toast.js';

export function initTheme() {
    const savedTheme = localStorage.getItem('cinevault-theme');
    if (savedTheme) {
        if (savedTheme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
        updateThemeIcon(savedTheme);
    } else {
        // Follow system preference, but DON'T persist - manual toggle only
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) {
            document.documentElement.removeAttribute('data-theme');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
        }
        // Icon reflects what clicking will switch TO (light mode → show sun, dark mode → show moon)
        updateThemeIcon(prefersDark ? 'light' : 'dark');
    }

    // Listen for system preference changes - only if no manual preference saved
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('cinevault-theme')) {
            if (e.matches) {
                document.documentElement.removeAttribute('data-theme');
                // Show sun icon because clicking will switch to light (the opposite)
                updateThemeIcon('light');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                // Show moon icon because clicking will switch to dark (the opposite)
                updateThemeIcon('dark');
            }
        }
    });
}

export function toggleTheme() {
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
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
    } else {
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
    }
}

window.toggleTheme = toggleTheme;