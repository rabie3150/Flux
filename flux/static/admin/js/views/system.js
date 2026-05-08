/** Flux Admin — System Settings View */

import { escapeHtml } from '../utils.js';

export function renderSystem(state) {
    const settings = state.settings || {};
    const fields = [
        { key: 'storage_budget_gb', label: 'Storage budget (GB)', type: 'number', fallback: 5 },
        { key: 'auto_delete_published', label: 'Auto-delete published files', type: 'checkbox', fallback: true },
        { key: 'log_retention_days', label: 'Log retention (days)', type: 'number', fallback: 7 },
        { key: 'thermal_pause_c', label: 'Thermal pause threshold (°C)', type: 'number', fallback: 45 },
        { key: 'timezone', label: 'Timezone', type: 'text', fallback: 'UTC' },
    ];

    return `
        <section class="page-grid">
            <section class="panel span-8">
                <div class="panel-head"><div><h2>Preferences</h2><p>Global configuration and runtime controls.</p></div></div>
                <div class="form-stack">${fields.map((f) => settingField(f, settings)).join('')}</div>
            </section>
            <section class="panel span-4">
                <div class="panel-head"><div><h2>Status</h2><p>Runtime overview.</p></div></div>
                <div class="form-stack">
                    ${snapshot('Daemon', 'Running')}
                    ${snapshot('Health', state.health?.status === 'healthy' ? 'Healthy' : 'Check')}
                    ${snapshot('Pipelines', (state.pipelines || []).length)}
                    ${snapshot('Workers', (state.workers || []).filter((w) => w.enabled).length + ' active')}
                </div>
            </section>
        </section>`;
}

function settingField(field, settings) {
    const value = settings[field.key] ?? field.fallback;
    if (field.type === 'checkbox') {
        const checked = value ? 'checked' : '';
        return `<div class="inline-control" style="grid-template-columns: 1fr auto; align-items:center;">
            <label class="toggle-row" style="margin:0;"><input type="checkbox" data-setting="${escapeHtml(field.key)}" ${checked}><span>${escapeHtml(field.label)}</span></label>
            <button class="button compact ghost" data-save-setting="${escapeHtml(field.key)}">Save</button>
        </div>`;
    }
    return `<label><span>${escapeHtml(field.label)}</span>
        <div class="inline-control" style="grid-template-columns: minmax(0, 240px) auto;">
            <input type="${field.type}" data-setting="${escapeHtml(field.key)}" value="${escapeHtml(String(value))}">
            <button class="button compact ghost" data-save-setting="${escapeHtml(field.key)}">Save</button>
        </div></label>`;
}

function snapshot(label, value) {
    return `<article class="snapshot"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`;
}
