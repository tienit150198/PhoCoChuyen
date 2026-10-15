/* Layout checks for one screen, run in the page by scripts/browser_mobile_sweep.py (page.evaluate of this file's
 * text): returns {root, W, H, issues[]} with issues of type
 *   hscroll-page / hscroll-box  sideways scroll that is not a deliberate strip
 *   offscreen-x / clipped-x     a control past the viewport or cut by an overflow:hidden parent
 *   small-tap                   a control under 32 px on a side
 *   covered / covered-edge      another element on top of a control (≥ 3 / 1–2 of 9 sample points); a sticky bar
 *                               over content that scrolling brings out is not counted
 *   text-overlap                text of two unrelated elements painted over each other
 *   text-clipped                text cut by overflow without an ellipsis or line clamp
 * Dev tool only; not loaded by the game. */
(opts) => {
  opts = opts || {};
  const W = innerWidth, H = innerHeight, issues = [];
  const MINTAP = opts.minTap || 32;
  const shown = el => el.checkVisibility ? el.checkVisibility({opacityProperty: true, visibilityProperty: true, contentVisibilityAuto: true}) : true;
  const desc = el => {
    if (!el || el.nodeType !== 1) return String(el);
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    const cls = (typeof el.className === 'string' ? el.className : '').trim().split(/\s+/).filter(Boolean).slice(0, 3);
    if (cls.length) s += '.' + cls.join('.');
    for (const a of ['data-action', 'data-command', 'data-tab']) if (el.getAttribute(a)) s += `[${a}=${el.getAttribute(a)}]`;
    const t = (el.innerText || el.value || el.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim().slice(0, 40);
    if (t) s += ` "${t}"`;
    return s;
  };
  // Visible part of an element: viewport ∩ every clipping ancestor.
  const clipRect = el => {
    const r = el.getBoundingClientRect();
    let L = r.left, T = r.top, R = r.right, B = r.bottom, hx = false;
    for (let a = el.parentElement; a && a !== document.documentElement; a = a.parentElement) {
      const cs = getComputedStyle(a);
      const ox = cs.overflowX, oy = cs.overflowY;
      if (ox !== 'visible' || oy !== 'visible') {
        const ar = a.getBoundingClientRect();
        if (ox !== 'visible') { L = Math.max(L, ar.left); R = Math.min(R, ar.right); if ((ox === 'auto' || ox === 'scroll') && a.scrollWidth > a.clientWidth + 1) hx = true; }
        if (oy !== 'visible') { T = Math.max(T, ar.top); B = Math.min(B, ar.bottom); }
      }
      if (cs.position === 'fixed') break;
    }
    return {L, T, R, B, hx, r};
  };
  const vScroller = el => { for (let a = el.parentElement; a; a = a.parentElement) { const cs = getComputedStyle(a); if ((cs.overflowY === 'auto' || cs.overflowY === 'scroll') && a.scrollHeight > a.clientHeight + 2) return a; } return null; };
  // A sticky/fixed bar over content that scrolling can bring out from under it is normal scrolling, not an overlap.
  const revealable = (el, by) => {
    const S = vScroller(el); if (!S || !by) return false;
    if (S.contains(by)) { let st = false; for (let a = by; a && a !== S; a = a.parentElement) { const p = getComputedStyle(a).position; if (p === 'sticky' || p === 'fixed') { st = true; break; } } if (!st) return false; }
    const sr = S.getBoundingClientRect(), br = by.getBoundingClientRect();
    const upper = (br.top + br.bottom) / 2 < (sr.top + sr.bottom) / 2;
    return upper ? S.scrollTop > 1 : S.scrollTop < S.scrollHeight - S.clientHeight - 1;
  };
  const top = [...document.querySelectorAll('dialog[open]')].pop();
  const root = opts.root ? document.querySelector(opts.root) : (top || document.querySelector('#app'));
  const rootName = desc(root);
  // 1. horizontal scroll
  const se = document.scrollingElement;
  if (se.scrollWidth > W + 1) issues.push({t: 'hscroll-page', d: `page ${se.scrollWidth} > ${W}`});
  const scrollers = [root, ...root.querySelectorAll('*')].filter(e => { if (!shown(e)) return false; const cs = getComputedStyle(e); return (cs.overflowX === 'auto' || cs.overflowX === 'scroll') && e.scrollWidth > e.clientWidth + 2 && e.clientWidth > 0; });
  for (const s of scrollers) {
    // Horizontal scrollers that are meant to be (tab strips, chip rows) usually set white-space:nowrap or flex nowrap.
    const cs = getComputedStyle(s);
    const intended = cs.flexWrap === 'nowrap' && cs.display.includes('flex') || cs.whiteSpace === 'nowrap' || cs.scrollSnapType !== 'none' || cs.display.includes('grid') && cs.gridAutoFlow.includes('column');
    if (!intended) issues.push({t: 'hscroll-box', el: desc(s), d: `${s.scrollWidth}>${s.clientWidth}`});
  }
  // 2. interactive elements
  const ISEL = 'button,a[href],input:not([type=hidden]),select,textarea,summary,[data-action],[data-command],[role=button],[role=tab]';
  const inter = [...root.querySelectorAll(ISEL)].filter(el => shown(el) && !el.closest('[inert]') && !(el.closest(ISEL) !== el && el.parentElement.closest(ISEL)));
  const seen = new Set();
  for (const el of inter) {
    const c = clipRect(el);
    const w = c.R - c.L, h = c.B - c.T;
    if (w <= 2 || h <= 2) continue;  // scrolled away inside a scroller or clipped out
    const r = c.r;
    if (!c.hx && (r.left < -1 || r.right > W + 1)) issues.push({t: 'offscreen-x', el: desc(el), d: `${Math.round(r.left)}..${Math.round(r.right)} / ${W}`});
    if ((r.width < w - 1 || r.height < h - 1)) {}
    // partially clipped by a non-scroll ancestor (overflow hidden), horizontally
    if (!c.hx && r.width > 4 && w < r.width - 3 && c.R < W - 1 && c.L > 1) issues.push({t: 'clipped-x', el: desc(el), d: `visible ${Math.round(w)} of ${Math.round(r.width)}`});
    // tap size
    const tag = el.tagName;
    if (!['INPUT', 'SELECT', 'TEXTAREA'].includes(tag) || ['button', 'submit'].includes(el.type)) {
      if ((r.height < MINTAP - 0.5 || r.width < MINTAP - 0.5) && r.width < 400) {
        if (!(tag === 'A' && getComputedStyle(el).display === 'inline')) issues.push({t: 'small-tap', el: desc(el), d: `${Math.round(r.width)}x${Math.round(r.height)}`});
      }
    }
    // covered: sample 5 points of the visible rect
    const pts = [[.5, .5], [.2, .5], [.8, .5], [.5, .25], [.5, .75], [.1, .15], [.9, .15], [.1, .85], [.9, .85]];
    let covered = 0, by = null;
    for (const [fx, fy] of pts) {
      const x = c.L + w * fx, y = c.T + h * fy;
      if (x < 0 || y < 0 || x >= W || y >= H) continue;
      const hit = document.elementFromPoint(x, y);
      if (!hit) continue;
      if (hit === el || el.contains(hit) || hit.contains(el)) continue;
      // a <label> wrapping or for the input counts as the same control
      if (hit.closest('label') && hit.closest('label').contains(el)) continue;
      covered++; by = hit;
    }
    if (covered >= 1 && !revealable(el, by)) {
      const key = desc(el) + '|' + desc(by);
      if (!seen.has(key)) { seen.add(key); issues.push({t: covered >= 3 ? 'covered' : 'covered-edge', el: desc(el), by: desc(by), d: `${covered}/9 points`}); }
    }
  }
  // 3. text overlap between unrelated elements
  const texts = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {acceptNode: n => n.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT});
  let n;
  while ((n = walker.nextNode())) {
    const p = n.parentElement;
    if (!p || !shown(p) || p.closest('[inert],script,style,noscript,[aria-hidden=true] svg')) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    const rects = [...rg.getClientRects()].filter(q => q.width > 2 && q.height > 2);
    if (!rects.length) continue;
    const c = clipRect(p);
    for (const q of rects) {
      const L = Math.max(q.left, c.L), R = Math.min(q.right, c.R), T = Math.max(q.top, c.T), B = Math.min(q.bottom, c.B);
      if (R - L > 2 && B - T > 2) texts.push({p, L, R, T, B, s: n.nodeValue.trim().slice(0, 30)});
    }
    if (texts.length > 1500) break;
  }
  const tseen = new Set();
  for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
    const a = texts[i], b = texts[j];
    if (a.p === b.p) continue;
    const ox = Math.min(a.R, b.R) - Math.max(a.L, b.L), oy = Math.min(a.B, b.B) - Math.max(a.T, b.T);
    if (ox > 3 && oy > Math.min(a.B - a.T, b.B - b.T) * 0.35) {
      // which one is drawn on top? the overlap must be real paint, not a text node hidden under an opaque box
      const x = (Math.max(a.L, b.L) + Math.min(a.R, b.R)) / 2, y = (Math.max(a.T, b.T) + Math.min(a.B, b.B)) / 2;
      const hit = document.elementFromPoint(x, y);
      const stack = document.elementsFromPoint(x, y);
      const ia = stack.indexOf(a.p), ib = stack.indexOf(b.p);
      if (ia >= 0 && ib >= 0) {
        const lowP = ia > ib ? a.p : b.p, low = Math.max(ia, ib);
        let hidden = false;
        for (let k = 0; k < low; k++) {
          const e = stack[k];
          if (e.contains(lowP) || e === a.p || e === b.p) continue;
          const cs = getComputedStyle(e);
          const m = cs.backgroundColor.match(/rgba?\(([^)]+)\)/);
          const alpha = m ? (m[1].split(',')[3] === undefined ? 1 : parseFloat(m[1].split(',')[3])) : 0;
          if (alpha > 0.6 || cs.backgroundImage !== 'none' || e.tagName === 'IMG' || e.tagName === 'CANVAS') { hidden = true; break; }
        }
        if (hidden) continue;
      }
      if (revealable(a.p, b.p) || revealable(b.p, a.p)) continue;
      const k = desc(a.p) + '|' + desc(b.p);
      if (tseen.has(k)) continue; tseen.add(k);
      issues.push({t: 'text-overlap', el: desc(a.p) + ` «${a.s}»`, by: desc(b.p) + ` «${b.s}»`, d: `${Math.round(ox)}x${Math.round(oy)} at ${Math.round(x)},${Math.round(y)} hit=${hit ? hit.tagName.toLowerCase() + '.' + (hit.className || '').toString().split(' ')[0] : '-'}`});
    }
  }
  // 4. clipped text (overflow hidden without ellipsis / line clamp)
  for (const el of [root, ...root.querySelectorAll('*')]) {
    if (!el.firstChild || !shown(el) || el.clientWidth <= 2) continue;
    const hasText = [...el.childNodes].some(x => x.nodeType === 3 && x.nodeValue.trim());
    if (!hasText) continue;
    const cs = getComputedStyle(el);
    if (cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
    if (cs.textOverflow === 'ellipsis' || cs.webkitLineClamp !== 'none' && cs.webkitLineClamp) continue;
    if (cs.overflowX === 'auto' || cs.overflowX === 'scroll' || cs.overflowY === 'auto' || cs.overflowY === 'scroll') continue;
    if (el.scrollWidth > el.clientWidth + 2 || el.scrollHeight > el.clientHeight + 3) {
      const r = el.getBoundingClientRect();
      if (r.bottom < 0 || r.top > H) continue;
      issues.push({t: 'text-clipped', el: desc(el), d: `${el.scrollWidth}x${el.scrollHeight} in ${el.clientWidth}x${el.clientHeight}`});
    }
  }
  // 5. Content wider than the viewport inside root (not in a scroller)
  return {root: rootName, W, H, issues};
}
