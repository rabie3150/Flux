/** Flux Admin — Application Shell */

import { createStore } from './state.js';
import { api, optionalApi } from './api.js';
import { toast } from './components/toast.js';
import { openModal, closeModal } from './components/modal.js';
import { renderDashboard } from './views/dashboard.js';
import { renderPipelines, pipelineModal } from './views/pipelines.js';
import { renderWorkers, workerModal, refreshCredentialFields } from './views/workers.js';
import { renderPosts } from './views/posts.js';
import { renderSystem } from './views/system.js';
import { renderActivity } from './views/activity.js';
import { escapeHtml, escapeAttr, formatDate, formatDuration, platformLabel } from './utils.js';

// ── Global State ───────────────────────────────────────────────────────────
const store = createStore({
    view: 'dashboard',
    health: {},
    dashboard: {},
    pipelines: [],
    workers: [],
    posts: [],
    activity: [],
    plugins: [],
    settings: {},
    pipelineData: {},
    postFilters: {},
    selectedPipelineId: null,
    selectedWorkerId: null,
    selectedIngredients: new Set(),
    filters: { ingredientType: '', ingredientStatus: '', productionStatus: '' },
    operation: null,
    operationTimer: null,
    operationPoller: null,
});

const els = {};

// ── Bootstrap ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    cacheElements();
    bindShell();
    refreshAll();
    setInterval(refreshPassive, 10000);
});

function cacheElements() {
    els.body = document.body;
    els.view = document.querySelector('#app-view');
    els.pageTitle = document.querySelector('#page-title');
    els.pageEyebrow = document.querySelector('#page-eyebrow');
    els.topbarActions = document.querySelector('#topbar-actions');
    els.healthDot = document.querySelector('#health-dot');
    els.healthLabel = document.querySelector('#health-label');
}

function bindShell() {
    document.querySelectorAll('[data-view]').forEach((b) => {
        b.addEventListener('click', () => setView(b.dataset.view));
    });
    document.querySelector('#bottom-nav')?.querySelectorAll('button').forEach((b) => {
        b.addEventListener('click', () => setView(b.dataset.view));
    });
    document.querySelector('#mobile-menu')?.addEventListener('click', () => els.body.classList.add('nav-open'));
    document.querySelector('#mobile-backdrop')?.addEventListener('click', () => els.body.classList.remove('nav-open'));
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && store.get('selectedIngredients').size) {
            store.set('selectedIngredients', new Set());
            render();
        }
    });
}

// ── Data Loading ───────────────────────────────────────────────────────────
async function refreshAll() {
    try {
        await Promise.all([loadHealth(), loadDashboard(), loadWorkers(), loadActivity(), loadSettings(), loadPlugins()]);
        await loadPipelines();
        await Promise.all([loadAllPipelineData(), loadPosts()]);
        if (!store.get('selectedPipelineId') && store.get('pipelines')[0]) {
            store.set('selectedPipelineId', store.get('pipelines')[0].id);
        }
        render();
    } catch (err) {
        toast(err.message, 'error');
        render();
    }
}

async function refreshPassive() {
    try {
        await Promise.all([loadHealth(), loadDashboard(), loadActivity()]);
        await loadAllPipelineData();
        render();
    } catch {
        store.set('health', { status: 'unhealthy' });
        renderHealth();
    }
}

async function loadHealth() { store.set('health', await api('/api/health')); }
async function loadDashboard() { store.set('dashboard', await api('/api/system/dashboard')); }
async function loadPipelines() { store.set('pipelines', await api('/api/pipelines')); }
async function loadWorkers() { store.set('workers', await api('/api/workers')); }
async function loadActivity() { const d = await api('/api/system/activity?limit=60'); store.set('activity', d.events || []); }
async function loadSettings() { store.set('settings', await api('/api/system/settings')); }
async function loadPlugins() { store.set('plugins', await api('/api/system/plugins')); }

async function loadPosts() {
    const filters = store.get('postFilters');
    const params = new URLSearchParams();
    if (filters.platform) params.set('platform', filters.platform);
    if (filters.status) params.set('status', filters.status);
    if (filters.pipeline_id) params.set('pipeline_id', filters.pipeline_id);
    params.set('limit', '50');
    const result = await optionalApi(`/api/posts?${params.toString()}`, { posts: [], total: 0 });
    store.set('posts', result.data.posts || []);
}

