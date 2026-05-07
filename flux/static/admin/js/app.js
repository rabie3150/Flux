const state = {
    view: 'dashboard',
    pipelineTab: 'overview',
    workerTab: 'overview',
    dashboard: {},
    health: { status: 'unknown' },
    settings: {},
    pipelines: [],
    workers: [],
    posts: [],
    activity: [],
    pipelineData: {},
    selectedPipelineId: null,
    selectedWorkerId: null,
    selectedIngredients: new Set(),
    lastSelectedIngredientId: null,
    filters: { ingredientType: '', ingredientStatus: '', productionStatus: '' },
    backend: { posts: false, plugins: false },
    operation: null,
    operationTimer: null,
    operationPoller: null,
};
const el = {};
document.addEventListener('DOMContentLoaded', () => {
    cacheElements();
    bindShell();
    refreshAll();
    window.setInterval(refreshPassive, 30000);
});
function cacheElements() {
    el.body = document.body;
    el.view = document.querySelector('#app-view');
    el.pageTitle = document.querySelector('#page-title');
    el.pageEyebrow = document.querySelector('#page-eyebrow');
    el.topbarActions = document.querySelector('#topbar-actions');
    el.toastStack = document.querySelector('#toast-stack');
    el.healthDot = document.querySelector('#health-dot');
    el.healthLabel = document.querySelector('#health-label');
    el.modal = document.querySelector('#modal');
    el.modalTitle = document.querySelector('#modal-title');
    el.modalEyebrow = document.querySelector('#modal-eyebrow');
    el.modalBody = document.querySelector('#modal-body');
}
function bindShell() {
    document.querySelectorAll('[data-view]').forEach((button) => {
        button.addEventListener('click', () => setView(button.dataset.view));
    });
    document.querySelector('#mobile-menu').addEventListener('click', () => el.body.classList.add('nav-open'));
    document.querySelector('#mobile-backdrop').addEventListener('click', () => el.body.classList.remove('nav-open'));
    document.querySelector('#modal-close').addEventListener('click', closeModal);
    el.modal.addEventListener('click', (event) => {
        if (event.target === el.modal) closeModal();
    });
    document.addEventListener('keydown', handleGlobalShortcuts);
}
async function api(path, options = {}) {
    const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || payload.error?.message || 'Request failed');
    }
    if (response.status === 204) return null;
    return response.json();
}
async function optionalApi(path, fallback) {
    try {
        return { ok: true, data: await api(path) };
    } catch (_) {
        return { ok: false, data: fallback };
    }
}
async function refreshAll() {
    try {
        await Promise.all([loadHealth(), loadDashboard(), loadWorkers(), loadActivity(), loadSettings()]);
        await loadPipelines();
        await Promise.all([loadAllPipelineData(), loadPosts()]);
        if (!state.selectedPipelineId && state.pipelines[0]) state.selectedPipelineId = state.pipelines[0].id;
        render();
    } catch (error) {
        toast(error.message, 'error');
        render();
    }
}
async function refreshPassive() {
    try {
        await Promise.all([loadHealth(), loadDashboard(), loadActivity()]);
        await loadAllPipelineData();
        render();
    } catch (_) {
        state.health.status = 'unhealthy';
        renderHealth();
    }
}
async function loadHealth() {
    state.health = await api('/api/health');
}
async function loadDashboard() {
    state.dashboard = await api('/api/system/dashboard');
}
async function loadPipelines() {
    state.pipelines = await api('/api/pipelines');
}
async function loadWorkers() {
    state.workers = await api('/api/workers');
}
async function loadActivity() {
    const data = await api('/api/system/activity?limit=60');
    state.activity = data.events || [];
}
async function loadSettings() {
    state.settings = await api('/api/system/settings');
}
async function loadPosts() {
    const result = await optionalApi('/api/posts?limit=50', []);
    state.backend.posts = result.ok;
    state.posts = Array.isArray(result.data) ? result.data : result.data.posts || [];
}
async function loadAllPipelineData() {
    const entries = await Promise.all(state.pipelines.map(async (pipeline) => {
        const [stats, ingredients, production, workers] = await Promise.all([
            optionalApi(`/api/pipelines/${pipeline.id}/stats`, {}),
            optionalApi(`/api/pipelines/${pipeline.id}/ingredients?limit=1000`, { ingredients: [] }),
            optionalApi(`/api/pipelines/${pipeline.id}/production?limit=100`, []),
            optionalApi(`/api/pipelines/${pipeline.id}/workers`, []),
        ]);
        return [pipeline.id, {
            stats: stats.data,
            ingredients: ingredients.data.ingredients || [],
            production: production.data || [],
            workers: workers.data || [],
        }];
    }));
    state.pipelineData = Object.fromEntries(entries);
    state.selectedIngredients = new Set(
        [...state.selectedIngredients].filter((id) => currentIngredients().some((item) => item.id === id))
    );
}
async function saveSetting(key, value) {
    await api(`/api/system/settings/${encodeURIComponent(key)}`, {
        method: 'PUT',
        body: JSON.stringify({ value }),
    });
    toast('Setting saved.', 'success');
    await loadSettings();
    render();
}
function render() {
    renderChrome();
    renderHealth();
    renderView();
    bindViewEvents();
}
function renderChrome() {
    const pipeline = selectedPipeline();
    document.querySelectorAll('[data-view]').forEach((button) => {
        button.classList.toggle('active', button.dataset.view === state.view);
    });
    el.pageEyebrow.textContent = pipeline && state.view === 'pipelines' ? 'Pipeline workbench' : 'Flux admin';
    el.pageTitle.textContent = pageTitle();
    el.topbarActions.innerHTML = `
        <span class="topbar-status"><span class="health-dot ${escapeAttr(state.health.status || 'unknown')}"></span>${state.health.status === 'healthy' ? 'Status: Green' : 'Status: Check'}</span>
        <button class="button ghost" data-action="refresh" ${state.operation ? 'disabled' : ''}>Refresh</button>
        ${pipeline && state.view === 'pipelines' && state.pipelineTab !== 'production' ? `<button class="button primary" data-action="render-next" ${state.operation ? 'disabled' : ''}>Run Pipeline</button>` : ''}
    `;
}
function renderHealth() {
    el.healthDot.className = `health-dot ${escapeAttr(state.health.status || 'unknown')}`;
    el.healthLabel.textContent = state.health.status === 'healthy' ? 'Daemon healthy' : 'Health unknown';
}
function renderView() {
    const templates = {
        dashboard: dashboardTemplate,
        pipelines: pipelinesTemplate,
        workers: workersTemplate,
        posts: postsTemplate,
        system: systemTemplate,
        plugins: pluginsTemplate,
        activity: activityTemplate,
    };
    el.view.innerHTML = (templates[state.view] || templates.dashboard)();
}
function bindViewEvents() {
    el.view.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
    el.topbarActions.querySelector('[data-action="refresh"]')?.addEventListener('click', refreshAll);
    el.topbarActions.querySelector('[data-action="render-next"]')?.addEventListener('click', triggerRender);
    el.view.querySelector('#create-pipeline-form')?.addEventListener('submit', createPipeline);
    el.view.querySelector('#create-worker-form')?.addEventListener('submit', createWorker);
    el.view.querySelectorAll('[data-open-pipeline]').forEach((button) => button.addEventListener('click', () => openPipeline(button.dataset.openPipeline)));
    el.view.querySelectorAll('[data-toggle-pipeline]').forEach((button) => button.addEventListener('click', () => togglePipeline(button.dataset.togglePipeline)));
    el.view.querySelectorAll('[data-delete-pipeline]').forEach((button) => button.addEventListener('click', () => deletePipeline(button.dataset.deletePipeline)));
    el.view.querySelectorAll('[data-pipeline-tab]').forEach((button) => button.addEventListener('click', () => setPipelineTab(button.dataset.pipelineTab)));
    el.view.querySelectorAll('[data-open-attention]').forEach((button) => button.addEventListener('click', () => openAttention(button.dataset.openAttention)));
    el.view.querySelectorAll('[data-open-worker]').forEach((button) => button.addEventListener('click', () => openWorker(button.dataset.openWorker)));
    el.view.querySelectorAll('[data-worker-tab]').forEach((button) => button.addEventListener('click', () => setWorkerTab(button.dataset.workerTab)));
    el.view.querySelectorAll('[data-toggle-worker]').forEach((button) => button.addEventListener('click', () => toggleWorker(button.dataset.toggleWorker)));
    el.view.querySelectorAll('[data-delete-worker]').forEach((button) => button.addEventListener('click', () => deleteWorker(button.dataset.deleteWorker)));
    el.view.querySelectorAll('[data-attach-worker]').forEach((button) => button.addEventListener('click', () => attachWorker(button.dataset.attachWorker)));
    el.view.querySelectorAll('[data-detach-worker]').forEach((button) => button.addEventListener('click', () => detachWorker(button.dataset.detachWorker)));
    el.view.querySelectorAll('[data-attach-pipeline-worker]').forEach((button) => button.addEventListener('click', () => attachPipelineWorker(button.dataset.attachPipelineWorker)));
    el.view.querySelectorAll('[data-detach-pipeline-worker]').forEach((button) => button.addEventListener('click', () => detachPipelineWorker(button.dataset.detachPipelineWorker)));
    el.view.querySelectorAll('[data-save-setting]').forEach((button) => button.addEventListener('click', () => saveSettingFromInput(button.dataset.saveSetting)));
    el.view.querySelector('[data-action="create-worker"]')?.addEventListener('click', openCreateWorkerModal);
    el.view.querySelectorAll('[data-action="post-now"]').forEach((button) => button.addEventListener('click', () => triggerPostNow(button.dataset.workerId)));
    bindWorkbenchEvents();
}
function bindWorkbenchEvents() {
    el.view.querySelector('#ingredient-type')?.addEventListener('change', (event) => {
        state.filters.ingredientType = event.target.value;
        render();
    });
    el.view.querySelector('#ingredient-status')?.addEventListener('change', (event) => {
        state.filters.ingredientStatus = event.target.value;
        render();
    });
    el.view.querySelector('#production-status')?.addEventListener('change', (event) => {
        state.filters.productionStatus = event.target.value;
        render();
    });
    el.view.querySelector('[data-action="fetch"]')?.addEventListener('click', triggerFetch);
    el.view.querySelector('[data-action="render-next"]')?.addEventListener('click', triggerRender);
    el.view.querySelector('[data-action="approve"]')?.addEventListener('click', bulkApprove);
    el.view.querySelector('[data-action="reject"]')?.addEventListener('click', bulkReject);
    el.view.querySelector('[data-action="select-all-ingredients"]')?.addEventListener('click', selectAllIngredients);
    el.view.querySelector('[data-action="clear-ingredients"]')?.addEventListener('click', clearIngredientSelection);
    el.view.querySelector('[data-action="invert-ingredients"]')?.addEventListener('click', invertIngredientSelection);
    el.view.querySelector('[data-action="save-pipeline"]')?.addEventListener('click', saveSelectedPipeline);
    el.view.querySelector('#selected-pipeline-name')?.addEventListener('input', (event) => { selectedPipeline().name = event.target.value; });
    el.view.querySelector('#selected-pipeline-enabled')?.addEventListener('change', (event) => { selectedPipeline().enabled = event.target.checked; });
    el.view.querySelectorAll('[data-select-ingredient]').forEach((input) => {
        input.addEventListener('click', (event) => {
            event.stopPropagation();
            handleIngredientSelection(input.value, event, input.checked);
        });
    });
    el.view.querySelectorAll('[data-preview-ingredient]').forEach((button) => button.addEventListener('click', (event) => {
        if (event.ctrlKey || event.metaKey || event.shiftKey) return handleIngredientSelection(button.dataset.previewIngredient, event);
        previewIngredient(button.dataset.previewIngredient);
    }));
    el.view.querySelectorAll('[data-ingredient-card]').forEach((card) => card.addEventListener('click', (event) => {
        if (event.target.closest('button, input, label')) return;
        handleIngredientSelection(card.dataset.ingredientCard, event);
    }));
    el.view.querySelectorAll('[data-preview-production]').forEach((button) => button.addEventListener('click', () => previewProduction(button.dataset.previewProduction)));
    el.view.querySelectorAll('[data-identify-production]').forEach((button) => button.addEventListener('click', () => openIdentify(button.dataset.identifyProduction)));
    el.view.querySelectorAll('[data-redo-ai-production]').forEach((button) => button.addEventListener('click', () => redoAiProduction(button.dataset.redoAiProduction)));
}
function handleIngredientSelection(id, event, forcedChecked = null) {
    const visibleIds = currentIngredients().map((item) => item.id);
    if (event.shiftKey && state.lastSelectedIngredientId && visibleIds.includes(state.lastSelectedIngredientId)) {
        const start = visibleIds.indexOf(state.lastSelectedIngredientId);
        const end = visibleIds.indexOf(id);
        const [from, to] = start < end ? [start, end] : [end, start];
        visibleIds.slice(from, to + 1).forEach((itemId) => state.selectedIngredients.add(itemId));
    } else if (forcedChecked !== null) {
        if (forcedChecked) state.selectedIngredients.add(id);
        else state.selectedIngredients.delete(id);
    } else if (event.ctrlKey || event.metaKey || state.selectedIngredients.has(id)) {
        if (state.selectedIngredients.has(id)) state.selectedIngredients.delete(id);
        else state.selectedIngredients.add(id);
    } else {
        state.selectedIngredients.clear();
        state.selectedIngredients.add(id);
    }
    state.lastSelectedIngredientId = id;
    render();
}
function selectAllIngredients() {
    currentIngredients().forEach((item) => state.selectedIngredients.add(item.id));
    render();
}
function clearIngredientSelection() {
    state.selectedIngredients.clear();
    state.lastSelectedIngredientId = null;
    render();
}
function invertIngredientSelection() {
    currentIngredients().forEach((item) => {
        if (state.selectedIngredients.has(item.id)) state.selectedIngredients.delete(item.id);
        else state.selectedIngredients.add(item.id);
    });
    render();
}
function handleGlobalShortcuts(event) {
    const typing = ['INPUT', 'SELECT', 'TEXTAREA'].includes(event.target.tagName);
    if (typing || state.view !== 'pipelines' || state.pipelineTab !== 'ingredients') return;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') {
        event.preventDefault();
        selectAllIngredients();
    }
    if (event.key === 'Escape' && state.selectedIngredients.size) {
        clearIngredientSelection();
    }
}
async function createPipeline(event) {
    event.preventDefault();
    const form = new FormData(event.target);
    const name = String(form.get('name') || '').trim();
    if (!name) return toast('Pipeline name is required.', 'error');
    await api('/api/pipelines', { method: 'POST', body: JSON.stringify({ name, plugin_id: form.get('plugin_id'), config: {}, enabled: form.get('enabled') === 'on' }) });
    toast('Pipeline created.', 'success');
    await refreshAll();
}
async function saveSelectedPipeline() {
    const pipeline = selectedPipeline();
    if (!pipeline) return;
    await api(`/api/pipelines/${pipeline.id}`, { method: 'PUT', body: JSON.stringify({ name: pipeline.name, enabled: pipeline.enabled }) });
    toast('Pipeline saved.', 'success');
    await refreshAll();
}
async function togglePipeline(id) {
    const pipeline = state.pipelines.find((item) => item.id === id);
    if (!pipeline) return;
    await api(`/api/pipelines/${id}`, { method: 'PUT', body: JSON.stringify({ enabled: !pipeline.enabled }) });
    toast(!pipeline.enabled ? 'Pipeline resumed.' : 'Pipeline paused.', 'success');
    await refreshAll();
}
async function deletePipeline(id) {
    const pipeline = state.pipelines.find((item) => item.id === id);
    if (!pipeline || !window.confirm(`Delete ${pipeline.name} and all related data?`)) return;
    await api(`/api/pipelines/${id}`, { method: 'DELETE' });
    if (state.selectedPipelineId === id) state.selectedPipelineId = null;
    await refreshAll();
}
const WORKER_CREDENTIAL_SCHEMAS = {
    youtube: {
        official: [
            { name: 'client_id', label: 'OAuth Client ID', type: 'text' },
            { name: 'client_secret', label: 'OAuth Client Secret', type: 'password' },
            { name: 'refresh_token', label: 'Refresh Token', type: 'password' },
        ],
        third_party: [
            { name: 'api_key', label: 'Provider API Key', type: 'password' },
        ],
    },
    tiktok: {
        official: [
            { name: 'app_id', label: 'App ID', type: 'text' },
            { name: 'app_secret', label: 'App Secret', type: 'password' },
            { name: 'access_token', label: 'Access Token', type: 'password' },
            { name: 'advertiser_id', label: 'Advertiser ID', type: 'text' },
        ],
        third_party: [
            { name: 'api_key', label: 'Provider API Key', type: 'password' },
        ],
    },
    instagram: {
        official: [
            { name: 'app_id', label: 'App ID', type: 'text' },
            { name: 'app_secret', label: 'App Secret', type: 'password' },
            { name: 'access_token', label: 'Access Token', type: 'password' },
            { name: 'instagram_account_id', label: 'Instagram Account ID', type: 'text' },
        ],
        unofficial: [
            { name: 'username', label: 'Username', type: 'text' },
            { name: 'password', label: 'Password', type: 'password' },
            { name: 'session_json', label: 'Session JSON (optional)', type: 'textarea' },
        ],
        third_party: [
            { name: 'api_key', label: 'Provider API Key', type: 'password' },
        ],
    },
    x: {
        official: [
            { name: 'api_key', label: 'API Key', type: 'text' },
            { name: 'api_secret', label: 'API Secret', type: 'password' },
            { name: 'access_token', label: 'Access Token', type: 'password' },
            { name: 'access_token_secret', label: 'Access Token Secret', type: 'password' },
        ],
        third_party: [
            { name: 'api_key', label: 'Provider API Key', type: 'password' },
        ],
    },
};
const THIRD_PARTY_PROVIDERS = ['buffer', 'hootsuite', 'socialpilot'];
function credentialFieldsHtml(platform, strategy) {
    const schema = WORKER_CREDENTIAL_SCHEMAS[platform]?.[strategy] || [];
    return schema.map((field) => {
        if (field.type === 'textarea') {
            return `<label><span>${escapeHtml(field.label)}</span><textarea name="cred_${field.name}" rows="3" placeholder="${escapeAttr(field.label)}"></textarea></label>`;
        }
        return `<label><span>${escapeHtml(field.label)}</span><input name="cred_${field.name}" type="${escapeAttr(field.type)}" placeholder="${escapeAttr(field.label)}"></label>`;
    }).join('');
}
function openCreateWorkerModal() {
    el.modalTitle.textContent = 'Connect Worker';
    el.modalEyebrow.textContent = 'Platform Publisher';
    el.modalBody.innerHTML = `
        <form class="form-stack" id="create-worker-form">
            <label><span>Platform</span>
                <select name="platform" id="worker-platform">
                    <option value="youtube">YouTube</option>
                    <option value="tiktok">TikTok</option>
                    <option value="instagram">Instagram</option>
                    <option value="x">X / Twitter</option>
                </select>
            </label>
            <label><span>Display name</span><input name="display_name" type="text" placeholder="My YouTube Channel"></label>
            <label><span>Connection strategy</span>
                <select name="connection_strategy" id="worker-strategy">
                    <option value="official">Official API</option>
                    <option value="unofficial">Unofficial / Cookie-based</option>
                    <option value="third_party">Third-party service</option>
                </select>
            </label>
            <div id="third-party-provider" class="hidden">
                <label><span>Third-party provider</span>
                    <select name="third_party_provider">
                        ${THIRD_PARTY_PROVIDERS.map((p) => `<option value="${escapeAttr(p)}">${escapeHtml(titleCase(p))}</option>`).join('')}
                    </select>
                </label>
            </div>
            <div id="credential-fields" class="form-stack"></div>
            <label><span>Schedule (cron, optional)</span><input name="schedule_cron" type="text" placeholder="0 8 * * *"></label>
            <label><span>Hashtags (comma-separated, optional)</span><input name="hashtags" type="text" placeholder="Quran, Islam, Reminder"></label>
            <button class="button primary" type="submit">Create Worker</button>
        </form>`;
    el.modal.classList.remove('hidden');
    document.querySelector('#create-worker-form').addEventListener('submit', createWorker);
    const platformSelect = document.querySelector('#worker-platform');
    const strategySelect = document.querySelector('#worker-strategy');
    const providerDiv = document.querySelector('#third-party-provider');
    const credContainer = document.querySelector('#credential-fields');
    function refreshFields() {
        const platform = platformSelect.value;
        const strategy = strategySelect.value;
        const schema = WORKER_CREDENTIAL_SCHEMAS[platform] || {};
        // Hide/show unofficial option depending on platform support
        Array.from(strategySelect.options).forEach((opt) => {
            if (opt.value === 'unofficial') {
                opt.style.display = schema.unofficial ? '' : 'none';
            }
        });
        // If current platform doesn't support unofficial, switch to official
        if (strategy === 'unofficial' && !schema.unofficial) {
            strategySelect.value = 'official';
        }
        const effectiveStrategy = strategySelect.value;
        providerDiv.classList.toggle('hidden', effectiveStrategy !== 'third_party');
        credContainer.innerHTML = credentialFieldsHtml(platform, effectiveStrategy);
    }
    platformSelect.addEventListener('change', refreshFields);
    strategySelect.addEventListener('change', refreshFields);
    refreshFields();
}
async function createWorker(event) {
    event.preventDefault();
    const form = new FormData(event.target);
    const displayName = String(form.get('display_name') || '').trim();
    if (!displayName) return toast('Worker display name is required.', 'error');
    const platform = form.get('platform');
    const strategy = form.get('connection_strategy');
    const credentials = {};
    // Gather credential fields prefixed with cred_
    for (const [key, value] of form.entries()) {
        if (key.startsWith('cred_')) {
            credentials[key.slice(5)] = String(value || '').trim();
        }
    }
    const payload = {
        platform,
        display_name: displayName,
        connection_strategy: strategy,
        credentials,
        schedule_cron: form.get('schedule_cron') || null,
        hashtags: String(form.get('hashtags') || '').split(',').map((s) => s.trim()).filter(Boolean),
        enabled: true,
    };
    if (strategy === 'third_party') {
        payload.third_party_provider = form.get('third_party_provider');
    }
    await api('/api/workers', { method: 'POST', body: JSON.stringify(payload) });
    closeModal();
    toast('Worker created.', 'success');
    await refreshAll();
}
async function triggerPostNow(workerId) {
    if (!workerId) return;
    if (state.operation) return toast('Another backend operation is already running.', 'error');
    const worker = state.workers.find((w) => w.id === workerId);
    const label = worker ? `Posting to ${worker.display_name}` : 'Posting now';
    startOperation('post', { id: workerId, name: worker?.display_name || 'Worker' }, label, [
        'Building platform-specific caption',
        'Uploading video to platform',
        'Recording post result',
    ]);
    try {
        const result = await api(`/api/workers/${workerId}/post`, { method: 'POST' });
        await loadAllPipelineData();
        finishOperation(result.url ? `Posted: ${result.url}` : 'Post completed.', 'success');
    } catch (error) {
        finishOperation(error.message, 'error');
    }
}

