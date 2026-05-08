/** Flux Admin — Pipelines View */

import { escapeHtml, formatDate, shortDate, statusLabel } from '../utils.js';

export function renderPipelines(state) {
    const selected = state.selectedPipelineId;
    if (!selected) return pipelineList(state);
    return workbench(state);
}

function pipelineList(state) {
    const pipelines = state.pipelines || [];
    return `
        <section class="page-grid">
            <section class="panel span-12">
                <div class="panel-head">
                    <p>Manage automation streams.</p>
                    <button class="button primary" data-action="create-pipeline">+ Create Pipeline</button>
                </div>
                ${pipelines.length ? `
                <div class="table-wrap"><table><thead><tr><th>Name</th><th>Plugin</th><th>Status</th><th>Created</th><th></th></tr></thead><tbody>
                    ${pipelines.map((p) => `<tr>
                        <td><strong>${escapeHtml(p.name)}</strong></td><td>${escapeHtml(p.plugin_id)}</td>
                        <td>${statusPill(p.enabled ? 'Active' : 'Paused', p.enabled ? 'ok' : 'off')}</td>
                        <td>${formatDate(p.created_at)}</td>
                        <td class="table-actions icon-actions"><button class="button compact ghost" data-open-pipeline="${p.id}">Open</button></td>
                    </tr>`).join('')}
                </tbody></table></div>
                ` : '<div class="empty-state wide">No pipelines created yet. <button class="button compact" style="margin-left:8px;" data-action="create-pipeline">Create Pipeline</button></div>'}
            </section>
        </section>`;
}

function workbench(state) {
    const pipeline = (state.pipelines || []).find((p) => p.id === state.selectedPipelineId);
    if (!pipeline) return pipelineList(state);
    const data = state.pipelineData[pipeline.id] || { stats: {}, ingredients: [], production: [], workers: [] };
    const tab = state.pipelineTab || 'overview';

    return `
        <section class="page-grid">
            <section class="panel span-12">
                <div class="workbench-head">
                    <div><p class="eyebrow">Pipeline</p><h2>${escapeHtml(pipeline.name)} ${statusPill(pipeline.enabled ? 'Active' : 'Paused', pipeline.enabled ? 'ok' : 'off')}</h2></div>
                    <div class="card-actions">
                        <button class="button ghost" data-action="back-pipelines">← Back</button>
                        <button class="button ghost" data-toggle-pipeline="${pipeline.id}">${pipeline.enabled ? 'Pause' : 'Resume'}</button>
                    </div>
                </div>
                <div class="workbench-tabs"><div class="segmented">${['overview', 'ingredients', 'production', 'workers', 'settings'].map((t) => tabButton(t, tab, 'data-pipeline-tab')).join('')}</div></div>
                ${state.operation?.pipelineId === pipeline.id ? operationBar(state) : ''}
                ${tab === 'overview' ? overviewTab(data, state) : ''}
                ${tab === 'ingredients' ? ingredientsTab(data, state) : ''}
                ${tab === 'production' ? productionTab(data, state) : ''}
                ${tab === 'workers' ? workersTab(data, state) : ''}
                ${tab === 'settings' ? settingsTab(pipeline) : ''}
            </section>
        </section>`;
}

function overviewTab(data, state) {
    const stock = data.stats?.stock || {};
    const prod = data.stats?.production || {};
    return `
        <section class="flow-panel"><h2>Pipeline Flow</h2>
        <div class="stage-flow">
            ${stageCard('Sources', stock.pending || 0, 'pending', 'ingredients')}
            ${stageCard('Library', stock.approved || 0, 'approved', 'ingredients')}
            ${stageCard('Render', prod.rendering || 0, 'rendering', 'production', prod.rendering > 0)}
            ${stageCard('Publish', prod.ready || 0, 'ready', 'production', prod.ready > 0)}
        </div></section>
        <div class="overview-grid">
            ${metric('Pending Review', stock.pending || 0)}
            ${metric('Production Ready', prod.ready || 0)}
            ${metric('Verse Unknown', prod.verse_unknown || 0)}
            ${metric('Attached Workers', (data.workers || []).length)}
        </div>`;
}

