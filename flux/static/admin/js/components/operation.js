/** Flux Admin — Operation Progress Bar */

import { formatDuration } from '../utils.js';

export function renderOperation(op, latestActivity) {
    if (!op) return '';
    const isRelevant = latestActivity && new Date(latestActivity.timestamp).getTime() >= op.startedAt - 5000;
    return `
        <section class="operation-bar">
            <div class="spinner mini" aria-label="Operation in progress"></div>
            <div class="operation-info">
                <strong>${op.label}</strong>
                <span class="muted">(${op.pipelineName})</span>
                <span class="timer">${formatDuration(op.elapsed)}</span>
            </div>
            <div class="operation-status">${isRelevant ? latestActivity.message : 'Processing...'}</div>
        </section>`;
}