async function toggleWorker(id) {
    const worker = state.workers.find((item) => item.id === id);
    if (!worker) return;
    await api(`/api/workers/${id}`, { method: 'PUT', body: JSON.stringify({ enabled: !worker.enabled }) });
    toast(!worker.enabled ? 'Worker resumed.' : 'Worker paused.', 'success');
    await refreshAll();
}
async function deleteWorker(id) {
    const worker = state.workers.find((item) => item.id === id);
    if (!worker || !window.confirm(`Delete ${worker.display_name}?`)) return;
    await api(`/api/workers/${id}`, { method: 'DELETE' });
    if (state.selectedWorkerId === id) state.selectedWorkerId = null;
    await refreshAll();
}
async function attachWorker(pipelineId) {
    const worker = selectedWorker();
    if (!worker) return;
    await api(`/api/pipelines/${pipelineId}/workers`, { method: 'POST', body: JSON.stringify({ worker_id: worker.id }) });
    toast('Worker attached.', 'success');
    await refreshAll();
}
async function detachWorker(pipelineId) {
    const worker = selectedWorker();
    if (!worker) return;
    await api(`/api/pipelines/${pipelineId}/workers/${worker.id}`, { method: 'DELETE' });
    toast('Worker detached.', 'success');
    await refreshAll();
}
async function attachPipelineWorker(workerId) {
    const pipeline = selectedPipeline();
    if (!pipeline) return;
    await api(`/api/pipelines/${pipeline.id}/workers`, { method: 'POST', body: JSON.stringify({ worker_id: workerId }) });
    toast('Worker attached.', 'success');
    await refreshAll();
}
async function detachPipelineWorker(workerId) {
    const pipeline = selectedPipeline();
    if (!pipeline) return;
    await api(`/api/pipelines/${pipeline.id}/workers/${workerId}`, { method: 'DELETE' });
    toast('Worker detached.', 'success');
    await refreshAll();
}
async function triggerFetch() {
    const pipeline = selectedPipeline();
    if (!pipeline) return;
    if (state.operation) return toast('Another backend operation is already running.', 'error');
    startOperation('fetch', pipeline, 'Fetching ingredients', [
        'Calling the content plugin',
        'Downloading clips and backgrounds',
        'Saving new ingredients as pending',
        'Refreshing stock levels',
    ]);
    try {
        const result = await api(`/api/pipelines/${pipeline.id}/trigger`, { method: 'POST', body: JSON.stringify({ action: 'fetch' }) });
        await loadAllPipelineData();
        finishOperation(result.message || 'Fetch completed. New ingredients are ready for review.', 'success');
    } catch (error) {
        finishOperation(error.message, 'error');
    }
}
async function triggerRender() {
    const pipeline = selectedPipeline();
    if (!pipeline) return;
    if (state.operation) return toast('Another backend operation is already running.', 'error');
    startOperation('render', pipeline, 'Rendering next video', [
        'Selecting approved ingredients',
        'Waiting for the global render lock',
        'Running FFmpeg composition',
        'Extracting thumbnail and updating queue',
    ]);
    try {
        const result = await api(`/api/pipelines/${pipeline.id}/trigger`, { method: 'POST', body: JSON.stringify({ action: 'render' }) });
        await loadAllPipelineData();
        finishOperation(result.message || 'Render completed. Production queue has been refreshed.', 'success');
    } catch (error) {
        finishOperation(error.message, 'error');
    }
}
function startOperation(type, pipeline, label, steps) {
    if (state.operation) return;
    state.operation = {
        type,
        pipelineId: pipeline.id,
        pipelineName: pipeline.name,
        label,
        steps,
        startedAt: Date.now(),
        elapsed: 0,
        pulse: 0,
    };
    toast(`${label} started for ${pipeline.name}.`, 'success');
    clearOperationTimers();
    state.operationTimer = window.setInterval(() => {
        if (!state.operation) return;
        state.operation.elapsed = Math.floor((Date.now() - state.operation.startedAt) / 1000);
        state.operation.pulse += 1;
        render();
    }, 1000);
    state.operationPoller = window.setInterval(async () => {
        try {
            await Promise.all([loadActivity(), loadHealth()]);
            render();
        } catch (_) {
            // The main request will surface final operation errors.
        }
    }, 5000);
    render();
}
function finishOperation(message, type) {
    clearOperationTimers();
    const elapsed = state.operation?.elapsed || 0;
    state.operation = null;
    toast(`${message} (${formatDuration(elapsed)})`, type);
    render();
}
function clearOperationTimers() {
    if (state.operationTimer) window.clearInterval(state.operationTimer);
    if (state.operationPoller) window.clearInterval(state.operationPoller);
    state.operationTimer = null;
    state.operationPoller = null;
}
async function bulkApprove() {
    await bulkIngredientAction('approve', 'Approved');
}
async function bulkReject() {
    if (state.selectedIngredients.size && !window.confirm(`Reject ${state.selectedIngredients.size} ingredients?`)) return;
    await bulkIngredientAction('reject', 'Rejected');
}
async function bulkIngredientAction(action, label) {
    const pipeline = selectedPipeline();
    const ids = [...state.selectedIngredients];
    if (!pipeline || !ids.length) return toast('Select ingredients first.', 'error');
    await api(`/api/pipelines/${pipeline.id}/ingredients/${action}`, { method: 'POST', body: JSON.stringify({ ingredient_ids: ids }) });
    toast(`${label} ${ids.length} ingredients.`, 'success');
    state.selectedIngredients.clear();
    await loadAllPipelineData();
    render();
}
function setView(view) {
    state.view = view;
    el.body.classList.remove('nav-open');
    render();
}
function openPipeline(id) {
    state.selectedPipelineId = id;
    state.view = 'pipelines';
    state.pipelineTab = 'overview';
    render();
}
function openWorker(id) {
    state.selectedWorkerId = id;
    state.view = 'workers';
    state.workerTab = 'overview';
    render();
}
function setPipelineTab(tab) {
    state.pipelineTab = tab;
    render();
}
function setWorkerTab(tab) {
    state.workerTab = tab;
    render();
}
function openAttention(target) {
    if (target === 'workers') return setView('workers');
    if (!selectedPipeline() && state.pipelines[0]) state.selectedPipelineId = state.pipelines[0].id;
    state.view = 'pipelines';
    state.pipelineTab = target === 'ingredients' ? 'ingredients' : 'production';
    render();
}
function saveSettingFromInput(key) {
    const input = el.view.querySelector(`[data-setting-input="${key}"]`);
    const raw = input?.type === 'checkbox' ? input.checked : input?.value;
    const value = input?.type === 'number' ? Number(raw) : raw;
    saveSetting(key, value);
}
function previewIngredient(id) {
    const item = currentIngredients().find((ingredient) => ingredient.id === id);
    if (!item) return;
    openMediaModal({ title: prettyType(item.type), eyebrow: item.status, kind: isVideo(item) ? 'video' : 'image', src: previewUrl(item) });
}
function previewProduction(id) {
    const item = currentProduction().find((content) => content.id === id);
    const pipeline = selectedPipeline();
    if (!item || !pipeline) return;
    openMediaModal({
        title: verseLabel(item),
        eyebrow: `${item.status} / ${item.detected_verses?.surah_name || item.content_meta?.surah_name || 'Verse review'}`,
        kind: 'video',
        src: `/api/pipelines/${pipeline.id}/production/${item.id}/stream`,
        detail: verseTextBlock(item),
    });
}
function openIdentify(id) {
    const item = currentProduction().find((content) => content.id === id);
    if (!item) return;
    el.modalTitle.textContent = 'Assign Verse';
    el.modalEyebrow.textContent = 'Manual Review';
    el.modalBody.innerHTML = `
        <form class="form-stack identify-form" id="identify-form">
            <label><span>Surah number</span><input name="surah" type="number" min="1" max="114" value="${escapeAttr(item.content_meta?.surah || '')}"></label>
            <label><span>Start ayah</span><input name="ayah" type="number" min="1" value="${escapeAttr(item.content_meta?.ayah || '')}"></label>
            <label><span>End ayah</span><input name="ayah_end" type="number" min="1" value="${escapeAttr(item.content_meta?.ayah_end || '')}" placeholder="Optional"></label>
            ${verseTextBlock(item)}
            <button class="button primary" type="submit">Mark Ready</button>
        </form>`;
    el.modal.classList.remove('hidden');
    document.querySelector('#identify-form').addEventListener('submit', (event) => manualIdentify(event, id));
}
async function manualIdentify(event, id) {
    event.preventDefault();
    const pipeline = selectedPipeline();
    const form = new FormData(event.target);
    const surah = Number(form.get('surah'));
    const ayah = Number(form.get('ayah'));
    const ayahEnd = Number(form.get('ayah_end'));
    if (!pipeline || !surah || !ayah) return toast('Surah and ayah are required.', 'error');
    const payload = { surah, ayah, identified_by: 'manual', manual_override: true, ayah_end: null };
    if (ayahEnd && ayahEnd > ayah) payload.ayah_end = ayahEnd;
    await api(`/api/pipelines/${pipeline.id}/production/${id}/identify`, { method: 'POST', body: JSON.stringify(payload) });
    closeModal();
    await loadAllPipelineData();
    render();
}
async function redoAiProduction(id) {
    const pipeline = selectedPipeline();
    if (!pipeline) return;
    
    startOperation('identify', pipeline, 'Re-running AI Verse Detection', [
        'Querying AI model for verse matching',
        'Fetching translations from Quran API'
    ]);
    
    try {
        const result = await api(`/api/pipelines/${pipeline.id}/production/${id}/redo-ai`, { method: 'POST' });
        await loadAllPipelineData();
        const success = result.status === 'ready';
        finishOperation(success ? 'AI detection successful.' : 'AI detection failed to find a match.', success ? 'success' : 'error');
    } catch (error) {
        finishOperation(error.message, 'error');
    }
}
function openMediaModal({ title, eyebrow, kind, src, detail = '' }) {
    el.modalTitle.textContent = title;
    el.modalEyebrow.textContent = eyebrow;
    el.modalBody.innerHTML = kind === 'video'
        ? `<video src="${escapeAttr(src)}" controls autoplay playsinline></video>${detail}`
        : `<img src="${escapeAttr(src)}" alt="${escapeAttr(title)}">${detail}`;
    el.modal.classList.remove('hidden');
}
function closeModal() {
    el.modal.classList.add('hidden');
    el.modalBody.innerHTML = '';
}
function selectedPipeline() {
    return state.pipelines.find((pipeline) => pipeline.id === state.selectedPipelineId) || null;
}
function selectedWorker() {
    return state.workers.find((worker) => worker.id === state.selectedWorkerId) || null;
}
function currentData() {
    return state.pipelineData[state.selectedPipelineId] || { stats: {}, ingredients: [], production: [], workers: [] };
}
function currentIngredients() {
    return currentData().ingredients.filter((item) => {
        return (!state.filters.ingredientType || item.type === state.filters.ingredientType)
            && (!state.filters.ingredientStatus || item.status === state.filters.ingredientStatus);
    });
}
function currentProduction() {
    return currentData().production.filter((item) => !state.filters.productionStatus || item.status === state.filters.productionStatus);
}
function allIngredients() {
    return Object.values(state.pipelineData).flatMap((data) => data.ingredients || []);
}
function allProduction() {
    return Object.values(state.pipelineData).flatMap((data) => data.production || []);
}
function pluginInventory() {
    const names = new Set(['quran_shorts']);
    state.pipelines.forEach((pipeline) => names.add(pipeline.plugin_id));
    return [...names].map((name) => ({ name, display_name: name === 'quran_shorts' ? 'Quran Shorts' : name, enabled: true, api_version: '1' }));
}
function pageTitle() {
    const pipeline = selectedPipeline();
    if (pipeline && state.view === 'pipelines') return pipeline.name;
    return {
        dashboard: 'Operations Dashboard',
        pipelines: 'Pipelines',
        workers: 'Platform Workers',
        posts: 'Post Log',
        system: 'System',
        plugins: 'Plugins',
        activity: 'Activity Log',
    }[state.view] || 'Flux';
}
function isVideo(item) {
    return /\.(mp4|mov|webm)$/i.test(item.file_path || '');
}
function isImage(item) {
    return /\.(jpg|jpeg|png|webp)$/i.test(item.file_path || '');
}
function previewUrl(item) {
    return `/api/pipelines/${item.pipeline_id}/ingredients/${item.id}/preview`;
}
function formatDate(value) {
    if (!value) return '-';
    return new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function shortDate(value) {
    if (!value) return '-';
    return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}
function toast(message, type = 'success') {
    const item = document.createElement('div');
    item.className = `toast ${type}`;
    item.textContent = message;
    el.toastStack.appendChild(item);
    window.setTimeout(() => item.remove(), 4200);
}
function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}
function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, '&#96;');
}
