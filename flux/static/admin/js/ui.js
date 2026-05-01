function dashboardTemplate() {
    const ingredients = allIngredients();
    const production = allProduction();
    return `
        <section class="page-grid">
            <div class="metric-row">
                ${metric('Uptime', `${Math.floor((state.health.uptime_seconds || 0) / 86400) || 0} days`)}
                ${storageMetric()}
                ${scheduleMetric()}
            </div>
            <section class="panel span-7">
                ${panelHead('Pipelines', 'Active automation streams.', 'Manage', 'pipelines')}
                <div class="stack-list">${state.pipelines.length ? state.pipelines.map(pipelineRow).join('') : emptyState('No pipelines yet. Create the Quran pipeline to start the first content flow.')}</div>
                <button class="add-tile" data-view="pipelines">+ Add Pipeline</button>
            </section>
            <section class="panel span-5">
                ${panelHead('Platform Workers', 'Connected publishing destinations.')}
                <div class="compact-grid">${state.workers.length ? state.workers.slice(0, 3).map(workerCard).join('') : emptyState('No platform workers configured yet.')}</div>
            </section>
            <section class="panel span-12">
                ${panelHead('Recent Activity', 'Last system events from the daemon.', 'Open', 'activity')}
                ${activityTable(state.activity.slice(0, 8))}
            </section>
        </section>`;
}

function operationTemplate() {
    if (!state.operation) return '';
    const op = state.operation;
    const activeIndex = op.steps.length ? op.pulse % op.steps.length : 0;
    const latestActivity = state.activity && state.activity.length > 0 ? state.activity[0] : null;
    
    return `
        <section class="operation-bar">
            <div class="spinner mini" aria-label="Operation in progress"></div>
            <div class="operation-info">
                <strong>${escapeHtml(op.label)}</strong>
                <span class="muted">(${escapeHtml(op.pipelineName)})</span>
                <span class="timer">${formatDuration(op.elapsed)}</span>
            </div>
            <div class="operation-status">
                ${latestActivity ? escapeHtml(latestActivity.message) : escapeHtml(op.steps[activeIndex])}
            </div>
        </section>`;
}

function pipelinesTemplate() {
    if (selectedPipeline()) return `<section class="page-grid">${workbenchTemplate()}</section>`;
    return `
        <section class="page-grid">
            <section class="panel span-12">
                ${panelHead('Pipeline List', 'Select a pipeline to inspect ingredients, renders, workers, and settings.')}
                ${pipelineTable()}
            </section>
        </section>`;
}

function workbenchTemplate() {
    const pipeline = selectedPipeline();
    return `
        <section class="panel span-12">
            <div class="workbench-head">
                <div><p class="eyebrow">Pipelines / ${escapeHtml(pipeline.plugin_id)}</p><h2>${escapeHtml(pipeline.name)} ${statusPill(pipeline.enabled ? 'Active' : 'Paused', pipeline.enabled ? 'ok' : 'off')}</h2></div>
                <div class="card-actions">
                    <button class="button ghost" data-toggle-pipeline="${pipeline.id}">${pipeline.enabled ? 'Pause' : 'Resume'}</button>
                    <button class="button primary" data-action="render-next" ${state.operation ? 'disabled' : ''}>${state.operation?.type === 'render' ? 'Rendering...' : 'Run Pipeline'}</button>
                </div>
            </div>
            <div class="workbench-tabs">
                <div class="segmented">${['overview', 'ingredients', 'production', 'workers', 'settings'].map((tab) => tabButton(tab, state.pipelineTab, 'data-pipeline-tab')).join('')}</div>
            </div>
            ${state.pipelineTab === 'overview' ? pipelineOverviewTemplate() : ''}
            ${state.pipelineTab === 'ingredients' ? ingredientsTemplate() : ''}
            ${state.pipelineTab === 'production' ? productionTemplate() : ''}
            ${state.pipelineTab === 'workers' ? pipelineWorkersTemplate() : ''}
            ${state.pipelineTab === 'settings' ? pipelineSettingsTemplate(pipeline) : ''}
        </section>`;
}

