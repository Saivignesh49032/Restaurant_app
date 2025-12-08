// Simple Dark Mode Toggle - Clean Implementation
(function () {
    'use strict';

    // Toggle dark mode
    window.toggleDarkMode = function () {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        // Update icon
        const toggle = document.getElementById('dark-mode-toggle');
        if (toggle) {
            const icon = toggle.querySelector('i');
            if (icon) {
                if (newTheme === 'dark') {
                    icon.className = 'fas fa-sun';
                } else {
                    icon.className = 'fas fa-moon';
                }
            }
        }
    };

    // Initialize on page load
    function init() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);

        // Update icon
        const toggle = document.getElementById('dark-mode-toggle');
        if (toggle) {
            const icon = toggle.querySelector('i');
            if (icon && savedTheme === 'dark') {
                icon.className = 'fas fa-sun';
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
