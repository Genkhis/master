export function authHeaders() {
    const t = localStorage.getItem('jwt');
    return t ? { Authorization: `Bearer ${t}` } : {};
}
