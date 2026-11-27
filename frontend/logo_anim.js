/* MaBiYama · logo animada (vetorial). Lê window.LOGO_GEO (geometria) e window.LOGO_PAL (cores) e anima tudo com física
   simples a 60 qps: a água entra desenhando as faixas e não para de ondular; a engrenagem cai do céu com gravidade, quica e
   respinga; a bomba sobe de dentro da água numa mola amortecida (com respingos e as gotas saltando); um brilho passa pela bomba;
   o nome entra num corte da esquerda para a direita e o slogan sobe. Depois: engrenagem girando, água ondulando, bomba boiando. */
(function () {
  "use strict";
  var G = window.LOGO_GEO, NS = "http://www.w3.org/2000/svg", $ = function (id) { return document.getElementById(id); };
  var CX = 497.5, CY = 270, PCX = 669, PCY = 230;
  var reduz = false; try { reduz = matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { }

  /* ---------------- utilidades */
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function easeOut(t) { t = clamp(t, 0, 1); return 1 - Math.pow(1 - t, 3); }
  function easeInOut(t) { t = clamp(t, 0, 1); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function suave(pts) {   // Catmull-Rom fechado -> cúbicas
    var n = pts.length, d = "M" + pts[0][0].toFixed(1) + "," + pts[0][1].toFixed(1);
    for (var i = 0; i < n; i++) {
      var p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
      d += "C" + (p1[0] + (p2[0] - p0[0]) / 6).toFixed(1) + "," + (p1[1] + (p2[1] - p0[1]) / 6).toFixed(1) + " " +
        (p2[0] - (p3[0] - p1[0]) / 6).toFixed(1) + "," + (p2[1] - (p3[1] - p1[1]) / 6).toFixed(1) + " " + p2[0].toFixed(1) + "," + p2[1].toFixed(1);
    }
    return d + "Z";
  }

  /* ---------------- água */
  var FAIXAS = [
    { k: "a", el: $("ag-a"), ini: .05, dur: .95, A: 5, ph: 0.0, vel: 1.25 },
    { k: "b", el: $("ag-b"), ini: .0, dur: 1.15, A: 6.5, ph: 1.7, vel: 1.45 },
    { k: "fio", el: $("ag-fio"), ini: .55, dur: .7, A: 4, ph: 2.4, vel: 1.6 },
    { k: "c", el: $("ag-c"), ini: .2, dur: 1.0, A: 6, ph: 3.1, vel: 1.35 }
  ];
  FAIXAS.forEach(function (f) { f.p = G.agua[f.k]; f.x0 = f.p[0][0]; f.x1 = f.p[f.p.length - 1][0]; });
  function onda(x, t) { return 6 * Math.sin(x * .0098 - t * 1.35) + 2.6 * Math.sin(x * .023 + t * 1.9 + 1.3); }
  function desenhaFaixa(f, t, rev) {
    if (rev <= 0) { f.el.setAttribute("d", ""); return; }
    var xr = f.x0 + (f.x1 - f.x0) * rev, top = [], bot = [], p = f.p, w = f.x1 - f.x0;
    for (var i = 0; i < p.length; i++) {
      var x = p[i][0]; if (x > xr) break;
      var u = (x - f.x0) / w, env = Math.pow(Math.sin(Math.PI * clamp(u, 0, 1)), .55);
      // a mesma onda para todas as faixas (as folgas brancas entre elas se mantêm); cada faixa só respira um pouco
      var off = onda(x, t) * (.45 + .55 * env);
      var resp = 1.1 * Math.sin(x * .019 - t * 1.9 + f.ph) * env, ty = p[i][1] + off - resp * .4, by = p[i][2] + off + resp * .6;
      var cab = (xr - x) / 46;                 // cabeça da faixa afinando enquanto ela entra
      if (rev < 1 && cab < 1) { var m = (ty + by) / 2, k = Math.max(0, cab); ty = m + (ty - m) * k; by = m + (by - m) * k; }
      top.push([x, ty]); bot.push([x, by]);
    }
    if (top.length < 3) { f.el.setAttribute("d", ""); return; }
    f.el.setAttribute("d", suave(top.concat(bot.reverse())));
  }

  /* ---------------- respingos (partículas) e ondas circulares */
  var gResp = $("respingos"), parts = [], aneis = [];
  function respingar(x0, x1, y, n, forca) {
    for (var i = 0; i < n; i++) {
      var c = document.createElementNS(NS, "circle"); c.setAttribute("fill", "url(#gGota)"); gResp.appendChild(c);
      var f = (i + Math.random() * .8) / n;
      parts.push({ el: c, x: x0 + (x1 - x0) * f, y: y, vx: (f - .5) * 520 * forca + (Math.random() - .5) * 120, vy: -(380 + Math.random() * 420) * forca,
        r: 4 + Math.random() * 7, vida: 0, max: .75 + Math.random() * .45 });
    }
    var e = document.createElementNS(NS, "ellipse"); e.setAttribute("fill", "none"); e.setAttribute("stroke", "url(#gGota)"); gResp.appendChild(e);
    aneis.push({ el: e, x: (x0 + x1) / 2, y: y + 4, rx: (x1 - x0) * .55, vida: 0 });
  }
  function passoParticulas(dt) {
    parts = parts.filter(function (p) {
      p.vida += dt; if (p.vida > p.max) { p.el.remove(); return false; }
      p.vy += 2300 * dt; p.x += p.vx * dt; p.y += p.vy * dt;
      var a = 1 - p.vida / p.max;
      p.el.setAttribute("cx", p.x.toFixed(1)); p.el.setAttribute("cy", p.y.toFixed(1)); p.el.setAttribute("r", (p.r * (.6 + .4 * a)).toFixed(1));
      p.el.setAttribute("opacity", Math.min(1, a * 1.6).toFixed(2)); return true;
    });
    aneis = aneis.filter(function (r) {
      r.vida += dt; if (r.vida > 1) { r.el.remove(); return false; }
      var k = easeOut(r.vida);
      r.el.setAttribute("cx", r.x); r.el.setAttribute("cy", r.y); r.el.setAttribute("rx", (r.rx * (.35 + .9 * k)).toFixed(1));
      r.el.setAttribute("ry", (r.rx * .16 * (.35 + .9 * k)).toFixed(1)); r.el.setAttribute("stroke-width", (6 * (1 - k) + 1).toFixed(1));
      r.el.setAttribute("opacity", (1 - r.vida).toFixed(2)); return true;
    });
  }

  /* ---------------- estado das peças */
  var eng = { y: -1250, v: 0, ang: -140, w: -430, quiques: 0, pousou: false, ativo: false };
  var bom = { y: 440, v: 0, ativo: false, rompeu: false, assentou: false, tAss: 0 };
  var got = { p: 0 }, elEng = $("eng"), elEngGiro = $("eng-giro"), elBom = $("bomba-mov"), elGot = $("gotas");
  var elNomeClip = $("clip-nome-r"), elNome = $("nome"), elSlogan = $("slogan"), elLinE = $("lin-e"), elLinD = $("lin-d"), elBrilho = $("brilho");
  var T0 = null, ultimo = null, brilhoEm = 2.75;

  function quadro(agora) {
    requestAnimationFrame(quadro);
    if (document.hidden) { ultimo = agora; return; }
    if (T0 === null) { T0 = agora; ultimo = agora; }
    var t = (agora - T0) / 1000, dt = Math.min(.034, (agora - ultimo) / 1000); ultimo = agora;

    // água: entra desenhando e ondula sempre
    FAIXAS.forEach(function (f) { desenhaFaixa(f, t, easeInOut((t - f.ini) / f.dur)); });

    // engrenagem: gravidade, quiques e giro
    if (t > .22) eng.ativo = true;
    if (eng.ativo && !eng.pousou) {
      eng.v += 3600 * dt; eng.y += eng.v * dt;
      if (eng.y >= 0) {
        eng.y = 0;
        if (eng.quiques === 0) { respingar(215, 390, 338, 12, 1); eng.w *= .35; }
        eng.v = -eng.v * (eng.quiques === 0 ? .3 : .22); eng.quiques++;
        if (eng.quiques > 2 || Math.abs(eng.v) < 70) { eng.pousou = true; eng.v = 0; }
      }
    }
    var wAlvo = eng.pousou ? 20 : eng.w;          // depois de pousar, gira devagar e sem parar
    eng.w += (wAlvo - eng.w) * Math.min(1, dt * (eng.pousou ? 1.6 : .4));
    if (eng.ativo) eng.ang += eng.w * dt;
    elEng.setAttribute("transform", "translate(0," + eng.y.toFixed(2) + ")");
    elEngGiro.setAttribute("transform", "rotate(" + eng.ang.toFixed(2) + " " + CX + " " + CY + ")");
    elEng.setAttribute("opacity", eng.ativo ? 1 : 0);

    // bomba: mola amortecida subindo da água
    if (t > 1.2) bom.ativo = true;
    var by = bom.y, rot = 0;
    if (bom.ativo && !bom.assentou) {
      var a = -95 * bom.y - 11.5 * bom.v; bom.v += a * dt; bom.y += bom.v * dt;
      if (!bom.rompeu && bom.y < 300) { bom.rompeu = true; respingar(470, 900, 398, 18, 1.15); }
      if (bom.rompeu && Math.abs(bom.y) < .35 && Math.abs(bom.v) < 2) { bom.assentou = true; bom.tAss = t; bom.y = 0; }
      by = bom.y; rot = clamp(bom.v * .006, -4, 4);
    }
    if (bom.assentou) { var tb = t - bom.tAss; by = 4.5 * Math.sin(tb * 1.5); rot = .7 * Math.sin(tb * 1.5 - .6); }
    elBom.setAttribute("transform", "translate(0," + by.toFixed(2) + ") rotate(" + rot.toFixed(2) + " " + PCX + " " + PCY + ")");

    // gotas: saltam quando a bomba rompe a superfície e depois balançam
    if (bom.rompeu) got.p = Math.min(1, got.p + dt / .7);
    var gp = got.p, gs = gp < 1 ? .2 + .8 * (1 + 2.2 * Math.pow(gp - 1, 3) + 1.2 * Math.pow(gp - 1, 2)) : 1;
    var gx = -120 * (1 - easeOut(gp)), gyy = 90 * (1 - easeOut(gp)), bob = gp >= 1 ? Math.sin(t * 2.2) : 0;
    elGot.setAttribute("transform", "translate(" + (gx + bob * 3).toFixed(1) + "," + (gyy - Math.abs(bob) * 5).toFixed(1) + ") translate(1175 280) scale(" + gs.toFixed(3) + ") translate(-1175 -280)");
    elGot.setAttribute("opacity", clamp(gp * 3, 0, 1).toFixed(2));

    // brilho atravessando a bomba (depois que ela assenta, e de tempos em tempos)
    var tb2 = t - brilhoEm;
    if (tb2 > 0) {
      var pb = tb2 / 1.15; elBrilho.setAttribute("transform", "translate(" + (lerpN(-260, 760, easeInOut(pb))).toFixed(1) + ",0) skewX(-18)");
      elBrilho.setAttribute("opacity", pb < 1 ? (Math.sin(Math.PI * clamp(pb, 0, 1)) * .85).toFixed(2) : 0);
      if (tb2 > 7.5) brilhoEm = t;
    } else elBrilho.setAttribute("opacity", 0);

    // nome e slogan
    var pn = easeOut((t - 2.15) / .95);
    elNomeClip.setAttribute("width", (1320 * pn).toFixed(1));
    elNome.setAttribute("transform", "translate(0," + (16 * (1 - pn)).toFixed(1) + ")");
    var ps = easeOut((t - 2.7) / .8);
    elSlogan.setAttribute("opacity", ps.toFixed(2)); elSlogan.setAttribute("transform", "translate(0," + (14 * (1 - ps)).toFixed(1) + ")");
    var pl = easeOut((t - 2.6) / .9);
    elLinE.setAttribute("transform", "translate(132 0) scale(" + pl.toFixed(3) + " 1) translate(-132 0)");
    elLinD.setAttribute("transform", "translate(1161 0) scale(" + pl.toFixed(3) + " 1) translate(-1161 0)");

    passoParticulas(dt);
  }
  function lerpN(a, b, k) { return a + (b - a) * k; }

  if (reduz) {   // sem movimento: logo pronta, parada
    FAIXAS.forEach(function (f) { f.A = 0; desenhaFaixa(f, 0, 1); });
    $("eng").setAttribute("opacity", 1); $("clip-nome-r").setAttribute("width", 1320);
    return;
  }
  requestAnimationFrame(quadro);
})();
