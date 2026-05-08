/** Flux Admin — Workers View */

import { escapeHtml, escapeAttr, formatDate, statusLabel, platformLabel } from '../utils.js';

const CREDENTIAL_SCHEMAS = {
    youtube: {
        official: [
            { name: 'client_id', label: 'OAuth Client ID', type: 'text' },
            { name: 'client_secret', label: 'OAuth Client Secret', type: 'password' },
            { name: 'refresh_token', label: 'Refresh Token', type: 'password' },
        ],
        third_party: [{ name: 'api_key', label: 'Provider API Key', type: 'password' }],
    },
    tiktok: {
        official: [
            { name: 'app_id', label: 'App ID', type: 'text' },
            { name: 'app_secret', label: 'App Secret', type: 'password' },
            { name: 'access_token', label: 'Access Token', type: 'password' },
        ],
        third_party: [{ name: 'api_key', label: 'Provider API Key', type: 'password' }],
    },
    instagram: {
        official: [
            { name: 'app_id', label: 'App ID', type: 'text' },
            { name: 'app_secret', label: 'App Secret', type: 'password' },
            { name: 'access_token', label: 'Access Token', type: 'password' },
            { name: 'instagram_account_id', label: 'Account ID', type: 'text' },
        ],
        unofficial: [
            { name: 'username', label: 'Username', type: 'text' },
            { name: 'password', label: 'Password', type: 'password' },
        ],
        third_party: [{ name: 'api_key', label: 'Provider API Key', type: 'password' }],
    },
    x: {
        official: [
            { name: 'api_key', label: 'API Key', type: 'text' },
            { name: 'api_secret', label: 'API Secret', type: 'password' },
            { name: 'access_token', label: 'Access Token', type: 'password' },
            { name: 'access_token_secret', label: 'Access Token Secret', type: 'password' },
        ],
        third_party: [{ name: 'api_key', label: 'Provider API Key', type: 'password' }],
    },
};

const THIRD_PARTY_PROVIDERS = ['buffer', 'hootsuite', 'socialpilot'];

export function renderWorkers(state) {
    const selected = state.selectedWorkerId;
    const workers = state.workers || [];

    return `
        <section class="page-grid">
            <section class="panel span-12">
                <div class="panel-head">
                    <p>Manage publishing destinations.</p>
                    <button class="button primary" data-action="create-worker">+ Connect Worker</button>
                </div>
                <div class="worker-grid worker-grid-wide">${workers.length ? workers.map(workerCard).join('') : '<div class="empty-state wide">No workers configured yet. <button class="button compact" style="margin-left:8px;" data-action="create-worker">Connect Worker</button></div>'}</div>
            </section>
            ${selected ? workerDetail(state) : ''}
        </section>`;
}

function workerCard(w) {
    const hasError = w.last_error_at;
    return `<article class="worker-card">
        <div><span class="platform-badge">${platformLabel(w.platform)}</span><h3>${escapeHtml(w.display_name)}</h3><p>${escapeHtml(cronText(w.schedule_cron))}</p></div>
        <div>${statusPill(w.enabled ? 'Active' : 'Paused', w.enabled ? 'ok' : 'off')}${hasError ? ' ' + statusPill('Error', 'failed') : ''}</div>
        <div class="card-actions" style="margin-top:auto; padding-top:14px; border-top:1px solid var(--color-border);">
            <button class="button compact ghost" data-open-worker="${w.id}">Open</button>
            <button class="button compact ghost" data-toggle-worker="${w.id}">${w.enabled ? 'Pause' : 'Resume'}</button>
            <button class="button compact ghost danger-text" data-delete-worker="${w.id}" style="margin-left:auto;">Delete</button>
        </div>
    </article>`;
}

