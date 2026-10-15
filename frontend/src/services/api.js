const API_BASE = import.meta.env.VITE_API_URL || "";

export const getAuthToken = () => localStorage.getItem("envi_token");
export const setAuthToken = (token) => {
  if (token) localStorage.setItem("envi_token", token);
  else localStorage.removeItem("envi_token");
};

export const getStoredUser = () => {
  try {
    const u = localStorage.getItem("envi_user");
    return u ? JSON.parse(u) : null;
  } catch (e) {
    return null;
  }
};
export const setStoredUser = (user) => {
  if (user) localStorage.setItem("envi_user", JSON.stringify(user));
  else localStorage.removeItem("envi_user");
};

async function request(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    ...options.headers,
  };

  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // If body is not FormData, set Content-Type to application/json
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `Request failed (${response.status})`;
    try {
      const errorJson = await response.json();
      errorMessage = errorJson.detail || errorMessage;
    } catch (e) {
      // ignore
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export const api = {
  // Auth
  login: (email, password) =>
    request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (userData) =>
    request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(userData),
    }),
  getMe: () => request("/api/auth/me"),
  getDemoUsers: () => request("/api/auth/demo-users"),

  // Reports
  predictNLP: (text) =>
    request("/api/reports/ai-predict", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  createReport: (formData) =>
    request("/api/reports", {
      method: "POST",
      body: formData,
    }),
  getReports: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "" && v !== "all") {
        query.append(k, v);
      }
    });
    const qs = query.toString() ? `?${query.toString()}` : "";
    return request(`/api/reports${qs}`);
  },
  getReportById: (id) => request(`/api/reports/${id}`),
  updateStatus: (id, formData) =>
    request(`/api/reports/${id}/status`, {
      method: "PATCH",
      body: formData,
    }),
  submitFeedback: (id, feedback) =>
    request(`/api/reports/${id}/feedback`, {
      method: "POST",
      body: JSON.stringify(feedback),
    }),

  // Zones
  getZones: () => request("/api/zones"),
  getTrendingZones: () => request("/api/zones/trending"),

  // Analytics
  getAnalyticsKPIs: () => request("/api/analytics/kpis"),
  getAnalyticsCharts: () => request("/api/analytics/charts"),

  // Notifications
  getNotifications: () => request("/api/notifications"),
  markNotificationRead: (id) =>
    request(`/api/notifications/${id}/read`, { method: "PATCH" }),
  markAllNotificationsRead: () =>
    request("/api/notifications/mark-all-read", { method: "POST" }),

  // Admin
  getAuthorities: () => request("/api/admin/authorities"),
  createAuthority: (data) =>
    request("/api/admin/authorities", { method: "POST", body: JSON.stringify(data) }),
  getAdminZones: () => request("/api/admin/zones"),
  createZone: (data) =>
    request("/api/admin/zones", { method: "POST", body: JSON.stringify(data) }),
  getRoutingRules: () => request("/api/admin/routing-rules"),
  createRoutingRule: (data) =>
    request("/api/admin/routing-rules", { method: "POST", body: JSON.stringify(data) }),
  toggleRoutingRule: (id) =>
    request(`/api/admin/routing-rules/${id}/toggle`, { method: "PATCH" }),
  getUsers: () => request("/api/admin/users"),

  // EcoCredits, Green Civic Score & Government Volunteer Programs
  getEcoProfile: () => request("/api/eco/profile"),
  getVolunteerDrives: () => request("/api/eco/volunteer-drives"),
  enrollVolunteerDrive: (driveId) =>
    request(`/api/eco/volunteer-drives/${driveId}/enroll`, { method: "POST" }),
  getGreenPerks: () => request("/api/eco/perks"),
  redeemGreenPerk: (perkId) =>
    request(`/api/eco/perks/${perkId}/redeem`, { method: "POST" }),
  getEcoCertificate: () => request("/api/eco/certificate"),

  // Asset helper
  assetUrl: (path) => {
    if (!path) return `${API_BASE}/seed_assets/default_dumping.jpg`;
    if (path.startsWith("http")) return path;
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    return `${API_BASE}${cleanPath}`;
  }
};