async function loadAllPipelineData() {
    const pipelines = store.get('pipelines');
    const entries = await Promise.all(pipelines.map(async (p) => {
        const [stats, ingredients, production, workers] = await Promise.all([
            optionalApi(`/api/pipelines/${p.id}/stats`, {}),
            optionalApi(`/api/pipelines/${p.id}/ingredients?limit=1000`, { ingredients: [] }),
            optionalApi(`/api/pipelines/${p.id}/production?limit=100`, []),
            optionalApi(`/api/pipelines/${p.id}/workers`, []),
        ]);
        return [p.id, { stats: stats.data, ingredients: ingredients.data.ingredients || [], production: production.data || [], workers: workers.data || [] }];
    }));
    const data = Object.fromEntries(entries);
    store.set('pipelineData', data);
}

// ── Rendering ──────────────────────────────────────────────────────────────
function render() {
    const view = store.get('view');
    const state = store.get();

    // Chrome
    document.querySelectorAll('[data-view]').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
    document.querySelector('#bottom-nav')?.querySelectorAll('button').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
    const pipeline = state.pipelines.find((p) => p.id === state.selectedPipelineId);
    els.pageEyebrow.textContent = pipeline && view === 'pipelines' ? 'Pipeline workbench' : 'Flux admin';
    els.pageTitle.textContent = pageTitle(state);
    els.topbarActions.innerHTML = `
        <button class="button ghost" data-action="refresh">Refresh</button>
        ${pipeline && view === 'pipelines' ? `<button class="button primary" data-action="render-next" ${state.operation ? 'disabled' : ''}>Run Pipeline</button>` : ''}`;

    renderHealth();

    // View
    const templates = {
        dashboard: renderDashboard,
        pipelines: renderPipelines,
        workers: renderWorkers,
        posts: renderPosts,
        system: renderSystem,
        activity: renderActivity,
    };
    els.view.innerHTML = (templates[view] || renderDashboard)(state);
    bindViewEvents();
}

function renderHealth() {
    const status = store.get('health').status || 'unknown';
    els.healthDot.className = `health-dot ${status}`;
    els.healthLabel.textContent = status === 'healthy' ? 'Daemon healthy' : 'Health unknown';
}

function pageTitle(state) {
    const pipeline = state.pipelines.find((p) => p.id === state.selectedPipelineId);
    if (pipeline && state.view === 'pipelines') return pipeline.name;
    const map = { dashboard: 'Operations Dashboard', pipelines: 'Pipelines', workers: 'Workers', posts: 'Post Log', system: 'System', activity: 'Activity Log' };
    return map[state.view] || 'Flux';
}