function workerDetail(state) {
    const w = (state.workers || []).find((x) => x.id === state.selectedWorkerId);
    if (!w) return '';
    const tab = state.workerTab || 'overview';
    return `
        <section class="panel span-12">
            <div class="workbench-head">
                <div><p class="eyebrow">Worker Detail</p><h2>${escapeHtml(w.display_name)}</h2></div>
                <div class="card-actions">
                    <button class="button ghost" data-action="back-workers">← Back</button>
                    <div class="segmented">${['overview', 'schedule', 'caption', 'pipelines'].map((t) => tabButton(t, tab, 'data-worker-tab')).join('')}</div>
                </div>
            </div>
            ${tab === 'overview' ? workerOverview(w, state) : ''}
            ${tab === 'schedule' ? workerSchedule(w) : ''}
            ${tab === 'caption' ? workerCaption(w) : ''}
            ${tab === 'pipelines' ? workerPipelines(w, state) : ''}
        </section>`;
}

function workerOverview(w, state) {
    const recent = (state.posts || []).filter((p) => p.worker_id === w.id).slice(0, 5);
    return `
        <div class="overview-grid">
            ${metric('Platform', platformLabel(w.platform))}
            ${metric('Strategy', strategyLabel(w.connection_strategy))}
            ${metric('Status', w.enabled ? 'Active' : 'Paused')}
            ${metric('Last Post', formatDate(w.last_posted_at))}
            <div class="span-all" style="margin-top:0.5rem;">
                <button class="button primary" data-action="post-now" data-worker-id="${w.id}">Post Now</button>
                <button class="button ghost" data-action="test-worker" data-worker-id="${w.id}">Test Credentials</button>
                <button class="button ghost" data-action="edit-worker" data-worker-id="${w.id}">Edit</button>
            </div>
        </div>
        ${recent.length ? `<div class="panel" style="margin-top:1rem;"><div class="panel-head"><h2>Recent Posts</h2></div>
        <div class="table-wrap"><table><thead><tr><th>Verse</th><th>Status</th><th>Time</th></tr></thead><tbody>
        ${recent.map((p) => `<tr><td>${escapeHtml(p.verse_label || '-')}</td><td>${statusPill(statusLabel(p.status), p.status)}</td><td>${formatDate(p.created_at)}</td></tr>`).join('')}
        </tbody></table></div></div>` : ''}`;
}

function workerSchedule(w) {
    return `
        <div class="settings-grid">
            <label><span>Cron schedule</span><input id="worker-cron" value="${escapeAttr(w.schedule_cron || '')}" placeholder="0 8 * * *"></label>
            <button class="button primary" data-action="save-worker-schedule" data-worker-id="${w.id}">Save Schedule</button>
        </div>`;
}

function workerCaption(w) {
    let hashtags = [];
    try { hashtags = JSON.parse(w.hashtags_json || '[]'); } catch {}
    return `
        <div class="settings-grid">
            <label><span>Caption template override</span><textarea id="worker-caption" rows="4">${escapeHtml(w.caption_template_override || '')}</textarea></label>
            <label><span>Hashtags (comma-separated)</span><input id="worker-hashtags" value="${escapeAttr(hashtags.join(', '))}"></label>
            <button class="button primary" data-action="save-worker-caption" data-worker-id="${w.id}">Save Caption</button>
        </div>`;
}

function workerPipelines(w, state) {
    return `<div class="worker-grid">${(state.pipelines || []).map((p) => {
        const data = state.pipelineData[p.id] || {};
        const attached = (data.workers || []).some((x) => x.id === w.id);
        return `<article class="worker-card"><h3>${escapeHtml(p.name)}</h3>${statusPill(attached ? 'Attached' : 'Available', attached ? 'ok' : 'off')}<div class="card-actions">${attached ? `<button class="button compact ghost" data-detach-pipeline="${p.id}">Detach</button>` : `<button class="button compact" data-attach-pipeline="${p.id}">Attach</button>`}</div></article>`;
    }).join('')}</div>`;
}

