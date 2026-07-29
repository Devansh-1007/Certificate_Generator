import { useCallback, useEffect, useRef, useState } from "react";
import api from "../api/client";

/**
 * Google Identity Services button.
 *
 * GIS is loaded from Google's CDN on demand (no npm dependency) and returns an
 * ID token, which the backend verifies against Google's public keys before
 * trusting the email. The button renders only when the server reports that a
 * client id is configured, so a deployment without Google simply doesn't
 * advertise it.
 *
 * Two things this file gets deliberately right, because both bit us once:
 *
 * 1. The holder div is ALWAYS mounted (hidden while loading). GIS renders into
 *    a real DOM node, so if the component returned null until it was "ready",
 *    the ref would still be null at renderButton time and it could never
 *    become ready — a deadlock that looked exactly like "Google is disabled".
 * 2. Failures are reported, not swallowed. A misconfigured origin or client id
 *    fails inside Google's SDK; without a message the page just silently omits
 *    the button and there is nothing to debug.
 */
const SCRIPT_SRC = "https://accounts.google.com/gsi/client";

const loadGis = () =>
  new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve();
    const done = () =>
      window.google?.accounts?.id
        ? resolve()
        : reject(new Error("Google sign-in script loaded but did not initialise."));
    const existing = document.querySelector(`script[src="${SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", done);
      existing.addEventListener("error", () =>
        reject(new Error("Could not reach Google sign-in (blocked or offline)."))
      );
      return;
    }
    const s = document.createElement("script");
    s.src = SCRIPT_SRC;
    s.async = true;
    s.defer = true;
    s.onload = done;
    s.onerror = () =>
      reject(new Error("Could not reach Google sign-in (blocked or offline)."));
    document.head.appendChild(s);
  });

const GoogleButton = ({ orgName, onSuccess, onError, text = "signin_with" }) => {
  const holder = useRef(null);
  const [status, setStatus] = useState("loading"); // loading | ready | off | error
  const [problem, setProblem] = useState("");

  // Keep the latest props without re-initialising GIS on every parent render.
  const orgRef = useRef(orgName);
  const successRef = useRef(onSuccess);
  const errorRef = useRef(onError);
  orgRef.current = orgName;
  successRef.current = onSuccess;
  errorRef.current = onError;

  const start = useCallback(async () => {
    setStatus("loading");
    setProblem("");
    try {
      const { data } = await api.get("/auth/config");

      if (!data.GOOGLE_ENABLED || !data.GOOGLE_CLIENT_ID) {
        // Not an error: this deployment simply doesn't offer Google sign-in.
        if (data.GOOGLE_PROBLEM) console.warn("Google sign-in:", data.GOOGLE_PROBLEM);
        setStatus("off");
        return;
      }

      await loadGis();
      if (!holder.current) throw new Error("Sign-in container is not mounted.");

      window.google.accounts.id.initialize({
        client_id: data.GOOGLE_CLIENT_ID,
        callback: async ({ credential }) => {
          try {
            const res = await api.post("/auth/google", {
              CREDENTIAL: credential,
              ORG_NAME: orgRef.current || undefined,
            });
            successRef.current?.(res.data);
          } catch (err) {
            errorRef.current?.(err);
          }
        },
      });

      holder.current.innerHTML = "";
      window.google.accounts.id.renderButton(holder.current, {
        theme: "filled_black",
        size: "large",
        shape: "pill",
        width: 320,
        text,
      });
      setStatus("ready");
    } catch (err) {
      console.warn("Google sign-in unavailable:", err);
      setProblem(err?.message || "Google sign-in could not start.");
      setStatus("error");
    }
  }, [text]);

  useEffect(() => {
    start();
  }, [start]);

  // The deployment has no Google client id — show nothing at all.
  if (status === "off") return null;

  return (
    <div className="mb-6">
      {/* Always mounted so GIS has somewhere to render; hidden until it has. */}
      <div
        ref={holder}
        className={`flex justify-center ${status === "ready" ? "" : "hidden"}`}
      />

      {status === "loading" && (
        <p className="text-center text-xs text-slate-500">Loading Google sign-in…</p>
      )}

      {status === "error" && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-center text-xs text-amber-200">
          <p>{problem}</p>
          <button
            type="button"
            onClick={start}
            className="mt-2 underline underline-offset-2 hover:text-amber-100"
          >
            Try again
          </button>
        </div>
      )}

      <div className="mt-6 flex items-center gap-3 text-xs uppercase tracking-wide text-slate-600">
        <span className="h-px flex-1 bg-slate-800" />
        or use email
        <span className="h-px flex-1 bg-slate-800" />
      </div>
    </div>
  );
};

export default GoogleButton;