function pipelineOverviewTemplate() {
    const stock = currentData().stats.stock || {};
    return `
        <section class="flow-panel">
            <h2>Pipeline Flow</h2>
            <div class="stage-flow">
                ${stageCard('Step 1 Sources', stock.pending || 0, 'YT, Pexels', 'ingredients')}
                ${stageCard('Step 2 Library', stock.approved || 0, 'Clips, BGs', 'ingredients')}
                ${stageCard('Step 3 Render', countProduction('verse_unknown'), 'FFmpeg', 'production', 'active')}
                ${stageCard('Step 4 Publish', countProduction('ready'), 'Socials', 'production')}
            </div>
        </section>
        <div class="overview-grid">
            ${metric('Pending Review', stock.pending || 0, 'soft')}
            ${metric('Production Ready', countProduction('ready'), 'soft')}
            ${metric('Platform Coverage', currentData().workers.length || state.workers.length, 'soft')}
        </div>`;
}

function ingredientsTemplate() {
    const visible = currentIngredients();
    const selectedVisible = visible.filter((item) => state.selectedIngredients.has(item.id)).length;
    const hasSelection = state.selectedIngredients.size > 0;
    return `
        <div class="toolbar">
            <div>
                <p class="eyebrow">Ingredient library</p>
                <h2>Curate source media</h2>
                <small>${selectedVisible} of ${visible.length} visible selected. Ctrl-click toggles, shift-click selects a range.</small>
            </div>
            <div class="filter-group">
                <select id="ingredient-type">${option('', 'All types', state.filters.ingredientType)}${option('quran_clip', 'Quran clips', state.filters.ingredientType)}${option('bg_image', 'Background images', state.filters.ingredientType)}${option('bg_video', 'Background videos', state.filters.ingredientType)}</select>
                <select id="ingredient-status">${option('', 'All statuses', state.filters.ingredientStatus)}${option('pending', 'Pending', state.filters.ingredientStatus)}${option('approved', 'Approved', state.filters.ingredientStatus)}${option('rejected', 'Rejected', state.filters.ingredientStatus)}</select>
            </div>
            <div class="toolbar-actions">
                <button class="button ghost" data-action="select-all-ingredients" ${visible.length ? '' : 'disabled'}>Select All</button>
                <button class="button ghost" data-action="clear-ingredients" ${hasSelection ? '' : 'disabled'}>Clear</button>
                <button class="button ghost" data-action="invert-ingredients" ${visible.length ? '' : 'disabled'}>Invert</button>
                <button class="button" data-action="fetch" ${state.operation ? 'disabled' : ''}>${state.operation?.type === 'fetch' ? 'Fetching...' : 'Fetch'}</button>
                <button class="button ghost" data-action="approve" ${state.operation || !hasSelection ? 'disabled' : ''}>Approve ${hasSelection ? state.selectedIngredients.size : ''}</button>
                <button class="button ghost danger-text" data-action="reject" ${state.operation || !hasSelection ? 'disabled' : ''}>Reject ${hasSelection ? state.selectedIngredients.size : ''}</button>
            </div>
        </div>
        <div class="ingredient-grid">${visible.length ? visible.map(ingredientCard).join('') : emptyState('No ingredients match the current filters.', true)}</div>`;
}

function productionTemplate() {
    const items = currentProduction();
    const failed = items.filter((item) => item.status === 'failed').length;
    return `
        <div class="metric-row compact-metrics">
            ${metric('Awaiting Post', items.filter((item) => item.status === 'ready').length)}
            ${metric('Rendered Today', items.filter((item) => item.status === 'rendered' || item.status === 'ready').length)}
            ${metric('Failed Jobs', failed)}
            ${metric('Next Post', '14:00')}
        </div>
        <div class="toolbar">
            <div class="filter-group">
                <select id="production-status">${option('', 'All statuses', state.filters.productionStatus)}${option('rendering', 'Rendering', state.filters.productionStatus)}${option('rendered', 'Rendered', state.filters.productionStatus)}${option('ready', 'Ready', state.filters.productionStatus)}${option('verse_unknown', 'Verse unknown', state.filters.productionStatus)}${option('failed', 'Failed', state.filters.productionStatus)}</select>
            </div>
            <button class="button primary" data-action="render-next" ${state.operation ? 'disabled' : ''}>${state.operation?.type === 'render' ? 'Rendering...' : 'Render Next Video'}</button>
        </div>
        <div class="table-wrap">
            <table class="production-table"><thead><tr><th>Status</th><th>Verse</th><th>Rendered</th><th></th></tr></thead><tbody>${items.map(productionRow).join('')}</tbody></table>
        </div>`;
}

