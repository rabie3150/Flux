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
            <section class="view-hero span-12"><div><h2>System Settings</h2><p>Global configuration and runtime controls.</p></div></section>
            <section class="panel span-8">
                <div class="panel-head"><div><h2>Preferences</h2><p>Save each setting individually.</p></div></div>
                <div class="form-stack">${fields.map((f) => settingField(f, settings)).join('')}</div>
            </section>
            <section class="panel span-4">
                <div class="panel-head"><div><h2>Render Engine</h2><p>Runtime status.</p></div></div>
                <div class="form-stack">
                    ${snapshot('Status', state.renderEngine?.locked ? 'Rendering…' : 'Idle')}
                    ${snapshot('Last render', state.renderEngine?.lastRender || '-')}
                    ${snapshot('Queue', state.renderEngine?.queue || '0')}
                </div>
            </section>
        </section>`;
}

function settingField(field, settings) {
    const value = settings[field.key] ?? field.fallback;
    if (field.type === 'checkbox') {
        const checked = value ? 'checked' : '';
        return `<label class="toggle-row"><input type="checkbox" data-setting="${escapeHtml(field.key)}" ${checked}><span>${escapeHtml(field.label)}</span></label>
            <button class="button compact" data-save-setting="${escapeHtml(field.key)}">Save</button>`;
    }
    return `<label><span>${escapeHtml(field.label)}</span>
        <div class="inline-control"><input type="${field.type}" data-setting="${escapeHtml(field.key)}" value="${escapeHtml(String(value))}">
        <button class="button compact" data-save-setting="${escapeHtml(field.key)}">Save</button></div></label>`;
}

function snapshot(label, value) {
    return `<article class="snapshot"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`;
}
