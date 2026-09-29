"""Smoke test for the interactive HTMLs: opens each file in headless Edge, types a search,
selects the first result, cycles through every group button/dropdown item (checking the
tooltip/visibility state that results) and, for animated files, changes the year with the
selection active. Prints one JSON line per file.

    python ui_smoke_test.py file1.html file2.html ...     (paths relative to this folder or absolute)
"""
import json
import os
import re
import subprocess
import sys
import tempfile

EDGE = "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
HERE = os.path.dirname(os.path.abspath(__file__))

SCENARIO = r"""
(function(){
  var out = {errs: window.__errs || []};
  function done(){ var pre=document.createElement('pre'); pre.id='dbg'; pre.textContent=JSON.stringify(out); document.body.appendChild(pre); }
  try {
    var gd = document.querySelector('.plotly-graph-div');
    var roles = gd.data.map(function(t){ return t.meta && t.meta.role; });
    out.roles = roles.filter(function(r){return r==='nodes';}).length + 'n/' + roles.filter(function(r){return r==='edgehover';}).length + 'e';
    out.legend = gd.data.filter(function(t,i){return roles[i]==='nodes';}).map(function(t){return t.name;});
    var nt = roles.map(function(r,i){return r==='nodes'?i:-1;}).filter(function(i){return i>=0;});
    var hv = String(gd.data[nt[0]].hovertext[0]); var nm = (hv.match(/<b>(.*?)<\/b>/)||[0,hv])[1];
    var term = nm.split(/[\s(]+/).filter(function(w){return w.length>=3;})[0] || nm;
    out.term = term;
    var q = document.getElementById('q'); q.value = term; q.dispatchEvent(new Event('input'));
    setTimeout(function(){
      out.nres = document.querySelectorAll('#res [data-g]').length;
      var r = document.querySelector('#res [data-g]'); if (r) r.dispatchEvent(new MouseEvent('mousedown'));
      setTimeout(function(){
        var HL = gd.data.length-2, LB = gd.data.length-1;
        var hx = gd.data[HL].x || gd.data[HL].lon || [], lt = gd.data[LB].text || [];
        out.card = document.getElementById('card').textContent.length;
        out.hlEdges = hx.filter(function(v){return v!==null;}).length/2;
        out.labels = lt.length;
        // ---- group buttons / dropdown items
        var modes = [], items = [];
        (gd.layout.updatemenus||[]).forEach(function(m){ (m.buttons||[]).forEach(function(b){ if (b.method==='restyle') items.push(b); }); });
        items.forEach(function(b){
          try {
            Plotly.restyle(gd, b.args[0], b.args[1]);
            modes.push(b.label+': '+nt.map(function(i){ return gd.data[i].hoverinfo+'/'+gd.data[i].visible; }).join(' '));
          } catch(e) { modes.push(b.label+': ERR '+e.message); }
        });
        out.modes = modes;
        // ---- animated files: change year with selection active
        var fr = gd._transitionData && gd._transitionData._frames;
        if (fr && fr.length > 2) {
          Plotly.animate(gd, [fr[2].name], {frame:{duration:0, redraw:true}, mode:'immediate'}).then(function(){
            setTimeout(function(){
              var i0 = nt[0];
              out.frame = {name: fr[2].name, hlEdgesAfter: (gd.data[HL].x||[]).filter(function(v){return v!==null;}).length/2,
                           labelsAfter: (gd.data[LB].text||[]).length, dimmedColors: (Array.isArray(gd.data[i0].marker.color)? gd.data[i0].marker.color.filter(function(c){return /rgba/.test(c);}).length : -1)};
              done();
            }, 900);
          });
        } else { done(); }
      }, 900);
    }, 700);
  } catch (e) { out.fatal = e.message; done(); }
})();
"""


def test(path):
    src = open(path, encoding="utf-8").read()
    head = "<head><script>window.__errs=[];window.addEventListener('error',function(e){window.__errs.push(String(e.message))});</script>"
    src = src.replace("<head>", head, 1)
    src = src.replace("</body>", "<script>window.addEventListener('load',function(){setTimeout(function(){" + SCENARIO + "},5000);});</script></body>", 1)
    d = tempfile.mkdtemp(dir=os.path.dirname(path) if os.path.isdir(os.path.dirname(path)) else HERE)
    tmp = os.path.join(d, "t.html")
    open(tmp, "w", encoding="utf-8").write(src)
    win = subprocess.check_output(["wslpath", "-m", tmp]).decode().strip()
    dom = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--window-size=1700,1300", "--virtual-time-budget=90000",
                          "--dump-dom", "file:///" + win], capture_output=True, timeout=400).stdout.decode("utf-8", "ignore")
    os.remove(tmp)
    os.rmdir(d)
    m = re.search(r'<pre id="dbg">(.*?)</pre>', dom, re.S)
    if not m:
        return {"error": "no result (script did not finish)"}
    import html
    return json.loads(html.unescape(m.group(1)))


if __name__ == "__main__":
    for f in sys.argv[1:]:
        p = f if os.path.isabs(f) else os.path.join(HERE, f)
        r = test(p)
        print(os.path.relpath(p, HERE), json.dumps(r, ensure_ascii=False))
