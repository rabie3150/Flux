/** Flux Admin — Activity Log View */

import { escapeHtml, timeAgo } from '../utils.js';

export function renderActivity(state) {
    const events = state.activity || [];
    return `
        <section class="page-grid">
            <section class="panel span-12">
                <div class="panel-head"><div><h2>Activity Log</h2><p>Operational trail for fetches, renders, approvals, and system events.</p></div></div>
                ${events.length ? activityList(events) : emptyState('No activity recorded yet.')}
            </section>
        </section>`;
}

function activityList(events) {
    return `<div class="activity-list">${events.map((e) => {
        let tone = e.level;
        const ev = e.event_type.toLowerCase();
        if (ev.includes('error') || ev.includes('failed') || ev.includes('reject')) tone = 'error';
        else if (ev.includes('trigger') || ev.includes('fetch') || ev.includes('render')) tone = 'info';
        else if (ev.includes('approve') || ev.includes('publish') || ev.includes('success')) tone = 'info'; // 'ok' implies success, but blue/info is better for system events.
        
        return `
        <article class="activity-item">
            <span class="level-dot ${escapeHtml(tone)}"></span>
            <span style="overflow:hidden;"><strong style="font-size:14px; color:var(--color-text);">${escapeHtml(e.event_type)}</strong><small style="display:block; overflow-wrap:anywhere;">${escapeHtml(e.message)}</small></span>
            <time>${timeAgo(e.timestamp)}</time>
        </article>`;
    }).join('')}</div>`;
}

function emptyState(text) {
    return `<div class="empty-state">${escapeHtml(text)}</div>`;
}
