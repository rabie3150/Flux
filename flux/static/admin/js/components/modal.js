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
            <button class="icon-button" id="modal-close" title="Close">×</button></header>
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