// ── Event Binding ──────────────────────────────────────────────────────────
function bindViewEvents() {
    const state = store.get();

    // Navigation
    els.topbarActions.querySelector('[data-action="refresh"]')?.addEventListener('click', refreshAll);
    els.view.querySelectorAll('[data-nav]').forEach((b) => b.addEventListener('click', () => {
        if (b.dataset.tab) store.set('pipelineTab', b.dataset.tab);
        setView(b.dataset.nav);
    }));

    // Pipelines
    els.view.querySelectorAll('[data-open-pipeline]').forEach((b) => b.addEventListener('click', () => { store.set('selectedPipelineId', b.dataset.openPipeline); store.set('pipelineTab', 'overview'); render(); }));
    els.view.querySelectorAll('[data-action="create-pipeline"]').forEach((b) => b.addEventListener('click', openCreatePipelineModal));
    els.view.querySelectorAll('[data-action="back-pipelines"]').forEach((b) => b.addEventListener('click', () => { store.set('selectedPipelineId', null); render(); }));
    els.view.querySelectorAll('[data-toggle-pipeline]').forEach((b) => b.addEventListener('click', () => togglePipeline(b.dataset.togglePipeline)));
    els.view.querySelectorAll('[data-pipeline-tab]').forEach((b) => b.addEventListener('click', () => { store.set('pipelineTab', b.dataset.pipelineTab); render(); }));
    els.view.querySelectorAll('[data-delete-pipeline]').forEach((b) => b.addEventListener('click', () => deletePipeline(b.dataset.deletePipeline)));

    // Workers
    els.view.querySelectorAll('[data-open-worker]').forEach((b) => b.addEventListener('click', () => { store.set('selectedWorkerId', b.dataset.openWorker); store.set('workerTab', 'overview'); render(); }));
    els.view.querySelector('[data-action="back-workers"]')?.addEventListener('click', () => { store.set('selectedWorkerId', null); render(); });
    els.view.querySelectorAll('[data-toggle-worker]').forEach((b) => b.addEventListener('click', () => toggleWorker(b.dataset.toggleWorker)));
    els.view.querySelectorAll('[data-delete-worker]').forEach((b) => b.addEventListener('click', () => deleteWorker(b.dataset.deleteWorker)));
    els.view.querySelectorAll('[data-worker-tab]').forEach((b) => b.addEventListener('click', () => { store.set('workerTab', b.dataset.workerTab); render(); }));
    els.view.querySelector('[data-action="create-worker"]')?.addEventListener('click', openCreateWorkerModal);
    els.view.querySelectorAll('[data-action="post-now"]').forEach((b) => b.addEventListener('click', () => triggerPostNow(b.dataset.workerId)));
    els.view.querySelectorAll('[data-action="test-worker"]').forEach((b) => b.addEventListener('click', () => testWorker(b.dataset.workerId)));
    els.view.querySelectorAll('[data-action="edit-worker"]').forEach((b) => b.addEventListener('click', () => openEditWorkerModal(b.dataset.workerId)));
    els.view.querySelectorAll('[data-action="save-worker-schedule"]').forEach((b) => b.addEventListener('click', () => saveWorkerSchedule(b.dataset.workerId)));
    els.view.querySelectorAll('[data-action="save-worker-caption"]').forEach((b) => b.addEventListener('click', () => saveWorkerCaption(b.dataset.workerId)));
    els.view.querySelectorAll('[data-attach-pipeline]').forEach((b) => b.addEventListener('click', () => attachPipelineWorker(b.dataset.attachPipeline)));
    els.view.querySelectorAll('[data-detach-pipeline]').forEach((b) => b.addEventListener('click', () => detachPipelineWorker(b.dataset.detachPipeline)));

    // Pipeline worker attach/detach from pipeline view
    els.view.querySelectorAll('[data-attach-worker]').forEach((b) => b.addEventListener('click', () => attachWorker(b.dataset.attachWorker)));
    els.view.querySelectorAll('[data-detach-worker]').forEach((b) => b.addEventListener('click', () => detachWorker(b.dataset.detachWorker)));

    // Actions
    els.topbarActions.querySelector('[data-action="render-next"]')?.addEventListener('click', triggerRender);
    els.view.querySelectorAll('[data-action="render-next"]').forEach((b) => b.addEventListener('click', triggerRender));
    els.view.querySelector('[data-action="fetch"]')?.addEventListener('click', triggerFetch);
    els.view.querySelector('[data-action="approve"]')?.addEventListener('click', bulkApprove);
    els.view.querySelector('[data-action="reject"]')?.addEventListener('click', bulkReject);
    els.view.querySelector('[data-action="select-all"]')?.addEventListener('click', selectAllIngredients);
    els.view.querySelector('[data-action="clear-selection"]')?.addEventListener('click', clearIngredients);
    els.view.querySelector('[data-action="save-pipeline"]')?.addEventListener('click', savePipeline);
    els.view.querySelectorAll('[data-save-setting]').forEach((b) => b.addEventListener('click', () => saveSetting(b.dataset.saveSetting)));

    // Filters
    els.view.querySelectorAll('select[data-filter]').forEach((el) => el.addEventListener('change', (e) => {
        const key = e.target.dataset.filter;
        if (['platform', 'status', 'pipeline_id'].includes(key)) {
            const f = { ...store.get('postFilters'), [key]: e.target.value };
            store.set('postFilters', f);
            loadPosts().then(render);
        } else {
            const f = { ...store.get('filters'), [key]: e.target.value };
            store.set('filters', f);
            render();
        }
    }));

    // Ingredient selection
    els.view.querySelectorAll('[data-select-ingredient]').forEach((el) => el.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleIngredient(el.value, el.checked);
    }));
    els.view.querySelectorAll('[data-ingredient-card]').forEach((el) => el.addEventListener('click', (e) => {
        if (e.target.closest('button, input, label')) return;
        const cb = el.querySelector('input[type="checkbox"]');
        if (cb) { cb.checked = !cb.checked; toggleIngredient(el.dataset.ingredientCard, cb.checked); }
    }));
    els.view.querySelectorAll('[data-preview-ingredient]').forEach((b) => b.addEventListener('click', (e) => {
        e.stopPropagation();
        previewIngredient(b.dataset.previewIngredient);
    }));
    els.view.querySelectorAll('[data-preview-production]').forEach((b) => b.addEventListener('click', () => previewProduction(b.dataset.previewProduction)));
    els.view.querySelectorAll('[data-post-production]').forEach((b) => b.addEventListener('click', () => postProductionItem(b.dataset.postProduction)));
    els.view.querySelectorAll('[data-identify-production]').forEach((b) => b.addEventListener('click', () => openIdentifyModal(b.dataset.identifyProduction)));
    els.view.querySelectorAll('[data-redo-ai]').forEach((b) => b.addEventListener('click', () => redoAi(b.dataset.redoAi)));

    // Posts
    els.view.querySelectorAll('[data-post-id]').forEach((row) => row.addEventListener('click', () => openPostDetail(row.dataset.postId)));
    els.view.querySelector('[data-action="export-posts"]')?.addEventListener('click', exportPosts);
}

