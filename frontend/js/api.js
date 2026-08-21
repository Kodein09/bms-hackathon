const BMS_API_URL = 'http://127.0.0.1:8000/api/v1';
const BMS_ACCESS_TOKEN_KEY = 'bms-access-token';
const BMS_REFRESH_TOKEN_KEY = 'bms-refresh-token';
const BMS_USER_KEY = 'bms-user';

function bmsAuthHeaders(extra = {}) {
  const token = localStorage.getItem(BMS_ACCESS_TOKEN_KEY);
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

async function bmsApi(path, options = {}) {
  const response = await fetch(`${BMS_API_URL}${path}`, {
    ...options,
    headers: bmsAuthHeaders(options.headers || {}),
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

async function bmsLogin(username, password) {
  const body = new URLSearchParams({ username, password });
  const tokens = await bmsApi('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  localStorage.setItem(BMS_ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(BMS_REFRESH_TOKEN_KEY, tokens.refresh_token);
  const user = await bmsApi('/auth/me');
  localStorage.setItem(BMS_USER_KEY, JSON.stringify(user));
  return user;
}

async function bmsRegister(username, email, password) {
  return bmsApi('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });
}

function bmsLogout() {
  [BMS_ACCESS_TOKEN_KEY, BMS_REFRESH_TOKEN_KEY, BMS_USER_KEY].forEach((key) => localStorage.removeItem(key));
}

function bmsUser() {
  try { return JSON.parse(localStorage.getItem(BMS_USER_KEY) || 'null'); } catch (_) { return null; }
}

function bmsWebSocket() {
  const user = bmsUser();
  const token = localStorage.getItem(BMS_ACCESS_TOKEN_KEY);
  if (!user || !token) return null;
  const socket = new WebSocket(`ws://127.0.0.1:8000/ws/notifications/${user.id}?token=${encodeURIComponent(token)}`);
  return socket;
}
