const STYLES = {
  error: "border-rose-500/40 bg-rose-500/10 text-rose-200",
  warning: "border-amber-500/40 bg-amber-500/10 text-amber-200",
  info: "border-sky-500/40 bg-sky-500/10 text-sky-200",
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
};

/** Inline, dismissible message — used where a modal would interrupt the flow. */
const Alert = ({ kind = "error", title, children, onClose }) => (
  <div className={`mb-6 rounded-xl border px-4 py-3 text-sm ${STYLES[kind]}`}>
    <div className="flex items-start justify-between gap-4">
      <div>
        {title && <p className="mb-1 font-semibold">{title}</p>}
        <div className="leading-relaxed">{children}</div>
      </div>
      {onClose && (
        <button onClick={onClose} className="shrink-0 text-lg leading-none opacity-60 hover:opacity-100">
          ×
        </button>
      )}
    </div>
  </div>
);

export default Alert;