function setView(view) {
    store.set('view', view);
    els.body.classList.remove('nav-open');
    render();
}

// ── Pipeline Actions ───────────────────────────────────────────────────────
async function togglePipeline(id) {
    const p = store.get('pipelines').find((x) => x.id === id);
    if (!p) return;
    await api(`/api/pipelines/${id}`, { method: 'PUT', body: JSON.stringify({ enabled: !p.enabled }) });
    toast(!p.enabled ? 'Pipeline resumed.' : 'Pipeline paused.', 'success');
    await refreshAll();
}

async function deletePipeline(id) {
    const p = store.get('pipelines').find((x) => x.id === id);
    if (!p || !confirm(`Delete ${p.name}?`)) return;
    await api(`/api/pipelines/${id}`, { method: 'DELETE' });
    if (store.get('selectedPipelineId') === id) store.set('selectedPipelineId', null);
    await refreshAll();
}

async function savePipeline() {
    const id = store.get('selectedPipelineId');
    if (!id) return;
    const name = document.getElementById('pipeline-name')?.value;
    const enabled = document.getElementById('pipeline-enabled')?.checked;
    await api(`/api/pipelines/${id}`, { method: 'PUT', body: JSON.stringify({ name, enabled }) });
    toast('Pipeline saved.', 'success');
    await refreshAll();
}

function openCreatePipelineModal() {
    openModal({ title: 'Create Pipeline', eyebrow: 'New automation stream', body: pipelineModal(store.get('plugins')) });
    document.getElementById('pipeline-form').addEventListener('submit', submitPipeline);
}

async function submitPipeline(event) {
    event.preventDefault();
    const fd = new FormData(event.target);
    const payload = {
        name: String(fd.get('name')).trim(),
        plugin_id: fd.get('plugin_id'),
        enabled: true,
        config: {},
    };
    await api('/api/pipelines', { method: 'POST', body: JSON.stringify(payload) });
    toast('Pipeline created.', 'success');
    closeModal();
    await refreshAll();
}

async function triggerFetch() {
    const id = store.get('selectedPipelineId');
    if (!id) return;
    startOperation('fetch', id, 'Fetching ingredients', ['Downloading clips and backgrounds']);
    try {
        await api(`/api/pipelines/${id}/trigger`, { method: 'POST', body: JSON.stringify({ action: 'fetch' }) });
        finishOperation('Fetch completed.', 'success');
    } catch (e) { finishOperation(e.message, 'error'); }
}

async function triggerRender() {
    const id = store.get('selectedPipelineId');
    if (!id) return;
    startOperation('render', id, 'Rendering video', ['Running FFmpeg composition']);
    try {
        await api(`/api/pipelines/${id}/trigger`, { method: 'POST', body: JSON.stringify({ action: 'render' }) });
        finishOperation('Render completed.', 'success');
    } catch (e) { finishOperation(e.message, 'error'); }
}

// ── Ingredient Actions ─────────────────────────────────────────────────────
function toggleIngredient(id, checked) {
    const set = new Set(store.get('selectedIngredients'));
    if (checked) set.add(id); else set.delete(id);
    store.set('selectedIngredients', set);
    render();
}

