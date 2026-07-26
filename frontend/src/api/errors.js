/**
 * One place that turns any axios failure into a message a human can act on.
 *
 * The backend answers with {description} or {ERRORS:[...]}; network failures,
 * Render cold starts and rate limits have no body at all, so those are mapped
 * by status code instead of showing "Request failed with status code 500".
 */
import Swal from "sweetalert2";

const BY_STATUS = {
  400: "That request was invalid — check the highlighted fields.",
  401: "Your session expired. Please sign in again.",
  403: "You don't have access to that. Sign in with a client account.",
  404: "Not found.",
  413: "That file is too large.",
  422: "The AI agent couldn't produce a valid result. Try rewording the prompt.",
  429: "Rate limit reached — wait about a minute and try again.",
  500: "Something went wrong on the server.",
  502: "The AI provider is unavailable right now.",
  503: "Service is starting up (free tier sleeps when idle). Retry in ~30 seconds.",
  504: "The server took too long to respond. Try again.",
};

export function errorMessage(err, fallback = "Something went wrong.") {
  if (err?.code === "ERR_NETWORK" || !err?.response) {
    return "Can't reach the server. It may be waking from sleep — retry in ~30 seconds.";
  }
  const { status, data } = err.response;
  if (data?.description) return data.description;
  if (data?.error) return data.error;
  if (Array.isArray(data?.ERRORS) && data.ERRORS.length) {
    return data.ERRORS.slice(0, 3).join(" · ");
  }
  return BY_STATUS[status] || fallback;
}

const swalCfg = { background: "#0f172a", color: "#e2e8f0", confirmButtonColor: "#f59e0b" };

export function showError(err, title = "Something went wrong") {
  Swal.fire({ icon: "error", title, text: errorMessage(err), ...swalCfg });
}

export function showSuccess(title, text) {
  Swal.fire({ icon: "success", title, text, ...swalCfg });
}
