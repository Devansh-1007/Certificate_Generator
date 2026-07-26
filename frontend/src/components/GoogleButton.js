import { useEffect, useRef, useState } from "react";
import api from "../api/client";

/**
 * Google Identity Services button.
 *
 * GIS is loaded from Google's CDN on demand (no npm dependency) and returns an
 * ID token, which the backend verifies against Google's public keys before
 * trusting the email. The button renders only when the server reports that a
 * client id is configured, so a deployment without Google simply doesn't
 * advertise it.
 */
const SCRIPT_SRC = "https://accounts.google.com/gsi/client";

const loadGis = () =>
  new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve();
    const existing = document.querySelector(`script[src="${SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", reject);
      return;
    }
    const s = document.createElement("script");
    s.src = SCRIPT_SRC;
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Could not load Google sign-in."));
    document.head.appendChild(s);
  });

const GoogleButton = ({ orgName, onSuccess, onError, text = "signin_with" }) => {
  const holder = useRef(null);
  const [enabled, setEnabled] = useState(false);
  // Keep the latest orgName without re-initialising GIS on every keystroke.
  const orgRef = useRef(orgName);
  orgRef.current = orgName;

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const { data } = await api.get("/auth/config");
        if (cancelled || !data.GOOGLE_ENABLED || !data.GOOGLE_CLIENT_ID) return;
        await loadGis();
        if (cancelled || !holder.current) return;

        window.google.accounts.id.initialize({
          client_id: data.GOOGLE_CLIENT_ID,
          callback: async ({ credential }) => {
            try {
              const res = await api.post("/auth/google", {
                CREDENTIAL: credential,
                ORG_NAME: orgRef.current || undefined,
              });
              onSuccess?.(res.data);
            } catch (err) {
              onError?.(err);
            }
          },
        });
        window.google.accounts.id.renderButton(holder.current, {
          theme: "filled_black",
          size: "large",
          shape: "pill",
          width: 320,
          text,
        });
        setEnabled(true);
      } catch {
        // Google unavailable or not configured — the password form still works.
      }
    })();

    return () => { cancelled = true; };
  }, [onSuccess, onError, text]);

  if (!enabled) return null;
  return (
    <div className="mb-6">
      <div ref={holder} className="flex justify-center" />
      <div className="mt-6 flex items-center gap-3 text-xs uppercase tracking-wide text-slate-600">
        <span className="h-px flex-1 bg-slate-800" />
        or use email
        <span className="h-px flex-1 bg-slate-800" />
      </div>
    </div>
  );
};

export default GoogleButton;