function selectAllIngredients() {
    const data = store.get('pipelineData')[store.get('selectedPipelineId')] || {};
    const visible = (data.ingredients || []).filter((i) => {
        const f = store.get('filters');
        return (!f.ingredientType || i.type === f.ingredientType) && (!f.ingredientStatus || i.status === f.ingredientStatus);
    });
    store.set('selectedIngredients', new Set(visible.map((i) => i.id)));
    render();
}

function clearIngredients() {
    store.set('selectedIngredients', new Set());
    render();
}

async function bulkApprove() {
    await bulkIngredientAction('approve', 'Approved');
}
async function bulkReject() {
    await bulkIngredientAction('reject', 'Rejected');
}
async function bulkIngredientAction(action, label) {
    const id = store.get('selectedPipelineId');
    const ids = [...store.get('selectedIngredients')];
    if (!id || !ids.length) return;
    await api(`/api/pipelines/${id}/ingredients/${action}`, { method: 'POST', body: JSON.stringify({ ingredient_ids: ids }) });
    toast(`${label} ${ids.length} ingredients.`, 'success');
    store.set('selectedIngredients', new Set());
    await loadAllPipelineData();
    render();
}

function previewIngredient(id) {
    const data = store.get('pipelineData')[store.get('selectedPipelineId')] || {};
    const item = (data.ingredients || []).find((i) => i.id === id);
    if (!item) return;
    const src = `/api/pipelines/${item.pipeline_id}/ingredients/${item.id}/preview`;
    openModal({ title: item.type, body: item.file_path?.match(/\.(mp4|mov|webm)$/i) ? `<video src="${src}" controls autoplay playsinline></video>` : `<img src="${src}" alt="">` });
}

// ── Production Actions ─────────────────────────────────────────────────────
function previewProduction(id) {
    const data = store.get('pipelineData')[store.get('selectedPipelineId')] || {};
    const item = (data.production || []).find((p) => p.id === id);
    if (!item) return;
    openModal({ title: 'Preview', body: `<video src="/api/pipelines/${item.pipeline_id}/production/${item.id}/stream" controls autoplay playsinline></video>` });
}

function openIdentifyModal(id) {
    const data = store.get('pipelineData')[store.get('selectedPipelineId')] || {};
    const item = (data.production || []).find((p) => p.id === id);
    if (!item) return;
    const meta = item.content_meta || {};
    openModal({
        title: 'Assign Verse', eyebrow: 'Manual Review',
        body: `<form class="form-stack" id="identify-form">
            <label><span>Surah</span><input name="surah" type="number" min="1" max="114" value="${meta.surah || ''}" required></label>
            <label><span>Ayah</span><input name="ayah" type="number" min="1" value="${meta.ayah || ''}" required></label>
            <label><span>End ayah</span><input name="ayah_end" type="number" min="1" value="${meta.ayah_end || ''}" placeholder="Optional"></label>
            <button class="button primary" type="submit">Mark Ready</button>
        </form>`,
    });
    document.getElementById('identify-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const payload = { surah: Number(fd.get('surah')), ayah: Number(fd.get('ayah')), identified_by: 'manual', manual_override: true };
        const end = Number(fd.get('ayah_end'));
        if (end > payload.ayah) payload.ayah_end = end;
        await api(`/api/pipelines/${store.get('selectedPipelineId')}/production/${id}/identify`, { method: 'POST', body: JSON.stringify(payload) });
        closeModal();
        await loadAllPipelineData();
        render();
    });
}

async function redoAi(id) {
    const pid = store.get('selectedPipelineId');
    if (!pid) return;
    startOperation('identify', pid, 'Re-running AI detection', []);
    try {
        await api(`/api/pipelines/${pid}/production/${id}/redo-ai`, { method: 'POST' });
        finishOperation('AI detection complete.', 'success');
    } catch (e) { finishOperation(e.message, 'error'); }
}

// ── Worker Actions ─────────────────────────────────────────────────────────
async function toggleWorker(id) {
    const w = store.get('workers').find((x) => x.id === id);
    if (!w) return;
    await api(`/api/workers/${id}`, { method: 'PUT', body: JSON.stringify({ enabled: !w.enabled }) });
    toast(!w.enabled ? 'Worker resumed.' : 'Worker paused.', 'success');
    await refreshAll();
}

async function deleteWorker(id) {
    const w = store.get('workers').find((x) => x.id === id);
    if (!w || !confirm(`Delete ${w.display_name}?`)) return;
    await api(`/api/workers/${id}`, { method: 'DELETE' });
    if (store.get('selectedWorkerId') === id) store.set('selectedWorkerId', null);
    await refreshAll();
}