function ingredientsTab(data, state) {
    const visible = (data.ingredients || []).filter((i) => {
        return (!state.filters?.ingredientType || i.type === state.filters.ingredientType)
            && (!state.filters?.ingredientStatus || i.status === state.filters.ingredientStatus);
    });
    const selected = state.selectedIngredients || new Set();
    const hasSel = selected.size > 0;
    const selVisible = visible.filter((i) => selected.has(i.id)).length;

    return `
        <div class="toolbar">
            <div><p class="eyebrow">Ingredient library</p><h2>Curate source media</h2><small>${selVisible} of ${visible.length} visible selected.</small></div>
            <div class="filter-group">
                <select data-filter="ingredientType">${option('', 'All types', state.filters?.ingredientType)}${option('quran_clip', 'Quran clips', state.filters?.ingredientType)}${option('bg_image', 'Background images', state.filters?.ingredientType)}${option('bg_video', 'Background videos', state.filters?.ingredientType)}</select>
                <select data-filter="ingredientStatus">${option('', 'All statuses', state.filters?.ingredientStatus)}${option('pending', 'Pending', state.filters?.ingredientStatus)}${option('approved', 'Approved', state.filters?.ingredientStatus)}${option('rejected', 'Rejected', state.filters?.ingredientStatus)}</select>
            </div>
            <div class="toolbar-actions">
                <button class="button ghost" data-action="select-all" ${visible.length ? '' : 'disabled'}>Select All</button>
                <button class="button ghost" data-action="clear-selection" ${hasSel ? '' : 'disabled'}>Clear</button>
                <button class="button" data-action="fetch" ${state.operation ? 'disabled' : ''}>Fetch</button>
                <button class="button ghost" data-action="approve" ${!hasSel || state.operation ? 'disabled' : ''}>Approve ${hasSel ? selected.size : ''}</button>
                <button class="button ghost danger-text" data-action="reject" ${!hasSel || state.operation ? 'disabled' : ''}>Reject ${hasSel ? selected.size : ''}</button>
            </div>
        </div>
        <div class="ingredient-grid">${visible.length ? visible.map((i) => ingredientCard(i, selected.has(i.id))).join('') : emptyState('No ingredients match filters.', true)}</div>`;
}

function productionTab(data, state) {
    const items = (data.production || []).filter((i) => !state.filters?.productionStatus || i.status === state.filters.productionStatus);
    return `
        <div class="production-stats">
            ${metric('Ready', items.filter((i) => i.status === 'ready').length)}
            ${metric('Rendered', items.filter((i) => i.status === 'rendered').length)}
            ${metric('Failed', items.filter((i) => i.status === 'failed').length)}
            ${metric('Unknown', items.filter((i) => i.status === 'verse_unknown').length)}
        </div>
        <div class="toolbar">
            <div class="filter-group">
                <select data-filter="productionStatus">${option('', 'All statuses', state.filters?.productionStatus)}${option('ready', 'Ready', state.filters?.productionStatus)}${option('rendered', 'Rendered', state.filters?.productionStatus)}${option('verse_unknown', 'Verse unknown', state.filters?.productionStatus)}${option('failed', 'Failed', state.filters?.productionStatus)}</select>
            </div>
            <button class="button primary" data-action="render-next" ${state.operation ? 'disabled' : ''}>Render Next Video</button>
        </div>
        <div class="table-wrap"><table class="production-table"><thead><tr><th>Status</th><th>Verse</th><th>Rendered</th><th></th></tr></thead><tbody>
            ${items.map(productionRow).join('')}
        </tbody></table></div>`;
}

function workersTab(data, state) {
    const attached = new Set((data.workers || []).map((w) => w.id));
    const allWorkers = state.workers || [];
    return `
        <div class="worker-grid">${allWorkers.map((w) => `
            <article class="worker-card">
                <div><span class="platform-badge">${escapeHtml(w.platform)}</span><h3>${escapeHtml(w.display_name)}</h3><p>${escapeHtml(w.schedule_cron || 'Manual only')}</p></div>
                ${statusPill(attached.has(w.id) ? 'Attached' : 'Available', attached.has(w.id) ? 'ok' : 'off')}
                <div class="card-actions">
                    ${attached.has(w.id)
                        ? `<button class="button compact ghost" data-detach-worker="${w.id}">Detach</button>`
                        : `<button class="button compact" data-attach-worker="${w.id}">Attach</button>`}
                </div>
            </article>`).join('')}</div>`;
}

function settingsTab(pipeline) {
    return `
        <div class="settings-grid">
            <label><span>Pipeline name</span><input id="pipeline-name" value="${escapeAttr(pipeline.name)}"></label>
            <label class="toggle-row"><input id="pipeline-enabled" type="checkbox" ${pipeline.enabled ? 'checked' : ''}><span>Enabled</span></label>
            <button class="button primary" data-action="save-pipeline">Save</button>
            <div class="code-panel"><span>Config JSON</span><pre>${escapeHtml(pipeline.config_json || '{}')}</pre></div>
        </div>`;
}