function pipelineWorkersTemplate() {
    const attached = new Set(currentData().workers.map((worker) => worker.id));
    return `<div class="worker-grid">${state.workers.length ? state.workers.map((worker) => `
        <article class="worker-card">
            <div><span class="platform-badge">${platformLabel(worker.platform)}</span><h3>${escapeHtml(worker.display_name)}</h3><p>${escapeHtml(worker.schedule_cron || 'Manual posting only')}</p></div>
            ${statusPill(attached.has(worker.id) ? 'Attached' : 'Available', attached.has(worker.id) ? 'ok' : 'off')}
            <div class="card-actions">
                ${attached.has(worker.id) ? `<button class="button compact ghost" data-detach-pipeline-worker="${worker.id}">Detach</button>` : `<button class="button compact" data-attach-pipeline-worker="${worker.id}">Attach</button>`}
            </div>
        </article>`).join('') : emptyState('No workers exist yet. Add one from Platform Workers.', true)}</div>`;
}

function pipelineSettingsTemplate(pipeline) {
    return `<div class="settings-grid">
        <label><span>Pipeline name</span><input id="selected-pipeline-name" value="${escapeAttr(pipeline.name)}"></label>
        <label class="toggle-row"><input id="selected-pipeline-enabled" type="checkbox" ${pipeline.enabled ? 'checked' : ''}><span>Pipeline enabled</span></label>
        <button class="button primary" data-action="save-pipeline">Save Changes</button>
        ${configPreview(pipeline.config_json)}
    </div>`;
}

function workersTemplate() {
    return `
        <section class="page-grid">
            <section class="view-hero span-12">
                <div><h2>Workers</h2><p>Manage your connected platform publishers.</p></div>
                <button class="button primary">+ Connect Worker</button>
            </section>
            <section class="span-12">
                <div class="worker-grid worker-grid-wide">${state.workers.length ? state.workers.map(workerCard).join('') : emptyState('No platform workers configured.', true)}</div>
            </section>
            ${selectedWorker() ? workerDetailTemplate() : ''}
        </section>`;
}

function workerDetailTemplate() {
    const worker = selectedWorker();
    return `<section class="panel span-12">
        <div class="workbench-head">
            <div><p class="eyebrow">Worker Detail</p><h2>${escapeHtml(worker.display_name)}</h2></div>
            <div class="segmented">${['overview', 'schedule', 'caption', 'pipelines', 'logs'].map((tab) => tabButton(tab, state.workerTab, 'data-worker-tab')).join('')}</div>
        </div>
        ${state.workerTab === 'overview' ? workerOverview(worker) : ''}
        ${state.workerTab === 'schedule' ? workerSchedule(worker) : ''}
        ${state.workerTab === 'caption' ? workerCaption(worker) : ''}
        ${state.workerTab === 'pipelines' ? workerPipelines(worker) : ''}
        ${state.workerTab === 'logs' ? workerLogs(worker) : ''}
    </section>`;
}

function postsTemplate() {
    return `<section class="page-grid">
        <section class="view-hero span-12"><div><h2>Post Log</h2><p>Historical record of all automated content distributions.</p></div><button class="button ghost">Export Log</button></section>
        <section class="panel span-12"><div class="filter-grid">${filterBox('Platform', 'All Platforms')}${filterBox('Pipeline', 'All Pipelines')}${filterBox('Status', 'All Statuses')}${filterBox('Date Range', 'Last 7 Days')}</div></section>
        <section class="panel span-12"><div class="table-wrap"><table><thead><tr><th>Media</th><th>Content Ref</th><th>Platform</th><th>Account</th><th>Posted At</th><th>Status</th><th>Action</th></tr></thead><tbody>${state.backend.posts && state.posts.length ? state.posts.map(postRow).join('') : `<tr><td colspan="7">${emptyState('Post records will appear here once publishing endpoints land.')}</td></tr>`}</tbody></table></div></section>
    </section>`;
}

