/** Flux Admin — Utilities */

export function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

export function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, '&#96;');
}

export function formatDate(value) {
    if (!value) return '-';
    return new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function shortDate(value) {
    if (!value) return '-';
    return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function formatDuration(seconds) {
    if (!seconds || seconds < 0) return '0s';
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export function titleCase(value) {
    return String(value).replace(/\b\w/g, (l) => l.toUpperCase());
}

export function statusLabel(status) {
    const map = {
        verse_unknown: 'Needs verse',
        ready: 'Ready',
        rendered: 'Rendered',
        rendering: 'Rendering',
        failed: 'Failed',
        pending: 'Pending',
        approved: 'Approved',
        rejected: 'Rejected',
        published: 'Published',
        ok: 'Active',
        off: 'Off',
    };
    return map[status] || titleCase(String(status || 'unknown').replaceAll('_', ' '));
}

export function platformLabel(platform) {
    return { youtube: 'YouTube', instagram: 'Instagram', tiktok: 'TikTok', x: 'X' }[platform] || platform;
}

export function debounce(fn, ms) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), ms);
    };
}