async function attachWorker(pipelineId) {
    const w = store.get('selectedWorkerId');
    if (!w) return;
    await api(`/api/pipelines/${pipelineId}/workers`, { method: 'POST', body: JSON.stringify({ worker_id: w }) });
    toast('Worker attached.', 'success');
    await refreshAll();
}

async function detachWorker(pipelineId) {
    const w = store.get('selectedWorkerId');
    if (!w) return;
    await api(`/api/pipelines/${pipelineId}/workers/${w}`, { method: 'DELETE' });
    toast('Worker detached.', 'success');
    await refreshAll();
}

async function attachPipelineWorker(workerId) {
    const pid = store.get('selectedPipelineId');
    if (!pid) return;
    await api(`/api/pipelines/${pid}/workers`, { method: 'POST', body: JSON.stringify({ worker_id: workerId }) });
    toast('Worker attached.', 'success');
    await refreshAll();
}

async function detachPipelineWorker(workerId) {
    const pid = store.get('selectedPipelineId');
    if (!pid) return;
    await api(`/api/pipelines/${pid}/workers/${workerId}`, { method: 'DELETE' });
    toast('Worker detached.', 'success');
    await refreshAll();
}

async function triggerPostNow(workerId) {
    if (!workerId) return;
    const w = store.get('workers').find((x) => x.id === workerId);
    startOperation('post', null, `Posting to ${w?.display_name || 'worker'}`, ['Uploading to platform']);
    try {
        const result = await api(`/api/workers/${workerId}/post`, { method: 'POST' });
        finishOperation(result.url ? `Posted: ${result.url}` : 'Post completed.', 'success');
    } catch (e) { finishOperation(e.message, 'error'); }
}

async function postProductionItem(contentId) {
    const pid = store.get('selectedPipelineId');
    if (!pid) return;
    const data = store.get('pipelineData')[pid] || {};
    const workers = data.workers || [];
    if (!workers.length) { toast('No workers attached to this pipeline.', 'error'); return; }
    const enabledWorker = workers.find((w) => w.enabled);
    if (!enabledWorker) { toast('No enabled workers attached.', 'error'); return; }
    await triggerPostNow(enabledWorker.id);
}

async function testWorker(workerId) {
    try {
        const result = await api(`/api/workers/${workerId}/test`, { method: 'POST' });
        toast(result.message || (result.ok ? 'Credentials valid.' : 'Credentials invalid.'), result.ok ? 'success' : 'error', 0);
    } catch (e) { toast(e.message, 'error', 0); }
}

async function saveWorkerSchedule(workerId) {
    const cron = document.getElementById('worker-cron')?.value || null;
    await api(`/api/workers/${workerId}`, { method: 'PUT', body: JSON.stringify({ schedule_cron: cron }) });
    toast('Schedule saved.', 'success');
    await refreshAll();
}

async function saveWorkerCaption(workerId) {
    const caption = document.getElementById('worker-caption')?.value || null;
    const hashtags = document.getElementById('worker-hashtags')?.value.split(',').map((s) => s.trim()).filter(Boolean) || [];
    await api(`/api/workers/${workerId}`, { method: 'PUT', body: JSON.stringify({ caption_template_override: caption, hashtags }) });
    toast('Caption saved.', 'success');
    await refreshAll();
}

function openCreateWorkerModal() {
    openModal({ title: 'Connect Worker', eyebrow: 'Platform Publisher', body: workerModal() });
    const plat = document.getElementById('w-platform');
    const strat = document.getElementById('w-strategy');
    const refresh = () => refreshCredentialFields(plat.value, strat.value);
    plat.addEventListener('change', refresh);
    strat.addEventListener('change', refresh);
    refresh();
    document.getElementById('worker-form').addEventListener('submit', submitWorker);
}

function openEditWorkerModal(workerId) {
    const w = store.get('workers').find((x) => x.id === workerId);
    if (!w) return;
    openModal({ title: 'Edit Worker', eyebrow: w.display_name, body: workerModal(w) });
    refreshCredentialFields(w.platform, w.connection_strategy, w.credentials);
    document.getElementById('worker-form').addEventListener('submit', (e) => submitWorker(e, workerId));
}