function systemTemplate() {
    return `<section class="page-grid">
        <section class="view-hero span-12"><div><h2>System Settings</h2><p>Manage global configurations, resource limits, and security policies.</p></div></section>
        <section class="span-12"><div class="segmented settings-tabs">${['General', 'Library', 'Sources', 'Captions', 'Timing', 'Security'].map((tab, index) => `<button class="${index === 0 ? 'active' : ''}">${tab}</button>`).join('')}</div></section>
        <section class="panel span-8">${panelHead('Storage & Retention', 'Local disk allocation and processed file cleanup.')}<div class="form-stack">${settingInput('storage_budget_gb', 'Storage budget (GB)', 5, 'number')}${settingInput('auto_delete_published', 'Auto-delete policy', true, 'checkbox')}${settingInput('log_retention_days', 'Log retention days', 7, 'number')}</div></section>
        <section class="panel span-4">${panelHead('Render Engine', 'Runtime controls for local production.')}<div class="form-stack">${settingInput('thermal_pause_c', 'Thermal pause threshold C', 45, 'number')}${snapshot('Hardware acceleration', 'NVENC planned')}${snapshot('Max concurrent renders', state.settings.max_concurrent_renders || 1)}</div></section>
        <section class="panel span-8">${panelHead('Regional Preferences', 'Timezone and timestamp formatting.')}<div class="settings-grid">${settingInput('timezone', 'System timezone', 'Africa/Casablanca')}${settingInput('timestamp_format', 'Timestamp format', 'YYYY-MM-DD HH:mm:ss')}</div></section>
        <section class="panel span-4">${panelHead('Unsaved Changes', 'Save configuration changes before navigating away.')}<div class="form-stack"><button class="button primary">Save Configuration</button><button class="button ghost">Discard Changes</button></div></section>
    </section>`;
}

function pluginsTemplate() {
    return `<section class="page-grid">
        <section class="panel span-8">${panelHead('Installed Plugins', 'Content types available to pipelines.')}<div class="worker-grid">${pluginInventory().map(pluginCard).join('')}</div></section>
        <section class="panel span-4">${panelHead('Plugin Manager Roadmap', 'Ready for future registry/install backend.')}<div class="stack-list">${roadmap('Install from Git URL')}${roadmap('Validate plugin manifest')}${roadmap('Enable / disable plugin')}${roadmap('Generate plugin config form')}</div></section>
    </section>`;
}

function activityTemplate() {
    return `<section class="panel">${panelHead('Activity Log', 'Operational trail for fetches, renders, approvals, and system events.')}${activityList(state.activity)}</section>`;
}

function pipelineTable() {
    return `<div class="table-wrap"><table>
        <thead><tr><th>Name</th><th>Plugin</th><th>Status</th><th>Created</th><th></th></tr></thead>
        <tbody>${state.pipelines.map((pipeline) => `<tr>
            <td>${escapeHtml(pipeline.name)}</td><td>${escapeHtml(pipeline.plugin_id)}</td>
            <td>${statusPill(pipeline.enabled ? 'Active' : 'Paused', pipeline.enabled ? 'ok' : 'off')}</td>
            <td>${formatDate(pipeline.created_at)}</td>
            <td class="table-actions"><button class="button compact" data-open-pipeline="${pipeline.id}">Open</button><button class="button compact ghost" data-toggle-pipeline="${pipeline.id}">${pipeline.enabled ? 'Pause' : 'Resume'}</button><button class="button compact danger" data-delete-pipeline="${pipeline.id}">Delete</button></td>
        </tr>`).join('')}</tbody>
    </table></div>`;
}

function pipelineRow(pipeline) {
    const data = state.pipelineData[pipeline.id] || {};
    const ready = (data.production || []).filter((item) => item.status === 'ready').length;
    return `<button class="row-card" data-open-pipeline="${pipeline.id}">
        <span><strong>${escapeHtml(pipeline.name)}</strong><small>${escapeHtml(pipeline.plugin_id)} / ${ready} ready</small></span>
        ${statusPill(pipeline.enabled ? 'Active' : 'Paused', pipeline.enabled ? 'ok' : 'off')}
    </button>`;
}

function workerCard(worker) {
    return `<article class="worker-card">
        <div><span class="platform-badge">${platformLabel(worker.platform)}</span><h3>${escapeHtml(worker.display_name)}</h3><p>${escapeHtml(worker.schedule_cron || 'Manual posting only')}</p></div>
        ${statusPill(worker.enabled ? 'Active' : 'Paused', worker.enabled ? 'ok' : 'off')}
        <div class="card-actions"><button class="button compact" data-open-worker="${worker.id}">Open</button><button class="button compact ghost" data-toggle-worker="${worker.id}">${worker.enabled ? 'Pause' : 'Resume'}</button><button class="button compact danger" data-delete-worker="${worker.id}">Delete</button></div>
    </article>`;
}

