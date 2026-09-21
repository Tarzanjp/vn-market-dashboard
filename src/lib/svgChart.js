/**
 * src/lib/svgChart.js
 * Shared SVG chart primitive helpers used by engine modules.
 * All functions return SVG markup strings or path data strings.
 * No DOM access, no side-effects — pure string builders.
 */

const MONO = "IBM Plex Mono, ui-monospace, monospace";

/**
 * Build an SVG <path> d-attribute from an array of [x,y] or null points.
 * Null values create gaps (pen-up) in the line.
 */
export function buildPath(points) {
  return points
    .map((p, i) =>
      p == null
        ? null
        : (i === 0 || points[i - 1] == null ? "M" : "L") +
          p[0].toFixed(1) + " " + p[1].toFixed(1)
    )
    .filter(Boolean)
    .join(" ");
}

/**
 * Build horizontal grid lines + left-axis labels.
 * @param {number[]} values  - y-axis tick values
 * @param {function} Y       - value -> pixel y
 * @param {number}   xLeft   - left margin (start of line)
 * @param {number}   xRight  - right edge (end of line)
 * @param {number}   labelX  - x position of label text
 * @param {function} fmt     - value -> label string
 * @param {string}   [color] - override line color (default var(--line-soft))
 */
export function gridLines(values, Y, xLeft, xRight, labelX, fmt, color = "var(--line-soft)") {
  return values.map(v => {
    const y = Y(v).toFixed(1);
    return (
      `<line x1="${xLeft}" y1="${y}" x2="${xRight}" y2="${y}" stroke="${color}"/>` +
      `<text x="${labelX}" y="${(Y(v) + 4).toFixed(1)}" text-anchor="end" ` +
      `fill="var(--dim)" font-size="10" font-family="${MONO}">${fmt(v)}</text>`
    );
  }).join("");
}

/**
 * Build vertical grid lines + bottom-axis date labels.
 * @param {string[]} dates   - ISO date strings
 * @param {number[]} indices - which indices to label
 * @param {function} X       - index -> pixel x
 * @param {number}   yTop    - top of chart area
 * @param {number}   yBot    - bottom of chart area
 * @param {number}   labelY  - y position of label text
 * @param {function} fmt     - date string -> label string
 */
export function verticalGridLines(dates, indices, X, yTop, yBot, labelY, fmt) {
  return indices.map(i => {
    const x = X(i).toFixed(1);
    return (
      `<line x1="${x}" y1="${yTop}" x2="${x}" y2="${yBot}" stroke="var(--line-soft)" opacity=".55"/>` +
      `<text x="${x}" y="${labelY}" text-anchor="middle" ` +
      `fill="var(--dim)" font-size="10" font-family="${MONO}">${fmt(dates[i])}</text>`
    );
  }).join("");
}

/**
 * Build a filled area path under a line (for area charts).
 * @param {string} linePath  - the line path d-attribute
 * @param {number} x0        - x of first point
 * @param {number} x1        - x of last point
 * @param {number} yBase     - y of baseline (bottom of area)
 */
export function areaPath(linePath, x0, x1, yBase) {
  return `${linePath} L ${x1.toFixed(1)} ${yBase} L ${x0.toFixed(1)} ${yBase} Z`;
}

/**
 * Build a crosshair group (vertical line + optional circle).
 * @param {string} id    - SVG group id
 * @param {number} yTop  - top of chart area
 * @param {number} yBot  - bottom of chart area
 */
export function crosshair(id, yTop, yBot) {
  return (
    `<g id="${id}" style="opacity:0">` +
    `<line y1="${yTop}" y2="${yBot}" stroke="var(--text)" stroke-width="1" stroke-dasharray="3 3" opacity=".35"/>` +
    `<circle r="4.5" fill="var(--surface)" stroke="var(--blue)" stroke-width="2.2"/>` +
    `</g>`
  );
}
