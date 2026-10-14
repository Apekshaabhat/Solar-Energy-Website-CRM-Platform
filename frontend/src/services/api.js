const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export const AUTH_TOKEN_KEY = "solara-auth-token";
export const AUTH_USER_KEY = "solara-auth-user";

export class ApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function buildUrl(path, params) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${cleanPath}`);

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value);
    }
  });

  return url.toString();
}

export function getAuthToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function getStoredUser() {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(AUTH_USER_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setAuthSession(token, user) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

export function clearAuthSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  window.localStorage.removeItem(AUTH_USER_KEY);
}

export async function apiRequest(path, options = {}) {
  const {
    method = "GET",
    body,
    params,
    headers = {},
    auth = true,
    signal,
  } = options;

  const token = getAuthToken();
  const requestHeaders = {
    Accept: "application/json",
    ...headers,
  };

  if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
  }

  if (auth && token) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }

  const requestController = new AbortController();
  const timeoutId = setTimeout(() => requestController.abort(), 15000);
  if (signal) {
    signal.addEventListener("abort", () => requestController.abort(), { once: true });
  }

  let response;
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers: requestHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: requestController.signal,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new ApiError("The SOLARA API request timed out. Please check that the backend is running.", 408, error);
    }
    throw new ApiError("Unable to reach the SOLARA API", 0, error);
  } finally {
    clearTimeout(timeoutId);
  }

  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;

  if (!response.ok) {
    if (response.status === 401) {
      clearAuthSession();
    }
    throw new ApiError(
      payload?.message || payload?.detail || "API request failed",
      response.status,
      payload?.details || payload
    );
  }

  return payload;
}

export async function downloadRequest(path, params = {}) {
  const token = getAuthToken();
  const requestHeaders = { Accept: "text/csv" };
  if (token) requestHeaders.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(buildUrl(path, params), { headers: requestHeaders });
  } catch (error) {
    throw new ApiError("Unable to reach the SOLARA API", 0, error);
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    if (response.status === 401) clearAuthSession();
    throw new ApiError(payload?.message || payload?.detail || "File download failed", response.status, payload);
  }

  return response.blob();
}

export function unwrapData(response) {
  return response?.data ?? response;
}
