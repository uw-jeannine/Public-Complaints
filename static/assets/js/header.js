(function () {
    "use strict";

    // Header Scroll Effect
    window.addEventListener('scroll', function () {
        const header = document.getElementById('mainHeader');
        if (header) {
            if (window.scrollY > 50) {
                header.classList.add('scrolled');
                const scrollTopBtn = document.getElementById('scrollTop');
                if (scrollTopBtn) scrollTopBtn.style.display = 'flex';
            } else {
                header.classList.remove('scrolled');
                const scrollTopBtn = document.getElementById('scrollTop');
                if (scrollTopBtn) scrollTopBtn.style.display = 'none';
            }
        }
    });

    // Language switcher logic
    function applyLanguage(lang) {
        document.querySelectorAll('[data-en]').forEach(function (el) {
            el.textContent = el.getAttribute('data-' + lang) || el.getAttribute('data-en');
        });

        // Handle placeholders
        document.querySelectorAll('[data-en-placeholder]').forEach(function (el) {
            el.placeholder = el.getAttribute('data-' + lang + '-placeholder') || el.getAttribute('data-en-placeholder');
        });

        document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
        const activeBtn = document.getElementById('lang-' + lang);
        if (activeBtn) activeBtn.classList.add('active');
    }

    window.setLanguage = function (lang) {
        localStorage.setItem('lang', lang);
        applyLanguage(lang);
    };

    // Initialize on load
    window.addEventListener('DOMContentLoaded', function () {
        applyLanguage(localStorage.getItem('lang') || 'en');

        const scrollTopBtn = document.getElementById('scrollTop');
        if (scrollTopBtn) {
            scrollTopBtn.addEventListener('click', function () {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        }
    });
})();
