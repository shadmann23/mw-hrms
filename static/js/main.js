/**
 * MilkWays Limited HRMS — main.js
 * Vanilla JS · No dependencies · Django-backend ready
 */
'use strict';

document.addEventListener('DOMContentLoaded', () => {

    /* ── Sidebar mobile toggle ─────────────────────────── */
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar       = document.getElementById('sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', e => {
            e.stopPropagation();
            sidebar.classList.toggle('open');
        });
        document.addEventListener('click', e => {
            if (sidebar.classList.contains('open')
                && !sidebar.contains(e.target)
                && e.target !== sidebarToggle) {
                sidebar.classList.remove('open');
            }
        });
    }

    /* ── Notification dropdown ─────────────────────────── */
    const notifBtn  = document.getElementById('notifBtn');
    const notifDrop = document.getElementById('notifDropdown');
    if (notifBtn && notifDrop) {
        notifBtn.addEventListener('click', e => {
            e.stopPropagation();
            notifDrop.classList.toggle('open');
        });
        document.addEventListener('click', e => {
            if (!notifDrop.contains(e.target) && e.target !== notifBtn) {
                notifDrop.classList.remove('open');
            }
        });
    }

    /* ── Alert dismiss ─────────────────────────────────── */
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', () => fadeRemove(btn.closest('.alert')));
    });
    // Auto-dismiss success after 4 s
    setTimeout(() => {
        document.querySelectorAll('.alert-success').forEach(fadeRemove);
    }, 4000);

    function fadeRemove(el) {
        if (!el) return;
        el.style.transition = 'opacity 200ms, transform 200ms';
        el.style.opacity    = '0';
        el.style.transform  = 'translateY(-6px)';
        setTimeout(() => el.remove(), 220);
    }

    /* ── Modal helpers ─────────────────────────────────── */
    function openModal(id)  { const m = document.getElementById(id); if (m) m.classList.add('open'); }
    function closeModal(id) { const m = document.getElementById(id); if (m) m.classList.remove('open'); }

    // Open via data-modal-open="modalId"
    document.querySelectorAll('[data-modal-open]').forEach(btn => {
        btn.addEventListener('click', () => openModal(btn.dataset.modalOpen));
    });
    // Close via data-modal-close="modalId"
    document.querySelectorAll('[data-modal-close]').forEach(btn => {
        btn.addEventListener('click', () => closeModal(btn.dataset.modalClose));
    });
    // Close on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', e => {
            if (e.target === overlay) overlay.classList.remove('open');
        });
    });
    // ESC key closes any open modal
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
        }
    });

    /* ── Confirm-delete ────────────────────────────────── */
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', e => {
            if (!confirm(el.dataset.confirm)) e.preventDefault();
        });
    });

    /* ── Filter tabs (data-filter) ─────────────────────── */
    document.querySelectorAll('.filter-pill[data-filter]').forEach(btn => {
        btn.addEventListener('click', () => {
            const group = btn.closest('.filter-bar');
            group.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const val = btn.dataset.filter;
            document.querySelectorAll('[data-status]').forEach(row => {
                row.style.display = (val === 'all' || row.dataset.status === val) ? '' : 'none';
            });
        });
    });

    /* ── Live employee search ──────────────────────────── */
    const empSearch = document.getElementById('empSearch');
    const empTBody  = document.getElementById('empTBody');
    if (empSearch && empTBody) {
        empSearch.addEventListener('input', () => {
            const q = empSearch.value.toLowerCase();
            empTBody.querySelectorAll('tr').forEach(row => {
                row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
            });
        });
    }

    /* ── Live clock ────────────────────────────────────── */
    const clockEl = document.getElementById('liveClock');
    if (clockEl) {
        const tick = () => {
            clockEl.textContent = new Date().toLocaleTimeString('en-GB', {
                hour: '2-digit', minute: '2-digit', second: '2-digit'
            });
        };
        tick();
        setInterval(tick, 1000);
    }

    /* ── Attendance check-in/out (async, Django backend) ─ */
    const markBtn = document.getElementById('markAttendanceBtn');
    if (markBtn) {
        markBtn.addEventListener('click', async () => {
            const action = markBtn.dataset.action;
            markBtn.disabled = true;
            const orig = markBtn.textContent.trim();
            markBtn.textContent = 'Processing…';
            try {
                const res = await fetch(`/attendance/${action}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrf(),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                if (res.ok) location.reload();
                else throw new Error();
            } catch {
                markBtn.disabled = false;
                markBtn.textContent = orig;
            }
        });
    }

    /* ── Leave approve/reject (async) ──────────────────── */
    document.querySelectorAll('[data-leave-action]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const { leaveId, leaveAction } = btn.dataset;
            if (leaveAction === 'reject' && !confirm('Reject this leave request?')) return;
            try {
                const body = new FormData();
                body.append('action', leaveAction);
                body.append('csrfmiddlewaretoken', getCsrf());
                const res = await fetch(`/leaves/${leaveId}/approve/`, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body
                });
                if (res.ok) location.reload();
            } catch (err) { console.error(err); }
        });
    });

    /* ── Util: CSRF token ──────────────────────────────── */
    function getCsrf() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value
            || document.querySelector('meta[name=csrf-token]')?.content
            || '';
    }

    /* ── Password toggle ───────────────────────────────── */
    document.querySelectorAll('.toggle-pwd').forEach(btn => {
        btn.addEventListener('click', () => {
            const inp = btn.closest('.field-wrap').querySelector('input');
            if (!inp) return;
            inp.type = inp.type === 'password' ? 'text' : 'password';
        });
    });

});
