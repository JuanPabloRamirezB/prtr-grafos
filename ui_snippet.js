(function () {
  // Generic search / highlight layer for the PRTR graphs (see prtr_ui.py).
  var gd = document.getElementById('{plot_id}');
  var D = __DATA__;
  var GEO = D.geo, NT = D.nt, HL = D.HL, LB = D.LB;
  var curFrame = null, lastMenu = null, state = {m: [], sel: null};

  function arr(v, n, d) {
    if (Array.isArray(v)) return v.slice();
    var a = new Array(n);
    for (var i = 0; i < n; i++) a[i] = (v === undefined || v === null) ? d : v;
    return a;
  }
  function npts(t) { return (GEO ? gd.data[t].lon : gd.data[t].x).length; }
  function rgba(c, a) {
    if (typeof c !== 'string') return c;
    if (c.charAt(0) === '#') {
      var h = c.slice(1);
      if (h.length === 3) h = h.replace(/./g, '$&$&');
      return 'rgba(' + parseInt(h.slice(0, 2), 16) + ',' + parseInt(h.slice(2, 4), 16) + ',' + parseInt(h.slice(4, 6), 16) + ',' + a + ')';
    }
    var m = c.match(/rgba?\(([^)]+)\)/);
    if (m) return 'rgba(' + m[1].split(',').slice(0, 3).map(function (s) { return s.trim(); }).join(',') + ',' + a + ')';
    return c;
  }
  function norm(s) { return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  var NORM = D.search.map(norm);

  // Pristine arrays of every node trace. Animation frames overwrite size/color/text each year,
  // so the "base" of the current frame is looked up in the frame itself when there is one.
  var INIT = {};
  NT.forEach(function (t) {
    var d = gd.data[t], n = npts(t);
    INIT[t] = {size: arr(d.marker && d.marker.size, n, 8), color: arr(d.marker && d.marker.color, n, '#888888'), text: arr(d.text, n, '')};
  });
  function baseOf(t) {
    var b = INIT[t], fr = gd._transitionData && gd._transitionData._frames;
    if (curFrame !== null && fr) {
      for (var k = 0; k < fr.length; k++) {
        if (fr[k].name !== curFrame) continue;
        var f = fr[k], idx = f.traces || f.data.map(function (_, i) { return i; }), j = idx.indexOf(t);
        if (j < 0) break;
        var s = f.data[j], n = npts(t);
        return {
          size: s.marker && s.marker.size !== undefined ? arr(s.marker.size, n, 8) : b.size,
          color: s.marker && s.marker.color !== undefined ? arr(s.marker.color, n, '#888888') : b.color,
          text: s.text !== undefined ? arr(s.text, n, '') : b.text
        };
      }
    }
    return b;
  }

  var fx, fy;
  if (GEO) { fx = gd._fullLayout.geo.lonaxis.range.slice(); fy = gd._fullLayout.geo.lataxis.range.slice(); }
  else { fx = gd._fullLayout.xaxis.range.slice(); fy = gd._fullLayout.yaxis.range.slice(); }

  var bar = document.createElement('div');
  bar.style.cssText = 'position:relative;margin:8px 16px 4px;font:13px system-ui,-apple-system,Segoe UI,sans-serif;color:#0b0b0b;max-width:760px;';
  bar.innerHTML =
    '<div style="display:flex;gap:8px;align-items:center">' +
    '<a href="' + D.home + '" style="white-space:nowrap;color:#2a78d6;text-decoration:none;font-weight:600" title="Volver al índice de gráficos">← Índice</a>' +
    '<input id="q" type="search" autocomplete="off" placeholder="' + D.placeholder + '" ' +
    'style="flex:1;padding:9px 11px;border:1px solid #c3c2b7;border-radius:6px;font:inherit;background:#fff">' +
    '<button id="clr" style="padding:9px 12px;border:1px solid #c3c2b7;border-radius:6px;background:#f2f1ec;font:inherit;cursor:pointer">Limpiar</button></div>' +
    '<div id="res" style="position:absolute;left:0;right:78px;top:42px;z-index:20;background:#fff;border:1px solid #c3c2b7;border-radius:0 0 6px 6px;max-height:300px;overflow:auto;display:none;box-shadow:0 4px 12px rgba(0,0,0,.12)"></div>' +
    '<div id="card" style="margin-top:6px;color:#52514e;line-height:1.35"></div>';
  gd.parentNode.insertBefore(bar, gd);
  var q = bar.querySelector('#q'), res = bar.querySelector('#res'), card = bar.querySelector('#card');

  function apply(matches, sel) {
    state = {m: matches, sel: sel};
    var hi = new Set(matches), nb = new Set();
    if (sel !== null) { hi = new Set([sel]); D.nbrs[sel].forEach(function (g) { nb.add(g); }); }
    var active = hi.size > 0, slot = {}, cl = [], tx = [], sz = [], base = [];
    NT.forEach(function (t, k) {
      slot[t] = k; var b = baseOf(t); base.push(b);
      cl.push(b.color.slice()); tx.push(b.text.slice()); sz.push(b.size.slice());
    });
    var lx = [], ly = [], lt = [];
    for (var g = 0; g < D.name.length; g++) {
      var k = slot[D.tr[g]], i = D.ix[g], b = base[k];
      if (!active) { /* keep base */ }
      else if (hi.has(g)) { tx[k][i] = ''; sz[k][i] = b.size[i] * 1.5 + 4; lx.push(D.x[g]); ly.push(D.y[g]); lt.push(D.name[g]); }
      else if (nb.has(g)) { tx[k][i] = ''; if (nb.size <= 60) { lx.push(D.x[g]); ly.push(D.y[g]); lt.push(D.name[g]); } }
      else { cl[k][i] = rgba(b.color[i], 0.07); tx[k][i] = ''; }
    }
    if (lt.length > 80) { lx = lx.slice(0, 80); ly = ly.slice(0, 80); lt = lt.slice(0, 80); }
    Plotly.restyle(gd, {'marker.color': cl, text: tx, 'marker.size': sz}, NT);
    var ex = [], ey = [];
    if (sel !== null) D.nbrs[sel].forEach(function (n) { ex.push(D.x[sel], D.x[n], null); ey.push(D.y[sel], D.y[n], null); });
    var hlv = GEO ? {lon: [ex], lat: [ey]} : {x: [ex], y: [ey]};
    var lbv = GEO ? {lon: [lx], lat: [ly], text: [lt]} : {x: [lx], y: [ly], text: [lt]};
    Plotly.restyle(gd, hlv, [HL]);
    Plotly.restyle(gd, lbv, [LB]);
    if (D.lines !== null) Plotly.restyle(gd, {opacity: active ? 0.04 : D.lineOpacity}, [D.lines]);
  }
  function zoom(sel) {
    var pts = [sel].concat(D.nbrs[sel]);
    var xs = pts.map(function (g) { return D.x[g]; }), ys = pts.map(function (g) { return D.y[g]; });
    var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs), miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
    var minSpan = 0.08 * Math.max(fx[1] - fx[0], fy[1] - fy[0]);
    var px = Math.max((maxx - minx) * 0.2, minSpan), py = Math.max((maxy - miny) * 0.2, minSpan);
    if (GEO) Plotly.relayout(gd, {'geo.lonaxis.range': [minx - px, maxx + px], 'geo.lataxis.range': [miny - py, maxy + py]});
    else Plotly.relayout(gd, {'xaxis.range': [minx - px, maxx + px], 'yaxis.range': [miny - py, maxy + py]});
  }
  function unzoom() {
    if (GEO) Plotly.relayout(gd, {'geo.lonaxis.range': fx, 'geo.lataxis.range': fy});
    else Plotly.relayout(gd, {'xaxis.range': fx, 'yaxis.range': fy});
  }
  function badge(g) { return '<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:' + D.gcolor[D.grp[g]] + ';margin-right:6px"></span>'; }
  function select(g) {
    res.style.display = 'none';
    q.value = D.name[g];
    apply([], g); zoom(g);
    var tip = gd.data[D.tr[g]].hovertext[D.ix[g]];
    card.innerHTML = '<div style="border-left:3px solid ' + D.gcolor[D.grp[g]] + ';padding:4px 10px;background:#fcfcfb">' + tip +
      '<br><i>' + D.nbrs[g].length + ' conexiones' + (D.nbrs[g].length <= 60 ? ' resaltadas y rotuladas' : ' resaltadas') + '</i></div>';
  }
  function clearAll() {
    q.value = ''; res.style.display = 'none'; card.innerHTML = '';
    apply([], null); unzoom();
  }
  function run() {
    var s = norm(q.value.trim());
    if (!s) { clearAll(); return; }
    card.innerHTML = '';
    var toks = s.split(/\s+/), m = [];
    for (var g = 0; g < NORM.length; g++) {
      var ok = true;
      for (var k = 0; k < toks.length; k++) if (NORM[g].indexOf(toks[k]) < 0) { ok = false; break; }
      if (ok) m.push(g);
    }
    m.sort(function (a, b) {
      var sa = norm(D.name[a]).indexOf(s) === 0 ? 0 : 1, sb = norm(D.name[b]).indexOf(s) === 0 ? 0 : 1;
      return sa - sb || D.rank[a] - D.rank[b];
    });
    apply(m, null);
    if (m.length !== 1) unzoom();
    if (!m.length) { res.innerHTML = '<div style="padding:8px 10px;color:#898781">Sin coincidencias</div>'; res.style.display = 'block'; res._first = undefined; return; }
    res.innerHTML = m.slice(0, 12).map(function (g) {
      return '<div data-g="' + g + '" style="padding:6px 10px;cursor:pointer;border-bottom:1px solid #f2f1ec">' + badge(g) + D.name[g] +
        (D.gname[D.grp[g]] ? ' <span style="color:#898781">· ' + D.gname[D.grp[g]] + '</span>' : '') + '</div>';
    }).join('') + (m.length > 12 ? '<div style="padding:6px 10px;color:#898781">… y ' + (m.length - 12) + ' más (todas resaltadas en el gráfico)</div>' : '');
    res.style.display = 'block';
    Array.prototype.forEach.call(res.querySelectorAll('[data-g]'), function (el) {
      el.addEventListener('mousedown', function () { select(parseInt(el.getAttribute('data-g'), 10)); });
    });
    res._first = m[0];
  }
  q.addEventListener('input', run);
  q.addEventListener('focus', function () { if (q.value && state.sel === null) run(); });
  q.addEventListener('blur', function () { setTimeout(function () { res.style.display = 'none'; }, 150); });
  q.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && res._first !== undefined && state.sel === null) { e.preventDefault(); select(res._first); }
    if (e.key === 'Escape') clearAll();
  });
  bar.querySelector('#clr').addEventListener('click', clearAll);

  // Animated graphs: every frame re-sends size/color/text (and may drop restyled marker.opacity),
  // so after each year change the type mode (button) and the search highlight are re-applied.
  gd.on('plotly_buttonclicked', function (e) {
    if (e && e.button && e.button.method === 'restyle') lastMenu = e.button.args;
  });
  gd.on('plotly_animatingframe', function (e) {
    if (e && e.frame) curFrame = e.frame.name;
    setTimeout(function () {
      if (lastMenu) Plotly.restyle(gd, lastMenu[0], lastMenu[1]);
      if (state.sel !== null || state.m.length) apply(state.m, state.sel);
    }, 60);
  });
})();
