/** Flux Admin — Modal System */

import { escapeHtml, escapeAttr } from '../utils.js';

let backdrop = null;
let panel = null;

function ensureModal() {
    if (backdrop) return;
    backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop hidden';
    backdrop.innerHTML = `
        <section class="modal-panel">
            <header><div><p class="eyebrow" id="modal-eyebrow"></p><h2 id="modal-title"></h2></div>
            <button class="icon-button ghost" id="modal-close" title="Close" style="border:none; padding:8px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button></header>
            <div class="modal-body" id="modal-body"></div>
        </section>`;
    document.body.appendChild(backdrop);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeModal(); });
    backdrop.querySelector('#modal-close').addEventListener('click', closeModal);
}

export function openModal({ title, eyebrow = '', body, onClose } = {}) {
    ensureModal();
    backdrop.querySelector('#modal-title').textContent = title || '';
    backdrop.querySelector('#modal-eyebrow').textContent = eyebrow;
    const bodyEl = backdrop.querySelector('#modal-body');
    if (typeof body === 'string') bodyEl.innerHTML = body;
    else { bodyEl.innerHTML = ''; bodyEl.appendChild(body); }
    backdrop.classList.remove('hidden');
    if (onClose) backdrop._onClose = onClose;
}

export function closeModal() {
    if (!backdrop) return;
    backdrop.classList.add('hidden');
    backdrop.querySelector('#modal-body').innerHTML = '';
    if (backdrop._onClose) { backdrop._onClose(); backdrop._onClose = null; }
}

export function modalBody() {
    ensureModal();
    return backdrop.querySelector('#modal-body');
}

export function isModalOpen() {
    return backdrop && !backdrop.classList.contains('hidden');
}