function workerTile(worker) {
    return `<article class="worker-tile"><span class="platform-badge">${platformLabel(worker.platform)}</span><strong>${escapeHtml(worker.display_name)}</strong><small>${escapeHtml(worker.schedule_cron || 'Manual only')}</small></article>`;
}

function ingredientCard(item) {
    const selected = state.selectedIngredients.has(item.id);
    return `<article class="ingredient-card ${selected ? 'selected' : ''}" data-ingredient-card="${item.id}">
        <label class="check-control"><input type="checkbox" data-select-ingredient value="${item.id}" ${selected ? 'checked' : ''}><span></span></label>
        <button class="preview-frame" data-preview-ingredient="${item.id}">${previewMarkup(item)}</button>
        <div class="ingredient-meta"><strong>${prettyType(item.type)}</strong>${statusPill(item.status, item.status)}<small>${ingredientDetail(item)}</small></div>
    </article>`;
}

function productionRow(item) {
    return `<tr>
        <td>${statusPill(item.status, item.status)}</td>
        <td class="verse-cell">${productionVerseSummary(item)}</td>
        <td class="rendered-cell">${formatDate(item.rendered_at)}</td>
        <td class="table-actions icon-actions"><button class="button compact table-icon" title="Preview" aria-label="Preview production item" data-preview-production="${item.id}">▶</button><button class="button compact ghost table-icon" title="Assign verse" aria-label="Assign verse" data-identify-production="${item.id}">✎</button></td>
    </tr>`;
}

function activityList(events) {
    if (!events.length) return emptyState('No activity recorded yet.');
    return `<div class="activity-list">${events.map((event) => `<article class="activity-item">
        <span class="level-dot ${escapeAttr(event.level)}"></span>
        <span><strong>${escapeHtml(event.event_type)}</strong><small>${escapeHtml(event.message)}</small></span>
        <time>${formatDate(event.timestamp)}</time>
    </article>`).join('')}</div>`;
}

function workerOverview(worker) {
    return `<div class="overview-grid">${metric('Platform', platformLabel(worker.platform), 'soft')}${metric('Status', worker.enabled ? 'Active' : 'Paused', 'soft')}${metric('Last post', formatDate(worker.last_posted_at), 'soft')}${metric('Last error', worker.last_error_message || 'None', 'soft')}</div>`;
}

function workerSchedule(worker) {
    return `<div class="settings-grid">${snapshot('Current schedule', worker.schedule_cron || 'Manual only')}${snapshot('Jitter', 'planned')}${snapshot('Quota tracking', worker.platform === 'youtube' ? 'planned' : 'n/a')}${snapshot('Circuit breaker', worker.last_error_at ? 'attention' : 'clear')}</div>`;
}

function workerCaption(worker) {
    return `<div class="settings-grid">${snapshot('Template override', worker.caption_template_override || 'Using global template')}${snapshot('Hashtags', worker.hashtags_json || '[]')}${emptyState('Caption editor UI is ready conceptually; backend currently stores raw override fields.')}</div>`;
}

function workerPipelines(worker) {
    return `<div class="worker-grid">${state.pipelines.map((pipeline) => {
        const attached = (state.pipelineData[pipeline.id]?.workers || []).some((item) => item.id === worker.id);
        return `<article class="worker-card"><h3>${escapeHtml(pipeline.name)}</h3>${statusPill(attached ? 'Attached' : 'Available', attached ? 'ok' : 'off')}<div class="card-actions">${attached ? `<button class="button compact ghost" data-detach-worker="${pipeline.id}">Detach</button>` : `<button class="button compact" data-attach-worker="${pipeline.id}">Attach</button>`}</div></article>`;
    }).join('')}</div>`;
}

function workerLogs(worker) {
    const events = state.activity.filter((event) => event.worker_id === worker.id || event.message?.includes(worker.display_name));
    return activityList(events);
}

