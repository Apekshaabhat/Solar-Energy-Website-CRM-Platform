const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const TOKEN_KEY = "solara_token";
const USER_KEY = "solara_user";
const REMEMBER_KEY = "solara_remember";

let isRedirectingToLogin = false;

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token, rememberMe = false) {
  if (token) {
    if (rememberMe) {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(REMEMBER_KEY, "true");
      sessionStorage.removeItem(TOKEN_KEY);
    } else {
      sessionStorage.setItem(TOKEN_KEY, token);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REMEMBER_KEY);
    }
  } else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REMEMBER_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

export function getStoredUser() {
  const user = localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY);
  try {
    return user ? JSON.parse(user) : null;
  } catch (e) {
    return null;
  }
}

export function setStoredUser(user) {
  if (user) {
    const isRemembered = localStorage.getItem(REMEMBER_KEY) === "true";
    if (isRemembered) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      sessionStorage.removeItem(USER_KEY);
    } else {
      sessionStorage.setItem(USER_KEY, JSON.stringify(user));
      localStorage.removeItem(USER_KEY);
    }
  } else {
    localStorage.removeItem(USER_KEY);
    sessionStorage.removeItem(USER_KEY);
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REMEMBER_KEY);
  localStorage.removeItem(USER_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
  window.dispatchEvent(new Event("solara_auth_logout"));
}

function handleSessionExpired() {
  clearAuth();
  if (!isRedirectingToLogin) {
    isRedirectingToLogin = true;
    sessionStorage.setItem("auth_redirect_message", "Your session has expired, please sign in again.");
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    setTimeout(() => {
      isRedirectingToLogin = false;
    }, 2000);
  }
}

function parseErrorMessage(data, statusText) {
  if (!data) return statusText || "An unexpected error occurred.";

  if (data.message) return data.message;

  if (typeof data.detail === "string") return data.detail;

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((err) => {
        const field = Array.isArray(err.loc) ? err.loc.slice(1).join(".") : "";
        return field ? `${field}: ${err.msg}` : err.msg;
      })
      .join("; ");
  }

  if (typeof data.details === "string") return data.details;

  return statusText || "An unexpected error occurred.";
}

export async function apiClient(endpoint, options = {}) {
  const { body, headers = {}, method = "GET", isBlob = false, ...customConfig } = options;

  const token = getToken();

  const reqHeaders = {
    ...headers,
  };

  if (token) {
    reqHeaders["Authorization"] = `Bearer ${token}`;
  }

  let reqBody = body;
  if (body && typeof body === "object" && !(body instanceof FormData)) {
    reqHeaders["Content-Type"] = "application/json";
    reqBody = JSON.stringify(body);
  }

  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = `${BASE_URL}${cleanEndpoint}`;
  const isLoginRequest = cleanEndpoint === "/auth/login";

  const config = {
    method,
    headers: reqHeaders,
    body: reqBody,
    ...customConfig,
  };

  let response;
  try {
    response = await fetch(url, config);
  } catch (err) {
    const error = new Error("Unable to connect to backend server. Please check your network connection.");
    error.status = 0;
    throw error;
  }

  if (response.status === 401 && !isLoginRequest) {
    handleSessionExpired();
    const err = new Error("Your session has expired, please sign in again.");
    err.status = 401;
    throw err;
  }

  if (isBlob) {
    if (!response.ok) {
      const errorText = await response.text();
      let parsed;
      try {
        parsed = JSON.parse(errorText);
      } catch (e) {
        parsed = null;
      }
      throw new Error(parseErrorMessage(parsed, response.statusText));
    }
    return await response.blob();
  }

  let data = null;
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    try {
      data = await response.json();
    } catch (e) {
      data = null;
    }
  }

  if (!response.ok) {
    const errorMsg = parseErrorMessage(data, response.statusText);
    const err = new Error(errorMsg);
    err.status = response.status;
    err.data = data;
    throw err;
  }

  if (data && typeof data === "object") {
    // If it's a paginated envelope
    if (data.items !== undefined && data.meta !== undefined) {
      return data;
    }
    // If it's an APIResponse envelope with data field
    if (data.data !== undefined) {
      return data.data;
    }
  }

  return data;
}

export default apiClient;
