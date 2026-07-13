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
    if (err.response && err.response.status === 401 && localStorage.getItem("cg_token")) {
      localStorage.removeItem("cg_token");
      localStorage.removeItem("cg_client");
      localStorage.removeItem("cg_role");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;