function pluginCard(plugin) {
    return `<article class="worker-card"><div><span class="platform-badge">API v${escapeHtml(plugin.api_version)}</span><h3>${escapeHtml(plugin.display_name)}</h3><p>${escapeHtml(plugin.name)}</p></div>${statusPill(plugin.enabled ? 'Enabled' : 'Disabled', plugin.enabled ? 'ok' : 'off')}</article>`;
}

function postRow(post) {
    return `<tr><td><div class="media-thumb">▧</div></td><td><strong>${escapeHtml(post.content_ref || post.caption_used || '-')}</strong><small>${escapeHtml(post.id || '')}</small></td><td>${escapeHtml(post.platform || post.worker_id || '-')}</td><td>${escapeHtml(post.account || '-')}</td><td>${formatDate(post.published_at)}</td><td>${statusPill(post.status || 'unknown', post.status || 'off')}</td><td><button class="button compact ghost">Open</button></td></tr>`;
}

function configPreview(configJson) {
    return `<div class="code-panel"><span>Current config JSON</span><pre>${escapeHtml(configJson || '{}')}</pre></div>`;
}

function settingInput(key, label, fallback, type = 'text') {
    const value = state.settings[key] ?? fallback;
    const checked = type === 'checkbox' && value ? 'checked' : '';
    const inputValue = type === 'checkbox' ? '' : `value="${escapeAttr(value)}"`;
    return `<label><span>${escapeHtml(label)}</span><div class="inline-control"><input data-setting-input="${escapeAttr(key)}" type="${type}" ${inputValue} ${checked}><button class="button compact" data-save-setting="${escapeAttr(key)}">Save</button></div></label>`;
}

function actionCard(title, count, detail, target, tone) {
    return `<button class="action-card ${tone}" data-open-attention="${target}"><span>${escapeHtml(title)}</span><strong>${count}</strong><small>${escapeHtml(detail)}</small></button>`;
}

function stageCard(title, count, detail, target, extra = '') {
    return `<button class="stage-card ${extra}" data-pipeline-tab="${target}"><span>${escapeHtml(title)}</span><strong>${count}</strong><small>${escapeHtml(detail)}</small></button>`;
}

function tabButton(tab, active, attr) {
    return `<button class="${active === tab ? 'active' : ''}" ${attr}="${tab}">${titleCase(tab)}</button>`;
}

function countProduction(status) {
    return currentData().production.filter((item) => item.status === status).length;
}

function metric(label, value, extra = '') {
    return `<article class="metric ${extra}"><span>${label}</span><strong>${value}</strong></article>`;
}
function storageMetric() {
    return `<article class="metric storage-metric"><span>Storage</span><strong>${state.settings.storage_budget_gb ? `${state.settings.storage_budget_gb} GB` : '5 GB'}</strong><div class="mini-bar"><span></span></div></article>`;
}
function scheduleMetric() {
    return `<article class="metric schedule-metric"><span>Next Scheduled Actions</span><strong>Render 02:00</strong><small>Post 08:30</small></article>`;
}
function activityTable(events) {
    if (!events.length) return emptyState('No activity recorded yet.');
    return `<div class="table-wrap"><table><thead><tr><th>Type</th><th>Time</th><th>Event</th><th>Pipeline</th></tr></thead><tbody>${events.map((event) => `<tr><td><span class="level-dot ${escapeAttr(event.level)}"></span></td><td>${formatDate(event.timestamp)}</td><td>${escapeHtml(event.message || event.event_type)}</td><td><span class="platform-badge">${escapeHtml(event.pipeline_id || 'System')}</span></td></tr>`).join('')}</tbody></table></div>`;
}
function filterBox(label, value) {
    return `<label><span>${escapeHtml(label)}</span><select><option>${escapeHtml(value)}</option></select></label>`;
}

function snapshot(label, value) {
    return `<article class="snapshot"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`;
}

function roadmap(text) {
    return `<div class="roadmap-item">${escapeHtml(text)}</div>`;
}

function panelHead(title, description, actionLabel = '', targetView = '') {
    return `<div class="panel-head"><div><h2>${title}</h2><p>${description}</p></div>${actionLabel ? `<button class="button compact" data-view="${targetView}">${actionLabel}</button>` : ''}</div>`;
}

function statusPill(label, status) {
    return `<span class="status-pill ${escapeAttr(status)}">${escapeHtml(label)}</span>`;
}

