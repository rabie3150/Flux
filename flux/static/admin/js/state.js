/** Flux Admin — Tiny Reactive Store */

export function createStore(initial = {}) {
    const state = { ...initial };
    const subs = new Map();

    function get(key) {
        return key ? state[key] : { ...state };
    }

    function set(key, value) {
        const prev = state[key];
        if (Object.is(prev, value)) return;
        state[key] = value;
        const cbs = subs.get(key);
        if (cbs) cbs.forEach((cb) => cb(value, prev));
    }

    function batch(updates) {
        Object.entries(updates).forEach(([k, v]) => { state[k] = v; });
        const notified = new Set();
        Object.keys(updates).forEach((k) => {
            const cbs = subs.get(k);
            if (cbs) { cbs.forEach((cb) => notified.add(cb)); }
        });
        notified.forEach((cb) => cb(state));
    }

    function subscribe(key, cb) {
        if (!subs.has(key)) subs.set(key, new Set());
        subs.get(key).add(cb);
        return () => subs.get(key).delete(cb);
    }

    return { get, set, batch, subscribe };
}
