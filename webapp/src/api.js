const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

// Token management
const TOKEN_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

function setTokens(accessToken, refreshToken) {
  localStorage.setItem(TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_KEY, refreshToken);
}

function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }

  const response = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  if (!response.ok) {
    clearTokens();
    throw new Error("Session expired. Please login again.");
  }

  const data = await response.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

async function request(path, options = {}) {
  // Add Authorization header if token exists
  const token = getAccessToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };

  if (token && !path.startsWith("/auth/")) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...options
  });

  // Handle 401 - try to refresh token once
  if (response.status === 401 && token && !options._retry) {
    try {
      const newToken = await refreshAccessToken();
      headers.Authorization = `Bearer ${newToken}`;

      // Retry the original request with new token
      response = await fetch(`${BASE_URL}${path}`, {
        headers,
        ...options,
        _retry: true
      });
    } catch (err) {
      clearTokens();
      throw new Error("Session expired. Please login again.");
    }
  }

  if (!response.ok) {
    const maybeJson = await response.text();
    let errorDetail = maybeJson;
    try {
      errorDetail = JSON.parse(maybeJson);
    } catch {
      // keep original text
    }
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(errorDetail)}`);
  }

  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  baseUrl: BASE_URL,

  // Authentication
  async login(username, password) {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Login failed: ${error}`);
    }

    const data = await response.json();
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  async register(username, email, password, fullName) {
    const response = await fetch(`${BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        email,
        password,
        full_name: fullName
      })
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Registration failed: ${error}`);
    }

    return response.json();
  },

  logout() {
    clearTokens();
  },

  isAuthenticated() {
    return !!getAccessToken();
  },

  async getCurrentUser() {
    return request("/auth/me");
  },

  // Schools
  listSchools: () => request("/schools"),
  createSchool: (payload) => request("/schools", { method: "POST", body: JSON.stringify(payload) }),

  // Students
  listStudents: () => request("/students"),
  createStudent: (payload) => request("/students", { method: "POST", body: JSON.stringify(payload) }),

  // Invoices
  listInvoices: () => request("/invoices"),
  createInvoice: (payload) => request("/invoices", { method: "POST", body: JSON.stringify(payload) }),

  // Payments
  listPayments: () => request("/payments"),
  createPayment: (payload) => request("/payments", { method: "POST", body: JSON.stringify(payload) }),

  // Account Status
  getSchoolAccountStatus: (schoolId) => request(`/schools/${schoolId}/account-status`),
  getStudentAccountStatus: (studentId) => request(`/students/${studentId}/account-status`)
};