function emptyState(text, wide = false) {
    return `<div class="empty-state ${wide ? 'wide' : ''}">${escapeHtml(text)}</div>`;
}

function option(value, label, selected) {
    return `<option value="${escapeAttr(value)}" ${value === selected ? 'selected' : ''}>${escapeHtml(label)}</option>`;
}

function previewMarkup(item) {
    if (isImage(item)) return `<img src="${previewUrl(item)}" alt="${escapeAttr(item.type)}" loading="lazy">`;
    if (isVideo(item)) return `<video src="${previewUrl(item)}" preload="metadata" muted></video>`;
    return '<span>No preview</span>';
}

function ingredientDetail(item) {
    if (item.duration_secs) return `${Number(item.duration_secs).toFixed(1)} sec`;
    if (item.file_size_bytes) return `${(item.file_size_bytes / 1024 / 1024).toFixed(2)} MB`;
    return item.source_url || 'No file metadata';
}

function verseLabel(item) {
    const detected = item.detected_verses || {};
    const meta = item.content_meta || {};
    if (meta.surah && meta.ayah_end && meta.ayah_end > meta.ayah) return `${meta.surah}:${meta.ayah}-${meta.ayah_end}`;
    if (meta.surah && meta.ayah) return `${meta.surah}:${meta.ayah}`;
    if (detected.ref) return detected.ref;
    return 'Unknown verse';
}

function productionVerseSummary(item) {
    const detected = item.detected_verses || {};
    const verses = Array.isArray(detected.verses) ? detected.verses : [];
    const meta = item.content_meta || {};
    const surahName = meta.surah_name || detected.surah_name || 'Awaiting identification';
    const arabic = verses.find((verse) => verse.arabic)?.arabic || detected.arabic || meta.arabic || meta.arabic_text || '';
    const refs = verses.length ? verses.map((verse) => verse.ref).filter(Boolean) : (detected.ref ? [detected.ref] : []);
    const visibleRefs = refs.slice(0, 4).map((ref) => `<span class="verse-chip">${escapeHtml(ref)}</span>`).join('');
    const more = refs.length > 4 ? `<span class="verse-chip muted">+${refs.length - 4}</span>` : '';
    return `<div class="verse-summary">
        <div class="verse-head"><strong>${verseLabel(item)}</strong><small>${escapeHtml(surahName)}</small>${meta.manual_override ? '<span class="mini-pill">Manual</span>' : ''}</div>
        ${refs.length ? `<div class="verse-chip-row">${visibleRefs}${more}</div>` : ''}
        ${arabic ? `<p class="verse-preview" dir="rtl" lang="ar">${escapeHtml(arabic)}</p>` : '<small class="verse-muted">No detected verse text cached yet.</small>'}
    </div>`;
}

function verseTextBlock(item) {
    const detected = item.detected_verses || {};
    if (Array.isArray(detected.verses) && detected.verses.length) {
        return `<div class="verse-text verse-list">${detected.verses.map((verse) => `
            <article class="verse-item">
                <span>${escapeHtml(verse.ref || '')}</span>
                ${verse.arabic ? `<p dir="rtl" lang="ar">${escapeHtml(verse.arabic)}</p>` : ''}
            </article>
        `).join('')}</div>`;
    }
    const arabic = detected.arabic || item.content_meta?.arabic || item.content_meta?.arabic_text || '';
    const translation = detected.translation || item.content_meta?.translation || '';
    const caption = !arabic && !translation ? item.caption_text : '';
    if (!arabic && !translation && !caption) return '<small class="verse-muted">No detected verse text cached yet.</small>';
    return `<div class="verse-text">${arabic ? `<p dir="rtl" lang="ar">${escapeHtml(arabic)}</p>` : ''}${translation ? `<p>${escapeHtml(translation)}</p>` : ''}${caption ? `<p>${escapeHtml(caption)}</p>` : ''}</div>`;
}

function platformLabel(platform) {
    return { youtube: 'YouTube', instagram: 'Instagram', tiktok: 'TikTok', x: 'X' }[platform] || platform;
}

function prettyType(type) {
    return titleCase((type || 'unknown').replaceAll('_', ' '));
}

function titleCase(value) {
    return String(value).replace(/\b\w/g, (letter) => letter.toUpperCase());
}
