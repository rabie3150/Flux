/** Flux Admin — Toast Notifications */

const stack = document.createElement('div');
stack.className = 'toast-stack';
stack.setAttribute('aria-live', 'polite');

document.addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(stack);
});

export function toast(message, type = 'success', duration = 4200) {
    const item = document.createElement('div');
    item.className = `toast ${type}`;
    item.textContent = message;
    stack.appendChild(item);
    if (duration > 0) {
        setTimeout(() => item.remove(), duration);
    }
    return item;
}

export function clearToasts() {
    stack.innerHTML = '';
}
