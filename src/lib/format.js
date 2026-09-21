/**
 * src/lib/format.js
 * Shared pure-function helpers for all engine modules.
 * No imports, no side-effects.
 */

/** Format number vi-VN locale, null/NaN -> em-dash */
export const nf = (v, d = 2) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
};

/** Signed format (+/-), null/NaN -> em-dash */
export const sgn = (v, d = 2) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return (n > 0 ? "+" : n < 0 ? "−" : "") + nf(Math.abs(n), d);
};

/** CSS direction class: "up" | "down" | "flat" */
export const cls = (v) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "flat";
  return v > 0 ? "up" : v < 0 ? "down" : "flat";
};

/** "YYYY-MM-DD" -> "MM/DD" (short) */
export const dmy = (iso) => (!iso ? "—" : String(iso).slice(5).replace("-", "/"));

/** "YYYY-MM-DD" -> "YYYY/MM/DD" (full) */
export const dmyF = (iso) => (!iso ? "—" : String(iso).replace(/-/g, "/"));

/** HTML-escape for safe innerHTML insertion */
export const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
