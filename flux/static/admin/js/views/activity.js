/** Flux Admin — Activity Log View */

import { escapeHtml, formatDate } from '../utils.js';

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
    return `<div class="activity-list">${events.map((e) => `
        <article class="activity-item">
            <span class="level-dot ${escapeHtml(e.level)}"></span>
            <span><strong>${escapeHtml(e.event_type)}</strong><small>${escapeHtml(e.message)}</small></span>
            <time>${formatDate(e.timestamp)}</time>
        </article>`).join('')}</div>`;
}

function emptyState(text) {
    return `<div class="empty-state">${escapeHtml(text)}</div>`;
}
