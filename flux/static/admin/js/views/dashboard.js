/** Flux Admin — Dashboard View */

import { escapeHtml, formatDate, statusLabel, platformLabel } from '../utils.js';

export function renderDashboard(state) {
    const pipelines = state.pipelines || [];
    const workers = state.workers || [];
    const activity = (state.activity || []).slice(0, 8);
    const health = state.health || {};
    const stats = state.stats || {};

    // Compute global alert counts
    let failedTotal = 0, unknownTotal = 0, readyTotal = 0;
    Object.values(state.pipelineData || {}).forEach((d) => {
        const prod = d.production || [];
        failedTotal += prod.filter((i) => i.status === 'failed').length;
        unknownTotal += prod.filter((i) => i.status === 'verse_unknown').length;
        readyTotal += prod.filter((i) => i.status === 'ready').length;
    });

    const alerts = [];
    if (failedTotal) alerts.push({ count: failedTotal, label: 'failed renders', target: 'production', tone: 'danger' });
    if (unknownTotal) alerts.push({ count: unknownTotal, label: 'need verse ID', target: 'production', tone: 'warn' });

    return `
        <section class="page-grid">
            ${alerts.length ? `<div class="span-12 alert-banner">${alerts.map((a) => actionCard(a.label, a.count, a.target, a.tone)).join('')}</div>` : ''}
            <div class="metric-row span-12">
                ${metric('Uptime', formatUptime(health.uptime_seconds))}
                ${metric('Pipelines', pipelines.length)}
                ${metric('Workers', workers.length)}
                ${metric('Ready to Post', readyTotal)}
            </div>
            <section class="panel span-7">
                <div class="panel-head"><div><h2>Pipelines</h2><p>Active automation streams.</p></div><button class="button compact" data-nav="pipelines">Manage</button></div>
                <div class="stack-list">${pipelines.length ? pipelines.map(pipelineRow).join('') : emptyState('No pipelines yet.')}</div>
            </section>
            <section class="panel span-5">
                <div class="panel-head"><div><h2>Workers</h2><p>Connected publishing destinations.</p></div></div>
                <div class="compact-grid">${workers.length ? workers.slice(0, 4).map(workerCard).join('') : emptyState('No workers configured.')}</div>
            </section>
            <section class="panel span-12">
                <div class="panel-head"><div><h2>Recent Activity</h2><p>Last system events.</p></div><button class="button compact" data-nav="activity">Open</button></div>
                ${activityTable(activity)}
            </section>
        </section>`;
}

function formatUptime(sec) {
    if (!sec) return '-';
    const d = Math.floor(sec / 86400);
    const h = Math.floor((sec % 86400) / 3600);
    if (d) return `${d}d ${h}h`;
    return `${h}h`;
}

function metric(label, value) {
    return `<article class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></article>`;
}

function pipelineRow(p) {
    return `<button class="row-card" data-open-pipeline="${p.id}">
        <span><strong>${escapeHtml(p.name)}</strong><small>${escapeHtml(p.plugin_id)}</small></span>
        ${statusPill(p.enabled ? 'Active' : 'Paused', p.enabled ? 'ok' : 'off')}
    </button>`;
}

function workerCard(w) {
    const hasError = w.last_error_at;
    return `<article class="worker-card">
        <div><span class="platform-badge">${platformLabel(w.platform)}</span><h3>${escapeHtml(w.display_name)}</h3><p>${escapeHtml(w.schedule_cron || 'Manual only')}</p></div>
        <div>${statusPill(w.enabled ? 'Active' : 'Paused', w.enabled ? 'ok' : 'off')}${hasError ? ' ' + statusPill('Error', 'failed') : ''}</div>
        <div class="card-actions"><button class="button compact" data-open-worker="${w.id}">Open</button></div>
    </article>`;
}

function activityTable(events) {
    if (!events.length) return emptyState('No activity recorded yet.');
    return `<div class="table-wrap"><table><thead><tr><th>Type</th><th>Time</th><th>Event</th><th>Pipeline</th></tr></thead><tbody>
        ${events.map((e) => `<tr><td><span class="level-dot ${escapeHtml(e.level)}"></span></td><td>${formatDate(e.timestamp)}</td><td>${escapeHtml(e.message || e.event_type)}</td><td><span class="platform-badge">${escapeHtml(e.pipeline_id || 'System')}</span></td></tr>`).join('')}
    </tbody></table></div>`;
}

function actionCard(label, count, target, tone) {
    return `<button class="action-card ${tone}" data-nav="pipelines" data-tab="${target}"><span>${escapeHtml(label)}</span><strong>${count}</strong></button>`;
}

function emptyState(text) {
    return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function statusPill(label, status) {
    return `<span class="status-pill ${escapeHtml(status)}">${escapeHtml(label)}</span>`;
}
