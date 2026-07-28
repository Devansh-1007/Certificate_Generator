import axios from "axios";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://localhost:5000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("cg_token");
  if (token) {
    config.headers["Authorization"] = "Bearer " + token;
    config.headers["x-token"] = token; // legacy header, still accepted
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    // A 401 while holding a token means the session is no longer valid — it
    // expired, the signing secret rotated, or it predates a schema change.
    // Record the reason so /login can explain the bounce instead of silently
    // dumping the user back at sign-in.
    if (err.response?.status === 401 && localStorage.getItem("cg_token")) {
      ["cg_token", "cg_user", "cg_org", "cg_client", "cg_role"].forEach((k) =>
        localStorage.removeItem(k)
      );
      sessionStorage.setItem(
        "cg_signout_reason",
        err.response?.data?.description || "Your session ended. Please sign in again."
      );
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export default api;