export function workerModal(worker = null) {
    const isEdit = !!worker;
    const platforms = Object.keys(CREDENTIAL_SCHEMAS);
    const w = worker || {};
    const creds = w.credentials || {};

    return `
        <form class="form-stack" id="worker-form">
            <label><span>Platform</span>
                <select name="platform" id="w-platform" ${isEdit ? 'disabled' : ''}>
                    ${platforms.map((p) => `<option value="${p}" ${w.platform === p ? 'selected' : ''}>${platformLabel(p)}</option>`).join('')}
                </select>
            </label>
            <label><span>Display name</span><input name="display_name" value="${escapeAttr(w.display_name || '')}" required></label>
            <label><span>Strategy</span>
                <select name="connection_strategy" id="w-strategy" ${isEdit ? 'disabled' : ''}>
                    <option value="official" ${w.connection_strategy === 'official' ? 'selected' : ''}>Official API</option>
                    <option value="unofficial" ${w.connection_strategy === 'unofficial' ? 'selected' : ''}>Unofficial</option>
                    <option value="third_party" ${w.connection_strategy === 'third_party' ? 'selected' : ''}>Third-party</option>
                </select>
            </label>
            <div id="tp-provider" class="hidden">
                <label><span>Provider</span><select name="third_party_provider">
                    ${THIRD_PARTY_PROVIDERS.map((p) => `<option value="${p}" ${w.third_party_provider === p ? 'selected' : ''}>${escapeHtml(p)}</option>`).join('')}
                </select></label>
            </div>
            <div id="cred-fields" class="form-stack"></div>
            <label><span>Schedule (cron, optional)</span><input name="schedule_cron" value="${escapeAttr(w.schedule_cron || '')}" placeholder="0 8 * * *"></label>
            <button class="button primary" type="submit">${isEdit ? 'Save Worker' : 'Create Worker'}</button>
        </form>`;
}

export function refreshCredentialFields(platform, strategy, credentials = {}) {
    const container = document.getElementById('cred-fields');
    if (!container) return;
    const schema = CREDENTIAL_SCHEMAS[platform]?.[strategy] || [];
    container.innerHTML = schema.map((f) => {
        const val = credentials[f.name] || '';
        return f.type === 'textarea'
            ? `<label><span>${escapeHtml(f.label)}</span><textarea name="cred_${f.name}" rows="3">${escapeHtml(val)}</textarea></label>`
            : `<label><span>${escapeHtml(f.label)}</span><input name="cred_${f.name}" type="${f.type}" value="${escapeAttr(val)}"></label>`;
    }).join('');

    const tp = document.getElementById('tp-provider');
    if (tp) tp.classList.toggle('hidden', strategy !== 'third_party');

    const stratSel = document.getElementById('w-strategy');
    if (stratSel) {
        Array.from(stratSel.options).forEach((opt) => {
            if (opt.value === 'unofficial') opt.style.display = CREDENTIAL_SCHEMAS[platform]?.unofficial ? '' : 'none';
        });
    }
}

function cronText(cron) {
    if (!cron) return 'Manual only';
    const parts = cron.split(' ');
    if (parts.length !== 5) return cron;
    const [min, hour, , , days] = parts;
    if (min === '0' && hour === '*' && days === '*') return 'Every hour';
    if (min === '0' && days === '*') {
        const h = parseInt(hour, 10);
        const ampm = h >= 12 ? 'PM' : 'AM';
        const hr12 = h % 12 || 12;
        return `Daily at ${hr12}:00 ${ampm}`;
    }
    if (min === '0' && hour === '0' && days === '0') return 'Weekly (Sun midnight)';
    return `Cron: ${cron}`;
}

function strategyLabel(s) {
    return { official: 'Official API', unofficial: 'Unofficial', third_party: 'Third-party' }[s] || s;
}

function metric(label, value) {
    return `<article class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></article>`;
}

function tabButton(tab, active, attr) {
    return `<button class="${active === tab ? 'active' : ''}" ${attr}="${tab}">${escapeHtml(tab[0].toUpperCase() + tab.slice(1))}</button>`;
}

function statusPill(label, status) {
    return `<span class="status-pill ${escapeHtml(status)}">${escapeHtml(label)}</span>`;
}
