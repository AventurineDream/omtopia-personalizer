.pragma library

// Perimeter SVG path geometry for GlyphOverlay.qml.
// Ported from home/shell/frame/Geometry.js in NIHIL by Pol Iglesias (poligle),
// MIT License — https://github.com/poligle/Nihil-Shell. See NOTICE.

const K = 0.5523; // cubic Bezier constant for a quarter circle

function fmt(p) {
    return (Math.round(p[0] * 100) / 100) + " " + (Math.round(p[1] * 100) / 100);
}

function edges(W, H, L, T, R, B) {
    const x0 = L, y0 = T, x1 = W - R, y1 = H - B;
    return [
        { o: [x0, y0], d: [1, 0], n: [0, 1], len: x1 - x0 },
        { o: [x1, y0], d: [0, 1], n: [-1, 0], len: y1 - y0 },
        { o: [x1, y1], d: [-1, 0], n: [0, -1], len: x1 - x0 },
        { o: [x0, y1], d: [0, -1], n: [1, 0], len: y1 - y0 }
    ];
}

function at(e, s, n) {
    return [e.o[0] + e.d[0] * s + e.n[0] * n, e.o[1] + e.d[1] * s + e.n[1] * n];
}

function corner(a, v, b) {
    const c1 = [a[0] + K * (v[0] - a[0]), a[1] + K * (v[1] - a[1])];
    const c2 = [b[0] + K * (v[0] - b[0]), b[1] + K * (v[1] - b[1])];
    return " C" + fmt(c1) + " " + fmt(c2) + " " + fmt(b);
}

// Plain rounded inner outline (SVG path), walking clockwise from edge `start`
// (0 = top, 1 = right, 2 = bottom, 3 = left).
function outline(W, H, L, T, R, B, radius, start) {
    if (W <= 0 || H <= 0) return "";
    const es = edges(W, H, L, T, R, B);
    const first = start || 0;
    const r = Math.max(0, Math.min(radius, (W - L - R) / 2, (H - T - B) / 2));
    let p = "M" + fmt(at(es[first], r, 0));
    for (let k = 0; k < 4; k++) {
        const i = (first + k) % 4;
        const n = (i + 1) % 4;
        const e = es[i];
        p += " L" + fmt(at(e, e.len - r, 0));
        p += corner(at(e, e.len - r, 0), at(e, e.len, 0), at(es[n], r, 0));
    }
    return p + " Z";
}

function ringLength(W, H, L, T, R, B, radius) {
    const r = Math.max(0, Math.min(radius, (W - L - R) / 2, (H - T - B) / 2));
    return Math.max(1, 2 * ((W - L - R) + (H - T - B)) - 8 * r + 2 * Math.PI * r);
}

// Half of the inner outline: from bottom-center up one side (1 = right, -1 = left)
// to top-center. Dual charging beams climb both halves simultaneously.
function rise(W, H, L, T, R, B, radius, side) {
    if (W <= 0 || H <= 0) return "";
    const x0 = L, y0 = T, x1 = W - R, y1 = H - B;
    const r = Math.max(0, Math.min(radius, (x1 - x0) / 2, (y1 - y0) / 2));
    const cx = (x0 + x1) / 2;
    const x = side > 0 ? x1 : x0;
    const inward = side > 0 ? -r : r;
    let p = "M" + fmt([cx, y1]);
    p += " L" + fmt([x + inward, y1]);
    p += corner([x + inward, y1], [x, y1], [x, y1 - r]);
    p += " L" + fmt([x, y0 + r]);
    p += corner([x, y0 + r], [x, y0], [x + inward, y0]);
    p += " L" + fmt([cx, y0]);
    return p;
}
