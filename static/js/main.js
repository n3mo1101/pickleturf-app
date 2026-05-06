/* ============================================================
   PICKLETURF — MAIN JS
   Sidebar · Dark Mode · FAB
   ============================================================ */

/* ── Theme ───────────────────────────────────────────────────── */
(function () {
    const saved = localStorage.getItem('pt-theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
})();

function toggleTheme() {
    const html    = document.documentElement;
    const current = html.getAttribute('data-theme') || 'light';
    const next    = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('pt-theme', next);
    updateThemeBtn(next);
}

function updateThemeBtn(theme) {
    const btn = document.getElementById('themeToggleBtn');
    if (!btn) return;
    const isDark = theme === 'dark';
    btn.innerHTML = isDark
        ? '<i class="bi bi-sun-fill"></i><span>Light Mode</span>'
        : '<i class="bi bi-moon-fill"></i><span>Dark Mode</span>';
}

/* ── Sidebar ─────────────────────────────────────────────────── */
function openSidebar() {
    document.getElementById('ptSidebar')?.classList.add('show');
    document.getElementById('ptOverlay')?.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeSidebar() {
    document.getElementById('ptSidebar')?.classList.remove('show');
    document.getElementById('ptOverlay')?.classList.remove('show');
    document.body.style.overflow = '';
}

/* ── FAB ─────────────────────────────────────────────────────── */
function toggleFAB() {
    const fab = document.getElementById('ptFAB');
    if (!fab) return;
    fab.classList.toggle('open');
}

// Close FAB when clicking outside
document.addEventListener('click', function (e) {
    const fab = document.getElementById('ptFAB');
    if (fab && !fab.contains(e.target)) {
        fab.classList.remove('open');
    }
});

/* ── Init ────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
    // Set theme button state
    const theme = document.documentElement.getAttribute('data-theme') || 'light';
    updateThemeBtn(theme);

    // Auto-expand sidebar submenu if active
    document.querySelectorAll('.pt-submenu-link.active').forEach(link => {
        const submenu = link.closest('.pt-submenu');
        if (submenu) {
            submenu.classList.add('show');
            const toggle = document.querySelector(
                `[data-bs-target="#${submenu.id}"]`
            );
            if (toggle) toggle.setAttribute('aria-expanded', 'true');
        }
    });

    // Close sidebar on overlay click
    document.getElementById('ptOverlay')
        ?.addEventListener('click', closeSidebar);

    // Dismiss alerts auto after 5s
    document.querySelectorAll('.alert.auto-dismiss').forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert?.close();
        }, 5000);
    });
});