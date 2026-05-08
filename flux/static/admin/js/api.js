/** Flux Admin — API Client */

export async function api(path, options = {}) {
    const response = await fetch(path, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || payload.error?.message || `HTTP ${response.status}`);
    }
    if (response.status === 204) return null;
    return response.json();
}

export async function optionalApi(path, fallback = null) {
    try {
        return { ok: true, data: await api(path) };
    } catch (_) {
        return { ok: false, data: fallback };
    }
}