function ingredientCard(item, isSelected) {
    const preview = item.file_path?.match(/\.(mp4|mov|webm)$/i)
        ? `<video src="/api/pipelines/${item.pipeline_id}/ingredients/${item.id}/preview" preload="metadata" muted></video>`
        : item.file_path?.match(/\.(jpg|jpeg|png|webp)$/i)
        ? `<img src="/api/pipelines/${item.pipeline_id}/ingredients/${item.id}/preview" alt="" loading="lazy">`
        : '<span>No preview</span>';
    const detail = item.duration_secs ? `${Number(item.duration_secs).toFixed(1)}s` : item.file_size_bytes ? `${(item.file_size_bytes / 1024 / 1024).toFixed(2)}MB` : '';
    return `
        <article class="ingredient-card ${isSelected ? 'selected' : ''}" data-ingredient-card="${item.id}">
            <label class="check-control"><input type="checkbox" data-select-ingredient value="${item.id}" ${isSelected ? 'checked' : ''}><span></span></label>
            <button class="preview-frame" data-preview-ingredient="${item.id}">${preview}</button>
            <div class="ingredient-meta"><strong>${escapeHtml(item.type)}</strong>${statusPill(item.status, item.status)}<small>${escapeHtml(detail)}</small></div>
        </article>`;
}

function productionRow(item) {
    const meta = item.content_meta || {};
    const ayah = meta.ayah || meta.ayah === 0 ? meta.ayah : null;
    const label = meta.surah ? `${meta.surah}:${ayah ?? '—'}${meta.ayah_end && meta.ayah_end > (ayah || 0) ? `-${meta.ayah_end}` : ''}` : 'Unknown';
    const canPost = item.status === 'ready';
    return `<tr>
        <td>${statusPill(statusLabel(item.status), item.status)}</td>
        <td><strong>${escapeHtml(label)}</strong><small>${escapeHtml(meta.surah_name || '')}</small></td>
        <td>${shortDate(item.rendered_at)}</td>
        <td class="table-actions icon-actions">
            <button class="button compact table-icon" title="Preview" data-preview-production="${item.id}">▶</button>
            ${canPost ? `<button class="button compact table-icon" title="Post Now" data-post-production="${item.id}">➤</button>` : ''}
            <button class="button compact ghost table-icon" title="Assign verse" data-identify-production="${item.id}">#</button>
            <button class="button compact ghost table-icon" title="Redo AI" data-redo-ai="${item.id}">↻</button>
        </td>
    </tr>`;
}

function operationBar(state) {
    const op = state.operation;
    if (!op) return '';
    return `
        <section class="operation-bar">
            <div class="spinner mini"></div>
            <div class="operation-info"><strong>${escapeHtml(op.label)}</strong><span class="muted">(${escapeHtml(op.pipelineName)})</span><span class="timer">${op.elapsed}s</span></div>
            <div class="operation-status">Processing…</div>
        </section>`;
}

function stageCard(title, count, status, target, active = false) {
    return `<button class="stage-card ${active ? 'active' : ''}" data-pipeline-tab="${target}"><span>${escapeHtml(title)}</span><strong>${count}</strong><small>${escapeHtml(status)}</small></button>`;
}

function metric(label, value) {
    return `<article class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></article>`;
}

function tabButton(tab, active, attr) {
    return `<button class="${active === tab ? 'active' : ''}" ${attr}="${tab}">${escapeHtml(tab[0].toUpperCase() + tab.slice(1))}</button>`;
}

function option(value, label, selected) {
    return `<option value="${escapeHtml(value)}" ${value === selected ? 'selected' : ''}>${escapeHtml(label)}</option>`;
}

export function pipelineModal(plugins = []) {
    return `
        <form class="form-stack" id="pipeline-form">
            <label><span>Pipeline name</span><input name="name" required placeholder="e.g. Quran Shorts"></label>
            <label><span>Plugin</span>
                <select name="plugin_id" required>
                    ${plugins.map((p) => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.display_name || p.name)}</option>`).join('')}
                </select>
            </label>
            <button class="button primary" type="submit">Create Pipeline</button>
        </form>`;
}

function emptyState(text, wide = false) {
    return `<div class="empty-state ${wide ? 'wide' : ''}">${escapeHtml(text)}</div>`;
}

function statusPill(label, status) {
    return `<span class="status-pill ${escapeHtml(status)}">${escapeHtml(label)}</span>`;
}