async function submitWorker(event, workerId = null) {
    event.preventDefault();
    const fd = new FormData(event.target);
    const credentials = {};
    let hasCreds = false;
    for (const [k, v] of fd.entries()) {
        if (k.startsWith('cred_')) {
            const val = String(v).trim();
            credentials[k.slice(5)] = val;
            if (val) hasCreds = true;
        }
    }
    const payload = {
        platform: fd.get('platform'),
        display_name: String(fd.get('display_name')).trim(),
        connection_strategy: fd.get('connection_strategy'),
        schedule_cron: fd.get('schedule_cron') || null,
        hashtags: [],
        enabled: true,
    };
    // Only send credentials on create or if user filled them in on edit
    if (!workerId || hasCreds) {
        payload.credentials = credentials;
    }
    if (payload.connection_strategy === 'third_party') {
        payload.third_party_provider = fd.get('third_party_provider');
    }
    if (workerId) {
        await api(`/api/workers/${workerId}`, { method: 'PUT', body: JSON.stringify(payload) });
        toast('Worker updated.', 'success');
    } else {
        await api('/api/workers', { method: 'POST', body: JSON.stringify(payload) });
        toast('Worker created.', 'success');
    }
    closeModal();
    await refreshAll();
}

// ── Settings ───────────────────────────────────────────────────────────────
async function saveSetting(key) {
    const el = document.querySelector(`[data-setting="${key}"]`);
    if (!el) return;
    const value = el.type === 'checkbox' ? el.checked : (el.type === 'number' ? Number(el.value) : el.value);
    await api(`/api/system/settings/${encodeURIComponent(key)}`, { method: 'PUT', body: JSON.stringify({ value }) });
    toast('Setting saved.', 'success');
    await loadSettings();
    render();
}

// ── Posts ──────────────────────────────────────────────────────────────────
function openPostDetail(postId) {
    const post = store.get('posts').find((p) => p.id === postId);
    if (!post) return;
    openModal({
        title: post.verse_label || 'Post Detail',
        eyebrow: `${platformLabel(post.platform)} — ${post.status}`,
        body: `
            <div class="form-stack">
                <p><strong>Pipeline:</strong> ${escapeHtml(post.pipeline_name || '-')}</p>
                <p><strong>Worker:</strong> ${escapeHtml(post.worker_name || post.worker_id || '-')}</p>
                <p><strong>Posted:</strong> ${formatDate(post.published_at || post.created_at)}</p>
                <p><strong>Attempts:</strong> ${post.attempt_count || 0}</p>
                ${post.platform_url ? `<p><a href="${escapeAttr(post.platform_url)}" target="_blank">Open on platform ↗</a></p>` : ''}
                ${post.caption_used ? `<div class="code-panel"><span>Caption used</span><pre>${escapeHtml(post.caption_used)}</pre></div>` : ''}
                ${post.error_log ? `<div class="code-panel"><span>Error log</span><pre style="color:var(--color-danger)">${escapeHtml(post.error_log)}</pre></div>` : ''}
            </div>`,
    });
}

function exportPosts() {
    const posts = store.get('posts');
    if (!posts.length) { toast('No posts to export.', 'error'); return; }
    const rows = posts.map((p) => [
        p.id, p.status, p.platform, p.worker_name, p.pipeline_name, p.verse_label,
        `"${(p.caption_used || '').replace(/"/g, '""')}"`, p.platform_url || '', p.published_at || p.created_at,
    ].join(','));
    const csv = 'ID,Status,Platform,Worker,Pipeline,Verse,Caption,URL,Date\n' + rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `flux-posts-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

// ── Operation Lifecycle ────────────────────────────────────────────────────
function startOperation(type, pipelineId, label, steps) {
    if (store.get('operation')) return;
    const op = { type, pipelineId, label, steps, startedAt: Date.now(), elapsed: 0 };
    store.set('operation', op);
    toast(`${label} started.`, 'success');
    const timer = setInterval(() => { op.elapsed = Math.floor((Date.now() - op.startedAt) / 1000); render(); }, 1000);
    const poller = setInterval(async () => { try { await loadActivity(); render(); } catch {} }, 5000);
    store.set('operationTimer', timer);
    store.set('operationPoller', poller);
    render();
}

function finishOperation(message, type) {
    clearInterval(store.get('operationTimer'));
    clearInterval(store.get('operationPoller'));
    store.set('operationTimer', null);
    store.set('operationPoller', null);
    store.set('operation', null);
    toast(message, type);
    refreshAll();
}
