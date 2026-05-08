/** Flux Admin — Posts View */

import { escapeHtml, formatDate, statusLabel, platformLabel } from '../utils.js';

export function renderPosts(state) {
    const posts = state.posts || [];
    const filters = state.postFilters || {};
    const platforms = [...new Set((state.workers || []).map((w) => w.platform))];
    const pipelines = state.pipelines || [];

    return `
        <section class="page-grid">
            <section class="panel span-12">
                <div class="panel-head">
                    <p>History of all published content.</p>
                </div>
                <div class="toolbar">
                    <div class="filter-group" style="display:flex; gap:12px; flex-wrap:wrap;">
                        <select data-filter="platform">${option('', 'All Platforms', filters.platform)}${platforms.map((p) => option(p, platformLabel(p), filters.platform)).join('')}</select>
                        <select data-filter="status">${option('', 'All Statuses', filters.status)}${option('published', 'Published', filters.status)}${option('failed', 'Failed', filters.status)}${option('pending', 'Pending', filters.status)}</select>
                        <select data-filter="pipeline_id">${option('', 'All Pipelines', filters.pipeline_id)}${pipelines.map((p) => option(p.id, p.name, filters.pipeline_id)).join('')}</select>
                    </div>
                    <button class="button ghost" data-action="export-posts">Export CSV</button>
                </div>
                <div class="table-wrap">
                    <table><thead><tr><th>Title / Content</th><th>Platform</th><th>Worker</th><th>Posted</th><th>Status</th></tr></thead><tbody>
                        ${posts.length ? posts.map(postRow).join('') : `<tr><td colspan="5" style="border:none;"><div class="empty-state" style="text-align:center;">No posts yet.</div></td></tr>`}
                    </tbody></table>
                </div>
            </section>
        </section>`;
}

function postRow(post) {
    const status = post.status || 'unknown';
    const tone = status === 'published' ? 'ok' : status === 'failed' ? 'failed' : 'pending';
    return `<tr data-post-id="${post.id}">
        <td><strong>${escapeHtml(post.verse_label || '-')}</strong><small>${escapeHtml(post.pipeline_name ? ' · ' + post.pipeline_name : '')}</small></td>
        <td>${escapeHtml(platformLabel(post.platform))}</td>
        <td>${escapeHtml(post.worker_name || post.worker_id || '-')}</td>
        <td>${formatDate(post.published_at || post.created_at)}</td>
        <td>${statusPill(statusLabel(status), tone)}</td>
    </tr>`;
}

function option(value, label, selected) {
    return `<option value="${escapeHtml(value)}" ${value === selected ? 'selected' : ''}>${escapeHtml(label)}</option>`;
}

function emptyState(text) {
    return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function statusPill(label, status) {
    return `<span class="status-pill ${escapeHtml(status)}">${escapeHtml(label)}</span>`;
}
