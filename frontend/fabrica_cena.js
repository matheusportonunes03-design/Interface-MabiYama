/* MaBiYama · cena isométrica estilo Habbo Hotel (desenho). Fragmento: é embutido em fabrica.js por animacao.py. */
var G = { ctx: null, vw: 0, vh: 0, dpr: 1, flipX: false };
var TW = 72, TH = 36, ZU = 36, SW = 13, SD = 10, WH = 5.7, PX0 = 2.7;
var SC = 1, OX = 0, OY = 0, PXS = 2.3;
var INK = '#17203a';
var COR = {
  fundoA: '#0b1530', fundoB: '#1d3f86', pisoA: '#dde5ef', pisoB: '#cbd6e5', pisoL: 'rgba(110,130,165,.45)', laje: '#8d9db8', lajeS: '#6f819f',
  paredeD: '#7aa2e0', paredeE: '#5f8bd0', pTopo: '#d6e4fb', pTopoE: '#c3d6f6', pEnd: '#3f66ad', rodape: '#3d63a8', trilho: '#a9c4f1',
  aco: '#7f93b3', acoL: '#6a7fa2', acoR: '#586d8f', acoT: '#a7b9d4', escuro: '#1a2845', amarelo: '#ffc21a', laranja: '#ff7a1a',
  verde: '#35d07f', ambar: '#ffb020', verm: '#ff4d4d', ciano: '#5fe0ff'
};

function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
function lerp(a, b, t) { return a + (b - a) * t; }
function ease(t) { t = clamp(t, 0, 1); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

function pj(x, y, z) { return [OX + (x - y) * TW / 2 * SC, OY + ((x + y) * TH / 2 - (z || 0) * ZU) * SC]; }

function layout(vw, vh) {
  G.vw = vw; G.vh = vh;
  var largura = (SW + SD) * TW / 2 + 60, altura = (SW + SD) * TH / 2 + WH * ZU + 40;
  SC = clamp(Math.min(vw * 0.97 / largura, vh * 0.86 / altura), 0.32, 2.2);
  PXS = PX0 * SC;
  var cx = (SW - SD) * TW / 4, topo = -WH * ZU, base = (SW + SD) * TH / 2;
  OX = vw / 2 - cx * SC;
  OY = vh / 2 - ((topo + base) / 2) * SC + vh * 0.035;
}

function poly(p, fill, stroke, lw) {
  var c = G.ctx; c.beginPath(); c.moveTo(p[0][0], p[0][1]);
  for (var i = 1; i < p.length; i++) c.lineTo(p[i][0], p[i][1]);
  c.closePath();
  if (fill) { c.fillStyle = fill; c.fill(); }
  if (stroke) { c.strokeStyle = stroke; c.lineWidth = lw || 1; c.lineJoin = 'round'; c.stroke(); }
}

/* plano 'y' (y=k, u=x) ou 'x' (x=k, u=y); v = altura. Dentro de fn desenha-se em coordenadas locais (u, v). */
function sobre(plano, k, u0, v0, fn) {
  var c = G.ctx, p = plano === 'y' ? pj(u0, k, v0) : pj(k, u0, v0);
  G.flipX = plano === 'x';
  c.save();
  c.transform(plano === 'y' ? TW / 2 * SC : -TW / 2 * SC, TH / 2 * SC, 0, -ZU * SC, p[0], p[1]);
  fn(c);
  c.restore();
}
function rc(c, u, v, w, h, fill) { c.fillStyle = fill; c.fillRect(u, v, w, h); }
function lin(c, u1, v1, u2, v2, cor, lw) { c.strokeStyle = cor; c.lineWidth = lw; c.lineCap = 'round'; c.beginPath(); c.moveTo(u1, v1); c.lineTo(u2, v2); c.stroke(); }
function txtL(c, s, u, v, tam, cor) {
  c.save(); c.translate(u, v); c.scale(G.flipX ? -1 : 1, -1); var k = tam / 10; c.scale(k, k);
  c.font = '800 10px Nunito, system-ui, sans-serif'; c.fillStyle = cor; c.textAlign = 'center'; c.textBaseline = 'alphabetic';
  c.fillText(s, 0, 0); c.restore();
}
function disco(c, u, v, r, fill) { c.fillStyle = fill; c.beginPath(); c.arc(u, v, r, 0, 6.2832); c.fill(); }
function faixaPerigo(c, u, v, w, h) {
  rc(c, u, v, w, h, COR.amarelo);
  c.fillStyle = INK;
  for (var s = -h; s < w; s += h * 1.6) {
    var a = Math.max(0, s), b = Math.min(w, s + h * .8);
    if (b <= a) continue;
    c.beginPath(); c.moveTo(u + Math.max(0, s), v); c.lineTo(u + Math.min(w, s + h * .8), v);
    c.lineTo(u + Math.min(w, s + h * .8 + h * .0), v + h); c.lineTo(u + Math.max(0, s - h * .8 + h * .8), v + h); c.closePath(); c.fill();
  }
}

function caixa(x, y, w, d, h, z0, cT, cL, cR, borda) {
  var z1 = z0 + h, b = borda || 'rgba(15,25,55,.55)';
  poly([pj(x, y, z1), pj(x + w, y, z1), pj(x + w, y + d, z1), pj(x, y + d, z1)], cT, b, 1);
  poly([pj(x, y + d, z0), pj(x + w, y + d, z0), pj(x + w, y + d, z1), pj(x, y + d, z1)], cL, b, 1);
  poly([pj(x + w, y, z0), pj(x + w, y + d, z0), pj(x + w, y + d, z1), pj(x + w, y, z1)], cR, b, 1);
}
function cilindro(cx, cy, r, z0, h, cT, cL, cR) {
  var a = r * TW * 0.7071 * SC, b = a / 2, p0 = pj(cx, cy, z0), p1 = pj(cx, cy, z0 + h), c = G.ctx;
  var g = c.createLinearGradient(p0[0] - a, 0, p0[0] + a, 0); g.addColorStop(0, cL); g.addColorStop(1, cR);
  c.fillStyle = g; c.beginPath(); c.ellipse(p0[0], p0[1], a, b, 0, 0, Math.PI); c.lineTo(p1[0] - a, p1[1]); c.ellipse(p1[0], p1[1], a, b, 0, Math.PI, 0, true); c.closePath(); c.fill();
  c.strokeStyle = 'rgba(15,25,55,.5)'; c.lineWidth = 1; c.stroke();
  c.fillStyle = cT; c.beginPath(); c.ellipse(p1[0], p1[1], a, b, 0, 0, 6.2832); c.fill(); c.stroke();
}

/* ------------------------------------------------------------------ fundo estático (pré-renderizado) */
function desenharFundo(c) {
  var vw = G.vw, vh = G.vh, i, j, g;
  g = c.createLinearGradient(0, 0, 0, vh); g.addColorStop(0, COR.fundoA); g.addColorStop(1, COR.fundoB);
  c.fillStyle = g; c.fillRect(0, 0, vw, vh);
  c.fillStyle = 'rgba(160,200,255,.16)';
  for (i = 0; i < 70; i++) { var px = (i * 197 % 101) / 101 * vw, py = (i * 61 % 97) / 97 * vh; c.fillRect(Math.round(px), Math.round(py), 2, 2); }

  // laje (espessura do piso)
  poly([pj(SW, 0, 0), pj(SW, SD, 0), pj(SW, SD, -.42), pj(SW, 0, -.42)], COR.lajeS, INK, 1);
  poly([pj(0, SD, 0), pj(SW, SD, 0), pj(SW, SD, -.42), pj(0, SD, -.42)], COR.laje, INK, 1);
  // piso
  for (i = 0; i < SW; i++) for (j = 0; j < SD; j++)
    poly([pj(i, j, 0), pj(i + 1, j, 0), pj(i + 1, j + 1, 0), pj(i, j + 1, 0)], (i + j) % 2 ? COR.pisoB : COR.pisoA, COR.pisoL, 1);
  // faixa de perigo na frente das máquinas e corredor
  var f = [pj(1.2, 2.0, 0), pj(12.6, 2.0, 0), pj(12.6, 2.2, 0), pj(1.2, 2.2, 0)];
  poly(f, COR.amarelo);
  for (i = 0; i < 57; i++) { var u = 1.2 + i * 0.2; poly([pj(u, 2.0, 0), pj(u + .1, 2.0, 0), pj(u + .2, 2.2, 0), pj(u + .1, 2.2, 0)], INK); }
  poly([pj(1.0, 2.9, 0), pj(12.6, 2.9, 0), pj(12.6, 2.96, 0), pj(1.0, 2.96, 0)], 'rgba(255,255,255,.55)');

  // parede direita (plano y=0)
  poly([pj(0, 0, WH), pj(SW, 0, WH), pj(SW, -.38, WH), pj(0, -.38, WH)], COR.pTopo, INK, 1);
  poly([pj(SW, 0, 0), pj(SW, -.38, 0), pj(SW, -.38, WH), pj(SW, 0, WH)], COR.pEnd, INK, 1);
  sobre('y', 0, 0, 0, function (c) {
    g = c.createLinearGradient(0, 0, 0, WH); g.addColorStop(0, COR.paredeD); g.addColorStop(1, '#8db1ea');
    rc(c, 0, 0, SW, WH, g);
    for (var k = 1; k < SW; k++) lin(c, k, .35, k, WH, 'rgba(20,40,90,.10)', .02);
    rc(c, 0, 0, SW, .35, COR.rodape); rc(c, 0, 1.45, SW, .1, COR.trilho); rc(c, 0, 5.3, SW, .4, '#4d77c0');
    // placa
    rc(c, 3.9, 3.85, 5.3, 1.1, '#f6f9ff'); rc(c, 3.9, 3.85, 5.3, .08, COR.amarelo); rc(c, 3.9, 4.87, 5.3, .08, COR.amarelo);
    txtL(c, 'MABIYAMA', 6.55, 4.62, .5, '#1e3f9a'); txtL(c, 'MANUTENÇÃO PREDITIVA', 6.55, 4.12, .22, '#4a5b7d');
    // relógio
    disco(c, 2.2, 4.5, .42, '#f8fbff'); disco(c, 2.2, 4.5, .34, '#fff');
    lin(c, 2.2, 4.5, 2.2, 4.77, INK, .05); lin(c, 2.2, 4.5, 2.42, 4.4, INK, .05);
    // tubulação
    rc(c, 0, 5.0, SW, .13, '#9aa9bf'); rc(c, 0, 5.0, SW, .04, '#c8d3e3');
    for (k = 1; k < SW; k += 3) rc(c, k, 4.95, .12, .23, '#74839c');
    // extintor + quadro de aviso
    rc(c, 12.25, .45, .34, 1.05, '#d63b3b'); rc(c, 12.25, 1.2, .34, .12, INK); rc(c, 12.32, 1.5, .2, .2, '#222');
    rc(c, 11.5, 2.4, .6, .8, '#fff7d6'); rc(c, 11.5, 3.12, .6, .08, COR.amarelo);
    txtL(c, 'EPI', 11.8, 2.55, .26, '#c24100');
  });

  // parede esquerda (plano x=0)
  poly([pj(0, 0, WH), pj(0, SD, WH), pj(-.38, SD, WH), pj(-.38, 0, WH)], COR.pTopoE, INK, 1);
  poly([pj(-.38, SD, 0), pj(0, SD, 0), pj(0, SD, WH), pj(-.38, SD, WH)], COR.pEnd, INK, 1);
  poly([pj(-.38, -.38, WH), pj(0, -.38, WH), pj(0, 0, WH), pj(-.38, 0, WH)], COR.pTopo, INK, 1);
  sobre('x', 0, 0, 0, function (c) {
    g = c.createLinearGradient(0, 0, 0, WH); g.addColorStop(0, COR.paredeE); g.addColorStop(1, '#7ea3dd');
    rc(c, 0, 0, SD, WH, g);
    for (var k = 1; k < SD; k++) lin(c, k, .35, k, WH, 'rgba(10,25,70,.14)', .02);
    rc(c, 0, 0, SD, .35, COR.rodape); rc(c, 0, 1.45, SD, .1, 'rgba(255,255,255,.35)');
    [[0.8, 2.9], [6.0, 8.7]].forEach(function (j) {
      var w = j[1] - j[0]; rc(c, j[0] - .08, 3.52, w + .16, 1.66, '#eaf1ff');
      var gg = c.createLinearGradient(0, 3.6, 0, 5.0); gg.addColorStop(0, '#9fd3ff'); gg.addColorStop(1, '#e4f4ff');
      rc(c, j[0], 3.6, w, 1.5, gg); rc(c, j[0] + w / 2 - .04, 3.6, .08, 1.5, '#eaf1ff'); rc(c, j[0], 4.28, w, .06, '#eaf1ff');
      c.fillStyle = 'rgba(255,255,255,.55)'; c.beginPath(); c.moveTo(j[0] + .2, 3.6); c.lineTo(j[0] + .6, 3.6); c.lineTo(j[0] + .1, 4.3); c.lineTo(j[0] - .0, 4.3); c.fill();
    });
    // porta (vão)
    rc(c, 4.1, 0, 1.7, 3.45, '#202b4a'); rc(c, 4.2, 0, 1.5, 3.35, '#e9f5ff');
    var gp = c.createLinearGradient(0, 0, 0, 3.35); gp.addColorStop(0, '#ffffff'); gp.addColorStop(1, '#b9dcff'); rc(c, 4.2, 0, 1.5, 3.35, gp);
    rc(c, 4.45, 3.6, 1.0, .34, '#1f9d62'); txtL(c, 'ENTRADA', 4.95, 3.67, .2, '#fff');
  });
}

/* ------------------------------------------------------------------ objetos dinâmicos */
function porta(E) {
  // folha da porta: abre girando (largura diminui)
  var aberta = clamp(E.porta, 0, 1);
  if (aberta >= .98) return;
  sobre('x', 0, 4.2, 0, function (c) {
    var w = 1.5 * (1 - aberta);
    rc(c, 0, 0, w, 3.35, '#7a8ca8'); rc(c, 0, 0, w, .12, '#5b6c87'); rc(c, w * .15, 1.3, w * .25, .1, '#d6dfec');
    rc(c, w * .1, 1.9, w * .8, .7, '#a8c9ee');
  });
}

function bancada(E) {
  // painel de ferramentas na parede
  sobre('x', 0, 6.3, 1.55, function (c) {
    rc(c, 0, 0, 2.3, 2.0, '#3a465f'); rc(c, .04, .04, 2.22, 1.92, '#4c5a78');
    for (var u = .15; u < 2.2; u += .3) for (var v = .15; v < 1.9; v += .3) rc(c, u, v, .04, .04, '#2a344b');
    // martelo
    rc(c, .3, .25, .09, 1.3, '#c58b4a'); rc(c, .15, 1.4, .4, .2, '#8c97a8');
    // chave de fenda
    rc(c, .85, .3, .07, 1.0, '#9aa5b5'); rc(c, .8, .1, .17, .4, '#e0553d');
    // alicate
    rc(c, 1.3, .6, .06, .8, '#c9d1dc'); rc(c, 1.42, .6, .06, .8, '#c9d1dc'); rc(c, 1.28, .35, .22, .3, '#e0553d');
    // contorno da chave inglesa (sempre) / chave (se ainda lá)
    c.strokeStyle = 'rgba(255,255,255,.45)'; c.lineWidth = .02; c.setLineDash([.06, .05]);
    c.strokeRect(1.7, .2, .4, 1.55); c.setLineDash([]);
    if (E.banca.ferr) { rc(c, 1.85, .25, .1, 1.1, '#c5ced8'); rc(c, 1.76, 1.3, .1, .35, '#c5ced8'); rc(c, 1.96, 1.3, .1, .35, '#c5ced8'); rc(c, 1.76, 1.3, .3, .1, '#c5ced8'); }
  });
  caixa(0, 6.4, 1.05, 2.1, 1.1, 0, '#c5a06a', '#8d6a3d', '#a77f4a');
  poly([pj(1.05, 6.4, 1.1), pj(1.05, 8.5, 1.1), pj(1.05, 8.5, 1.18), pj(1.05, 6.4, 1.18)], '#5a6781', INK, 1);
  caixa(.0, 6.4, 1.05, 2.1, .1, 1.1, '#e0c08b', '#a98450', '#b8905a');
  sobre('x', 1.05, 6.4, 0, function (c) {
    rc(c, .1, .15, 1.9, .8, '#7c5a30'); rc(c, .1, .15, 1.9, .04, '#b08a55'); rc(c, .9, .45, .35, .12, '#2a1f10');
  });
  if (E.banca.caixa) {
    caixa(.2, 6.75, .62, .8, .38, 1.2, '#e0554d', '#b8352f', '#c9423b');
    poly([pj(.35, 7.05, 1.58), pj(.67, 7.05, 1.58), pj(.67, 7.25, 1.58), pj(.35, 7.25, 1.58)], '#8a8f98', INK, 1);
  }
  if (E.banca.ferr) {
    var p = pj(.55, 7.9, 1.22), q = pj(.55, 8.35, 1.22), c = G.ctx;
    c.strokeStyle = '#c5ced8'; c.lineWidth = 4 * SC; c.lineCap = 'round'; c.beginPath(); c.moveTo(p[0], p[1]); c.lineTo(q[0], q[1]); c.stroke();
    c.strokeStyle = '#8c97a8'; c.lineWidth = 6 * SC; c.beginPath(); c.moveTo(q[0] - 3 * SC, q[1] - 1); c.lineTo(q[0] + 3 * SC, q[1] + 1); c.stroke();
  }
}

/* ---- máquinas ---- */
var TIPOS = ['cnc', 'prensa', 'torno', 'esteira', 'braco'];
function luzCor(n) { return n === 3 ? COR.verm : n === 2 ? COR.ambar : COR.verde; }

function maquina(m, t) {
  var x = m.x, y = m.y, w = m.w, d = m.d, h = m.h, tp = TIPOS[m.i % 5], pulso = .5 + .5 * Math.sin(t * 5 + m.i);
  var corpo = tp === 'prensa' ? ['#8a98b3', '#6f7f9d', '#5c6c8a'] : tp === 'torno' ? ['#9aa9c2', '#7b8bab', '#677799'] : [COR.acoT, COR.acoL, COR.acoR];
  caixa(x, y, w, d, h, 0, corpo[0], corpo[1], corpo[2]);
  // topo: peças decorativas
  if (tp === 'prensa') { caixa(x + w * .55, y + .15, .5, .5, .5, h, '#d0d9e8', '#a9b7cd', '#8d9cb5'); }
  if (tp === 'cnc') { caixa(x + w - .6, y + .3, .35, .35, .35, h, '#cfd8e6', '#a9b7cd', '#8d9cb5'); }
  if (tp === 'torno') { cilindro(x + w * .7, y + .5, .26, h, .4, '#d0d9e8', '#a9b7cd', '#8d9cb5'); }
  if (tp === 'braco') {
    caixa(x + w * .4, y + .3, .55, .55, .22, h, '#d0d9e8', '#a9b7cd', '#8d9cb5');
    var a0 = pj(x + w * .675, y + .575, h + .22), ang = Math.sin(t * 1.3 + m.i) * .5, L1 = 36 * SC, L2 = 30 * SC, c = G.ctx;
    var a1 = [a0[0] + Math.sin(ang - .5) * L1, a0[1] - Math.cos(ang - .5) * L1], a2 = [a1[0] + Math.sin(ang + .7) * L2, a1[1] - Math.cos(ang + .7) * L2 * .6];
    c.lineCap = 'round'; c.strokeStyle = INK; c.lineWidth = 8 * SC; c.beginPath(); c.moveTo(a0[0], a0[1]); c.lineTo(a1[0], a1[1]); c.lineTo(a2[0], a2[1]); c.stroke();
    c.strokeStyle = COR.laranja; c.lineWidth = 5.5 * SC; c.beginPath(); c.moveTo(a0[0], a0[1]); c.lineTo(a1[0], a1[1]); c.lineTo(a2[0], a2[1]); c.stroke();
    c.fillStyle = INK; c.beginPath(); c.arc(a1[0], a1[1], 4.5 * SC, 0, 6.3); c.fill();
  }
  // face frontal (plano y = y+d)
  sobre('y', y + d, x, 0, function (c) {
    faixaPerigo(c, 0, 0, w, .26);
    // janela
    var jw = w - .4, jh = h * .36, jv = h * .46;
    rc(c, .18, jv - .04, jw + .04, jh + .08, '#e9f0fb'); rc(c, .2, jv, jw, jh, '#1b2a44');
    c.save(); c.beginPath(); c.rect(.2, jv, jw, jh); c.clip();
    if (tp === 'cnc') {
      rc(c, jw * .3, jv + .05, jw * .5, .22, '#aab6c9'); var br = jv + jh * .75 - Math.abs(Math.sin(t * 2.2 + m.i)) * jh * .35;
      rc(c, .2 + jw * .5 - .04, br, .08, jh, '#e0e7f1'); rc(c, .2 + jw * .5 - .08, br - .02, .16, .08, '#e0e7f1');
      if (Math.sin(t * 22 + m.i) > .3) { rc(c, .2 + jw * .5 - .1, jv + .08, .05, .04, COR.amarelo); rc(c, .2 + jw * .5 + .07, jv + .12, .05, .04, COR.ambar); }
    } else if (tp === 'prensa') {
      var pv = jv + jh * .55 + Math.sin(t * 2.4 + m.i) * jh * .18;
      rc(c, .2 + jw * .38, pv, jw * .24, jh, '#9aa8bf'); rc(c, .2 + jw * .3, pv, jw * .4, .14, '#c8d3e3'); rc(c, .2 + jw * .25, jv + .04, jw * .5, .1, '#4b5b7c');
    } else if (tp === 'torno') {
      var cx = .2 + jw * .5, cy = jv + jh * .5, r = Math.min(jw, jh) * .34, a = t * 9;
      disco(c, cx, cy, r, '#8a98b3'); for (var k = 0; k < 3; k++) { lin(c, cx, cy, cx + Math.cos(a + k * 2.09) * r, cy + Math.sin(a + k * 2.09) * r, '#e0e7f1', .05); }
      disco(c, cx, cy, r * .22, INK);
    } else if (tp === 'esteira') {
      rc(c, .2, jv + jh * .3, jw, .12, '#4b5b7c');
      for (var q = 0; q < 4; q++) { var qu = .2 + ((t * .35 + q * .25) % 1) * jw; rc(c, qu - .12, jv + jh * .3 + .12, .26, .24, q % 2 ? '#d0a15a' : '#e5c58a'); }
      for (q = 0; q < 12; q++) rc(c, .2 + ((q / 12 + t * .5) % 1) * jw, jv + jh * .3 - .02, .03, .04, '#cfd8e6');
    } else {
      var ax = .2 + jw * .5; lin(c, ax, jv + jh * .12, ax + Math.sin(t * 1.6 + m.i) * jw * .22, jv + jh * .58, '#f08a3c', .09);
      disco(c, ax + Math.sin(t * 1.6 + m.i) * jw * .22, jv + jh * .58, .08, '#fff');
    }
    c.restore();
    c.fillStyle = 'rgba(255,255,255,.12)'; c.beginPath(); c.moveTo(.2, jv + jh); c.lineTo(.2, jv); c.lineTo(.5, jv); c.lineTo(.2 + .1, jv + jh * .55); c.fill();
    // controles
    var cv = .42; rc(c, .18, cv, jw + .04, .42, '#2d3f60');
    rc(c, .26, cv + .06, .56, .3, '#0f1e36');
    for (var s = 0; s < 6; s++) rc(c, .3 + s * .08, cv + .1 + (.1 + .08 * Math.sin(t * 3 + s + m.i)) * .5, .05, .04 + .06 * Math.abs(Math.sin(t * 3 + s * 1.7 + m.i)), '#5fe0ff');
    disco(c, w - .55, cv + .21, .06, pulso > .5 ? COR.verde : '#1d6b45'); disco(c, w - .38, cv + .21, .06, m.luz === 3 ? COR.verm : '#6b2a2a'); disco(c, w - .21, cv + .21, .06, COR.ambar);
    // placa
    rc(c, .18, h - .4, .98, .28, m.placa ? '#fff' : '#cfd8e6'); rc(c, .18, h - .4, .98, .04, m.luz === 3 ? COR.verm : m.luz === 2 ? COR.ambar : '#8da0bf');
    txtL(c, m.placa || '· · ·', .67, h - .3, .2, m.placa ? '#1e3f9a' : '#7886a3');
  });
  // face lateral (plano x = x+w)
  sobre('x', x + w, y, 0, function (c) {
    rc(c, .12, .5, d - .24, .08, 'rgba(255,255,255,.18)'); rc(c, .12, h - .55, d - .24, .08, 'rgba(0,0,0,.18)');
    for (var s = 0; s < 4; s++) rc(c, .25 + s * .2, h * .35, .1, .5, 'rgba(10,20,45,.35)');
  });
  // torre de sinalização
  var lx = x + .22, ly = y + .22, lz = h + (tp === 'prensa' || tp === 'braco' ? 0 : 0), on = m.luz;
  cilindro(lx, ly, .09, lz, .12, '#3a475f', '#2b364d', '#232d42');
  [[1, COR.verde, '#1b5a3a'], [2, COR.ambar, '#6b4a12'], [3, COR.verm, '#6b1f1f']].forEach(function (l, i) {
    var ligada = on === l[0] && (l[0] !== 3 || pulso > .3);
    cilindro(lx, ly, .09, lz + .12 + i * .14, .14, ligada ? l[1] : l[2], ligada ? l[1] : l[2], ligada ? l[1] : l[2]);
  });
  if (on) {
    var pp = pj(lx, ly, lz + .4), cc = G.ctx, rad = (on === 3 ? 34 : 22) * SC, gg = cc.createRadialGradient(pp[0], pp[1], 1, pp[0], pp[1], rad);
    var col = luzCor(on); gg.addColorStop(0, col + (on === 3 ? 'aa' : '66')); gg.addColorStop(1, col + '00');
    cc.fillStyle = gg; cc.beginPath(); cc.arc(pp[0], pp[1], rad, 0, 6.3); cc.fill();
  }
  // halo no chão quando destacada
  if (m.destaque > 0) {
    var cx2 = x + w / 2, cy2 = y + d + .9, pc = pj(cx2, cy2, 0), c2 = G.ctx, a2 = w * .75 * TW * .7071 * SC, pu = 1 + .06 * Math.sin(t * 6);
    c2.save(); c2.globalAlpha = clamp(m.destaque, 0, 1) * .85; c2.strokeStyle = luzCor(m.luz || 3); c2.lineWidth = 3 * SC; c2.setLineDash([8 * SC, 5 * SC]);
    c2.beginPath(); c2.ellipse(pc[0], pc[1], a2 * pu, a2 * pu / 2, 0, 0, 6.3); c2.stroke(); c2.restore();
  }
}

/* etiqueta flutuante com a classificação (desenhada por cima de tudo) */
function etiqueta(m, t) {
  if (!m.rank || m.mostrar <= 0) return;
  var c = G.ctx, p = pj(m.x + m.w / 2, m.y + m.d / 2, m.h + .95), k = SC, esc = ease(m.mostrar);
  var bob = Math.sin(t * 3 + m.i) * 3 * k, W = 70 * k, H = 40 * k, x = p[0] - W / 2, y = p[1] - H - 8 * k + bob - (1 - esc) * 14 * k;
  c.save(); c.globalAlpha = esc;
  c.fillStyle = 'rgba(10,20,50,.3)'; c.beginPath(); c.roundRect(x + 2 * k, y + 3 * k, W, H, 8 * k); c.fill();
  c.fillStyle = '#fff'; c.strokeStyle = INK; c.lineWidth = 2 * k; c.beginPath(); c.roundRect(x, y, W, H, 8 * k); c.fill(); c.stroke();
  c.fillStyle = '#fff'; c.beginPath(); c.moveTo(p[0] - 6 * k, y + H - 1); c.lineTo(p[0], y + H + 8 * k); c.lineTo(p[0] + 6 * k, y + H - 1); c.fill();
  c.strokeStyle = INK; c.beginPath(); c.moveTo(p[0] - 6 * k, y + H); c.lineTo(p[0], y + H + 8 * k); c.lineTo(p[0] + 6 * k, y + H); c.stroke();
  c.fillStyle = luzCor(m.luz || 3); c.beginPath(); c.arc(x + 13 * k, y + 13 * k, 8.5 * k, 0, 6.3); c.fill(); c.stroke();
  c.fillStyle = '#fff'; c.font = '900 ' + 10.5 * k + 'px Nunito, system-ui, sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('#' + m.rank, x + 13 * k, y + 13.5 * k);
  c.fillStyle = INK; c.textAlign = 'left'; c.font = '900 ' + 11.5 * k + 'px Nunito, system-ui, sans-serif'; c.fillText(m.placa || '', x + 25 * k, y + 13 * k);
  c.font = '800 ' + 10 * k + 'px Nunito, system-ui, sans-serif'; c.fillStyle = '#4a5b7d'; c.fillText(m.peca || '', x + 7 * k, y + 29 * k);
  c.fillStyle = luzCor(m.luz || 3); c.textAlign = 'right'; c.font = '900 ' + 11.5 * k + 'px Nunito, system-ui, sans-serif'; c.fillText(m.prob + '%', x + W - 7 * k, y + 29 * k);
  c.restore();
}

/* ------------------------------------------------------------------ personagens (pixel-art) */
var K = 1, BX = 0, BY = 0;
function R(x, y, w, h, col) { var c = G.ctx; c.fillStyle = col; var X = Math.round(BX + x * K), Y = Math.round(BY + y * K); c.fillRect(X, Y, Math.max(1, Math.round(BX + (x + w) * K) - X), Math.max(1, Math.round(BY + (y + h) * K) - Y)); }
function Ob(x, y, w, h, col, b) { R(x - 1, y - 1, w + 2, h + 2, b || INK); R(x, y, w, h, col); }
function sombra(rx) { var c = G.ctx; c.fillStyle = 'rgba(8,16,45,.3)'; c.beginPath(); c.ellipse(BX, BY, rx * K, rx * .38 * K, 0, 0, 6.3); c.fill(); }
function discoPx(cx, cy, r, col, borda) {
  var i, hw;
  if (borda) for (i = -r - 1; i <= r + 1; i++) { hw = Math.floor(Math.sqrt(Math.max(0, (r + 1) * (r + 1) - i * i)) + .5); R(cx - hw, cy + i, hw * 2, 1, borda); }
  for (i = -r; i <= r; i++) { hw = Math.floor(Math.sqrt(Math.max(0, r * r - i * i)) + .5); R(cx - hw, cy + i, hw * 2, 1, col); }
}
function discoSomb(cx, cy, r, base, luz, sombra_, borda) {
  discoPx(cx, cy, r, base, borda);
  var i, hw, ox = Math.round(r * .3), oy = Math.round(r * .3);
  // sombra (baixo/direita) recortada pelo disco
  for (i = -r; i <= r; i++) {
    hw = Math.floor(Math.sqrt(Math.max(0, r * r - i * i)) + .5);
    var hw2 = Math.floor(Math.sqrt(Math.max(0, (r - 1) * (r - 1) - (i + oy) * (i + oy))) + .5);
    var ini = cx - hw, fim = cx + hw, lx = cx - ox - hw2, rx = cx - ox + hw2;
    if (i + oy > r - 1 || i + oy < -(r - 1)) { R(ini, cy + i, hw * 2, 1, sombra_); continue; }
    if (rx < fim) R(Math.max(ini, rx), cy + i, fim - Math.max(ini, rx), 1, sombra_);
    if (lx > ini) R(ini, cy + i, Math.min(fim, lx) - ini, 1, sombra_);
  }
  // brilho
  R(cx - Math.round(r * .55), cy - Math.round(r * .55), Math.max(2, Math.round(r * .3)), Math.max(1, Math.round(r * .2)), luz);
}

var PELE = '#f0c08a', PELES = '#d79f68', CAMISA = '#6d7f96', CAMISAS = '#586a80', JEANS = '#34507f', CABELO = '#5a3b22', LUVA = '#e8a317';

function pontaBraco(lado, ky, cor, luva, camisa) {
  // braço esticado na horizontal (lado=+1 direita / -1 esquerda) com leve inclinação ky (-1 cima, +1 baixo)
  for (var i = 0; i < 6; i++) {
    var xx = lado > 0 ? 4 + i * 1.7 : -4 - i * 1.7 - 2, yy = -18.5 + i * ky * .8;
    Ob(xx, yy, 2.2, 2.2, i > 3 ? (luva ? LUVA : PELE) : camisa);
  }
}

function operador(a, sx, sy, k) {
  K = k; BX = sx; BY = sy;
  var e = a.eq, d = a.dir, costas = d === 'nw' || d === 'ne', lado = (d === 'se' || d === 'ne') ? 1 : ((d === 'sw' || d === 'nw') ? -1 : 0);
  var s = a.andando ? Math.sin(a.fase) : 0, la = Math.round(s * 2), hy = (!a.andando && Math.sin(a.t * 2.6) > .55) ? 0 : 0;
  var tr = a.pose === 'ocupado' ? -2 : 0; // braços levantados trabalhando
  sombra(8.5);
  // pernas
  var ev = Math.max(la, 0), dv = Math.max(-la, 0);
  Ob(-4.5, -9 + ev, 4, 9 - ev, JEANS); Ob(.5, -9 + dv, 4, 9 - dv, JEANS);
  Ob(-5 + lado * .5, -2 - ev, 5, 2, '#3b2c22'); Ob(0 + lado * .5, -2 - dv, 5, 2, '#3b2c22');
  if (e.botas) { R(-5 + lado * .5, -2 - ev, 5, .8, '#9aa5b5'); R(0 + lado * .5, -2 - dv, 5, .8, '#9aa5b5'); }
  // tronco
  Ob(-5, -20, 10, 11, CAMISA); R(-5, -10, 10, 1, CAMISAS);
  if (e.colete) {
    if (costas) { R(-5, -20, 10, 11, COR.laranja); R(-4, -20, 1.6, 11, '#eef5a8'); R(2.4, -20, 1.6, 11, '#eef5a8'); R(-5, -14, 10, 1.4, '#eef5a8'); }
    else { R(-5, -20, 3.6, 11, COR.laranja); R(1.4, -20, 3.6, 11, COR.laranja); R(-4.2, -20, 1.4, 11, '#eef5a8'); R(2.8, -20, 1.4, 11, '#eef5a8'); R(-5, -14, 3.6, 1.2, '#eef5a8'); R(1.4, -14, 3.6, 1.2, '#eef5a8'); R(-1.4, -20, 2.8, 11, CAMISA); }
  }
  // braços
  var bl = Math.round(-s * 1.6) + tr, br = Math.round(s * 1.6) + tr;
  var ponta = a.pose === 'ponta' ? (a.ponta || 1) : 0, ky = a.ky || 0;
  // braço esquerdo (da tela)
  if (ponta < 0) pontaBraco(-1, ky, 0, e.luvas, CAMISA);
  else { Ob(-7.2, -19 + bl, 2.2, 4, CAMISA); Ob(-7.2, -15 + bl, 2.2, 5, e.luvas ? LUVA : PELE); }
  // braço direito
  if (ponta > 0) pontaBraco(1, ky, 0, e.luvas, CAMISA);
  else if (a.pose === 'aceno') { var ac = Math.round(Math.sin(a.t * 9) * 1.5); Ob(5, -19 - 5, 2.2, 4, CAMISA); Ob(5 + ac, -24 - 6, 2.2, 5, e.luvas ? LUVA : PELE); }
  else { Ob(5, -19 + br, 2.2, 4, CAMISA); Ob(5, -15 + br, 2.2, 5, e.luvas ? LUVA : PELE); }
  // ferramentas
  if (e.caixa && ponta >= 0) {
    var cy = -9 + bl; Ob(-12, cy, 8, 5, '#d83a34'); R(-12, cy, 8, 1.4, '#f2766b'); R(-10, cy - 2, 4, 1, '#8a8f98'); R(-10, cy - 2, 1, 2, '#8a8f98'); R(-7, cy - 2, 1, 2, '#8a8f98'); R(-9, cy + 2, 2, 1, COR.amarelo);
  }
  if (e.ferr && ponta <= 0 && a.pose !== 'aceno') {
    var wy = -11 + br; Ob(6.2, wy - 14, 2, 14, '#c5ced8'); Ob(4.8, wy - 18, 1.8, 5, '#c5ced8'); Ob(8.4, wy - 18, 1.8, 5, '#c5ced8'); R(4.8, wy - 14.4, 5.4, 1.6, '#c5ced8');
  }
  // cabeça
  Ob(-5, -31 + hy, 10, 10, PELE); R(-1.5, -21 + hy, 3, 1.6, PELES);
  if (costas) { R(-5, -31 + hy, 10, 9, CABELO); R(-5, -23 + hy, 10, 2, PELES); }
  else {
    R(-5, -31 + hy, 10, 3, CABELO); R(-5, -28 + hy, 1.4, 3, CABELO); R(3.6, -28 + hy, 1.4, 3, CABELO);
    var ex = lado * 1.2;
    R(-3 + ex, -26.5 + hy, 1.8, 2.2, INK); R(1.4 + ex, -26.5 + hy, 1.8, 2.2, INK); R(-2.6 + ex, -26.5 + hy, .7, .7, '#fff'); R(1.8 + ex, -26.5 + hy, .7, .7, '#fff');
    R(.1 + ex, -24.6 + hy, 1.3, 1.5, PELES);
    if (a.fala) { var ab = Math.abs(Math.sin(a.t * 14)) > .5; R(-1.3 + ex, -22.6 + hy, 2.8, ab ? 1.8 : 1, '#8f3b32'); } else R(-1.2 + ex, -22.4 + hy, 2.6, 1, '#8f3b32');
    if (e.oculos) {
      R(-5.4, -27.5 + hy, 10.8, 1.2, '#1f2937'); var g = G.ctx.globalAlpha; G.ctx.globalAlpha = g * .9;
      R(-4.6 + ex, -28.2 + hy, 3.8, 3.4, '#a6e8ff'); R(.8 + ex, -28.2 + hy, 3.8, 3.4, '#a6e8ff'); G.ctx.globalAlpha = g;
      R(-4.2 + ex, -28 + hy, 1, 1, '#fff'); R(1.2 + ex, -28 + hy, 1, 1, '#fff'); R(-4.6 + ex, -28.4 + hy, 3.8, .6, '#1f2937'); R(.8 + ex, -28.4 + hy, 3.8, .6, '#1f2937');
    }
  }
  if (e.capacete) {
    Ob(-6, -37 + hy, 12, 7, COR.amarelo); R(-1, -38 + hy, 2, 8, '#e5a400'); R(-4.6, -36 + hy, 2.4, 1.2, '#fff0a8');
    Ob(-7.5, -31 + hy, 15, 2.2, '#e5a400'); R(-7.5, -29.8 + hy, 15, .9, '#b37f00');
  }
}

function elipse(cx, cy, rx, ry, col, borda) {
  var i, hw;
  if (borda) for (i = -ry - 1; i <= ry + 1; i++) { hw = Math.round((rx + 1) * Math.sqrt(Math.max(0, 1 - Math.pow(i / (ry + 1), 2)))); R(cx - hw, cy + i, hw * 2, 1, borda); }
  for (i = -ry; i <= ry; i++) { hw = Math.round(rx * Math.sqrt(Math.max(0, 1 - Math.pow(i / ry, 2)))); R(cx - hw, cy + i, hw * 2, 1, col); }
}
function elipSomb(cx, cy, rx, ry, base, luz, somb, borda) {
  elipse(cx, cy, rx, ry, base, borda);
  for (var i = -ry; i <= ry; i++) {
    var hw = Math.round(rx * Math.sqrt(Math.max(0, 1 - Math.pow(i / ry, 2)))), x0 = Math.round(rx * (.55 - .55 * i / ry));
    if (x0 < hw) R(cx + x0, cy + i, hw - x0, 1, somb);
  }
  R(cx - Math.round(rx * .55), cy - Math.round(ry * .62), Math.max(2, Math.round(rx * .3)), 1.2, luz);
}

/* Robô-boneco-de-neve inspirado no Olaf: três bolas, cabelo de galhos, nariz de cenoura, sorriso com dentes, botões e braços de galho. */
function robo(a, sx, sy, k) {
  K = k; BX = sx; BY = sy;
  var costas = a.dir === 'nw' || a.dir === 'ne', lado = (a.dir === 'se' || a.dir === 'ne') ? 1 : ((a.dir === 'sw' || a.dir === 'nw') ? -1 : 0);
  var c = G.ctx, BR = '#fbfdff', SB = '#bfd0e8', LZ = '#ffffff', GL = '#7a4e2a', GLB = '#3f2810', CY = '#5fe0ff';
  var hop = a.andando ? -Math.abs(Math.round(Math.sin(a.fase) * 2)) : Math.round(Math.sin(a.t * 3) * .5) - 1;
  var g = c.createRadialGradient(BX, BY, 1, BX, BY, 12 * K); g.addColorStop(0, 'rgba(95,224,255,.5)'); g.addColorStop(1, 'rgba(95,224,255,0)');
  c.fillStyle = g; c.beginPath(); c.ellipse(BX, BY, 12 * K, 4.4 * K, 0, 0, 6.3); c.fill();
  sombra(9.5);
  var ponta = a.pose === 'ponta' ? (a.ponta || -1) : 0, ky = a.ky || 0, p = a.andando ? Math.round(Math.sin(a.fase) * 1.5) : 0;
  function galho(ls, ang, esticar) {
    var x0 = ls * 6.2, y0 = -21 + hop, n = esticar ? 8 : 5, i, px, py;
    for (i = 0; i < n; i++) { px = x0 + ls * i * 1.6; py = y0 + (esticar ? i * ang : i * 1.0 + ang * i * .3); Ob(px - 1, py - 1, 2, 2, GL, GLB); }
    var ex = x0 + ls * n * 1.6, ey = y0 + (esticar ? n * ang : n * 1.0 + ang * n * .3);
    Ob(ex - 1, ey - 3, 1.4, 3, GL, GLB); Ob(ex + ls * 1.6 - 1, ey - 1.6, 1.4, 3, GL, GLB); Ob(ex + ls * .2 - .7, ey + 1, 1.4, 2.6, GL, GLB);
  }
  var costasArm = function () { galho(-1, 1.2 + Math.sin(a.fase) * .4, false); galho(1, 1.2 - Math.sin(a.fase) * .4, false); };
  if (costas) costasArm();
  // pés
  elipse(-4, -1.6 - Math.max(p, 0), 3.4, 1.8, BR, INK); elipse(4, -1.6 - Math.max(-p, 0), 3.4, 1.8, BR, INK);
  // corpo
  elipSomb(0, -9 + hop, 9, 7, BR, LZ, SB, INK);
  elipSomb(0, -21 + hop, 7, 6, BR, LZ, SB, INK);
  if (!costas) { for (var i = 0; i < 3; i++) { R(-1.2, -24.4 + hop + i * 3.4, 2.6, 2.6, '#16161f'); R(-.8, -24.2 + hop + i * 3.4, .9, .9, '#6d6d86'); } }
  else { R(-1.2, -22 + hop, 2.4, 1.2, CY); }
  if (!costas) {
    if (a.pose === 'aceno') galho(1, -1.6, true); else galho(1, ponta > 0 ? ky * .9 : 1.5 + Math.sin(a.fase) * .4, ponta > 0);
    galho(-1, ponta < 0 ? ky * .9 : 1.5 - Math.sin(a.fase) * .4, ponta < 0);
  } else { if (ponta > 0) galho(1, ky, true); if (ponta < 0) galho(-1, ky, true); }
  // cabeça
  elipSomb(0, -35 + hop, 8.5, 7.2, BR, LZ, SB, INK);
  R(-10.6, -36.5 + hop, 1.6, 2.8, CY); R(9, -36.5 + hop, 1.6, 2.8, CY); // parafusos de robô
  // cabelo de galhos
  Ob(-3, -46.5 + hop, 1, 4, GL, GLB); Ob(.2, -48.5 + hop, 1, 6, GL, GLB); Ob(3.2, -46.5 + hop, 1, 4, GL, GLB);
  if (!costas) {
    var ex = lado * 1.3;
    elipse(-3.2 + ex, -37 + hop, 2.3, 2.7, '#fff', INK); elipse(3.2 + ex, -37 + hop, 2.3, 2.7, '#fff', INK);
    var pisca = Math.sin(a.t * .9 + 1) > .965;
    if (pisca) { R(-5.2 + ex, -37 + hop, 4, 1, INK); R(1.2 + ex, -37 + hop, 4, 1, INK); }
    else { R(-3.8 + ex, -36.4 + hop, 1.8, 2.2, '#10101a'); R(2.6 + ex, -36.4 + hop, 1.8, 2.2, '#10101a'); R(-3.6 + ex, -36.2 + hop, .7, .7, '#fff'); R(2.8 + ex, -36.2 + hop, .7, .7, '#fff'); }
    R(-5.8 + ex, -41.4 + hop, 3.6, 1, INK); R(2.2 + ex, -41.9 + hop, 3.6, 1, INK);
    // nariz de cenoura
    Ob(-1.3 + ex, -34.2 + hop, 2.8, 2, '#ff8a1f', '#7a3600'); Ob(-.9 + ex, -32.4 + hop, 2, 1.8, '#ff8a1f', '#7a3600'); R(-.5 + ex, -31 + hop, 1.1, 1.2, '#d96a00');
    // sorriso com dentes
    var ab = a.fala ? 1 + Math.abs(Math.sin(a.t * 12)) * 1.6 : 1.2;
    R(-4.8 + ex, -30.6 + hop, 9.6, 1, INK); R(-3.8 + ex, -29.6 + hop, 7.6, ab + .6, INK); R(-2 + ex, -29.6 + hop, 1.7, 1.3, '#fff'); R(.3 + ex, -29.6 + hop, 1.7, 1.3, '#fff');
    R(-1.6 + ex, -28.3 + hop + (ab > 1.5 ? .4 : 0), 3.2, 1, '#e8697d');
    G.ctx.globalAlpha *= .75; R(-7.2 + ex, -32 + hop, 2, 1.4, '#ff8fa3'); R(5.2 + ex, -32 + hop, 2, 1.4, '#ff8fa3'); G.ctx.globalAlpha /= .75;
  }
  for (var f = 0; f < 3; f++) { var ft = (a.t * .7 + f * .33) % 1; R(-11 + f * 11 + Math.sin(ft * 6 + f) * 2, -52 + ft * 22, 1, 1, 'rgba(255,255,255,' + (1 - ft) + ')'); }
}

/* ------------------------------------------------------------------ fábrica por fora (fundo do login e abertura da cena) */
var FORA_W = 15, FORA_D = 12;
function layoutFora(vw, vh) {
  SC = Math.max(vw / 1150, vh / 780); PXS = PX0 * SC; G.vw = vw; G.vh = vh;
  OX = vw / 2 - (FORA_W - FORA_D) * TW / 4 * SC; OY = vh * .56 - 140 * SC;
}
function arvore(x, y, r) {
  var c = G.ctx, p = pj(x, y, 0), s = SC;
  c.fillStyle = 'rgba(20,50,30,.22)'; c.beginPath(); c.ellipse(p[0], p[1], r * 30 * s, r * 11 * s, 0, 0, 6.3); c.fill();
  c.fillStyle = '#6b4a2e'; c.fillRect(p[0] - 3 * s, p[1] - 26 * s * r, 6 * s, 26 * s * r);
  [['#3f9a58', 0, -38, 24], ['#56b56e', -5, -46, 17], ['#7fd18b', 5, -52, 11]].forEach(function (q) { c.fillStyle = q[0]; c.beginPath(); c.arc(p[0] + q[1] * s * r, p[1] + q[2] * s * r, q[3] * s * r, 0, 6.3); c.fill(); });
}
function nuvem(x, y, e, a) {
  var c = G.ctx; c.fillStyle = 'rgba(255,255,255,' + a + ')';
  [[0, 0, 34], [30, 6, 26], [-30, 8, 24], [58, 12, 18], [-56, 12, 16]].forEach(function (q) { c.beginPath(); c.arc(x + q[0] * e, y + q[1] * e, q[2] * e, 0, 6.3); c.fill(); });
}
function desenharFora(c, vw, vh, t, zoom) {
  var s0 = [OX, OY, SC, PXS, G.vw, G.vh, G.ctx], i, g;
  G.ctx = c; layoutFora(vw, vh);
  var door = pj(5.65, 7.5, 1.25);
  g = c.createLinearGradient(0, 0, 0, vh); g.addColorStop(0, '#3f86e6'); g.addColorStop(.55, '#8fc6f6'); g.addColorStop(1, '#e6f5ff');
  c.fillStyle = g; c.fillRect(0, 0, vw, vh);
  var dx = (t * 6) % (vw + 300);
  nuvem(vw * .12 + dx * .3, vh * .16, SC * .8, .9); nuvem(vw * .72 - dx * .2, vh * .1, SC * .9, .85); nuvem(vw * .45 + dx * .1, vh * .84, SC * 1.1, .8); nuvem(vw * .92 - dx * .25, vh * .78, SC * .8, .8); nuvem(vw * .06 - dx * .1, vh * .7, SC * .7, .75);
  c.save();
  if (zoom && zoom > 1) { c.translate(door[0], door[1]); c.scale(zoom, zoom); c.translate(-door[0], -door[1]); }
  var W = FORA_W, D = FORA_D, h;
  poly([pj(W, 0, 0), pj(W, D, 0), pj(W, D, -1.1), pj(W, 0, -1.1)], '#7c5b43', 'rgba(20,20,40,.5)', 1);
  poly([pj(0, D, 0), pj(W, D, 0), pj(W, D, -1.1), pj(0, D, -1.1)], '#9b7557', 'rgba(20,20,40,.5)', 1);
  for (i = 0; i < W; i++) for (h = 0; h < D; h++) poly([pj(i, h, 0), pj(i + 1, h, 0), pj(i + 1, h + 1, 0), pj(i, h + 1, 0)], (i + h) % 2 ? '#86cc8b' : '#7ec484');
  poly([pj(1.2, 7.6, 0), pj(13.8, 7.6, 0), pj(13.8, 9.3, 0), pj(1.2, 9.3, 0)], '#d9dfe9');
  poly([pj(0, 9.7, 0), pj(W, 9.7, 0), pj(W, 11.6, 0), pj(0, 11.6, 0)], '#5b647c');
  for (i = 0; i < 14; i++) poly([pj(.4 + i, 10.6, 0), pj(1.1 + i, 10.6, 0), pj(1.1 + i, 10.72, 0), pj(.4 + i, 10.72, 0)], '#eef1f7');
  arvore(1.2, 1.4, 1); arvore(13.6, 1.2, 1.1); arvore(.8, 5.6, .9); arvore(14.2, 5.2, 1);
  // prédio
  caixa(2.5, 2, 9, 5.5, 4.2, 0, '#f3f6fc', '#dbe5f4', '#c1d0e6');
  for (i = 0; i < 4; i++) {
    caixa(2.5 + i * 2.25, 2.4, 2.25, 4.7, .9, 4.2, '#a9b9d4', '#e3edf9', '#c0cfe6');
    sobre('y', 7.1, 2.5 + i * 2.25, 4.2, function (cc) { rc(cc, .12, .12, 2.0, .6, '#9fd3ff'); rc(cc, .12, .12, 2.0, .08, '#f3f9ff'); });
  }
  cilindro(10.2, 3.2, .45, 5.1, 2.4, '#c6563e', '#c6563e', '#8f3f2c'); cilindro(10.2, 3.2, .47, 7.2, .3, '#f4efe6', '#e7dfd0', '#cfc6b3');
  cilindro(8.9, 3.6, .38, 5.1, 1.8, '#c6563e', '#c6563e', '#8f3f2c'); cilindro(8.9, 3.6, .4, 6.6, .25, '#f4efe6', '#e7dfd0', '#cfc6b3');
  sobre('y', 7.5, 2.5, 0, function (cc) {
    rc(cc, 0, 0, 9, .45, '#8aa0c4'); rc(cc, 0, .45, 9, .08, '#fff');
    [[.5, 1.8], [2.4, 3.7], [6.9, 8.4]].forEach(function (j) { rc(cc, j[0] - .06, 1.28, j[1] - j[0] + .12, 1.34, '#fff'); rc(cc, j[0], 1.34, j[1] - j[0], 1.22, '#8cc7f5'); rc(cc, (j[0] + j[1]) / 2 - .03, 1.34, .06, 1.22, '#fff'); });
    rc(cc, 2.6, 3.0, 4.0, 1.0, '#1e3f9a'); rc(cc, 2.6, 3.0, 4.0, .07, '#ffc21a'); rc(cc, 2.6, 3.93, 4.0, .07, '#ffc21a'); txtL(cc, 'MABIYAMA', 4.6, 3.38, .5, '#fff');
    rc(cc, 2.35, 0, 1.7, 2.7, '#202b4a'); rc(cc, 2.45, 0, 1.5, 2.6, '#ffd98a');
    var gd = cc.createLinearGradient(0, 0, 0, 2.6); gd.addColorStop(0, '#fffbe8'); gd.addColorStop(1, '#ffc866'); rc(cc, 2.45, 0, 1.5, 2.6, gd);
    rc(cc, 2.35, 2.72, 1.7, .26, '#1f9d62'); txtL(cc, 'ENTRADA', 3.2, 2.78, .17, '#fff');
    faixaPerigo(cc, 2.35, 0, 1.7, .14);
  });
  sobre('x', 11.5, 2, 0, function (cc) {
    rc(cc, 0, 0, 5.5, .45, '#8aa0c4');
    [[.7, 2.0], [2.6, 3.9]].forEach(function (j) { rc(cc, j[0] - .06, 1.28, j[1] - j[0] + .12, 1.34, '#fff'); rc(cc, j[0], 1.34, j[1] - j[0], 1.22, '#6fb3ec'); });
    rc(cc, 4.2, 0, 1.1, 2.2, '#8a98b3'); for (var l = 0; l < 6; l++) rc(cc, 4.2, .2 + l * .35, 1.1, .05, '#6c7a96');
  });
  arvore(1.4, 9.0, 1.15); arvore(13.2, 8.8, 1.05);
  // lampadas
  [[1.5, 7.9], [13.4, 7.9]].forEach(function (q) { var p0 = pj(q[0], q[1], 0), p1 = pj(q[0], q[1], 2.6); c.strokeStyle = '#4a5775'; c.lineWidth = 3 * SC; c.beginPath(); c.moveTo(p0[0], p0[1]); c.lineTo(p1[0], p1[1]); c.stroke(); c.fillStyle = '#ffe9a3'; c.beginPath(); c.arc(p1[0], p1[1], 5 * SC, 0, 6.3); c.fill(); });
  // fumaça
  [[10.2, 3.2, 7.5], [8.9, 3.6, 6.9]].forEach(function (q, n) {
    var b = pj(q[0], q[1], q[2]);
    for (i = 0; i < 6; i++) { var ph = (t * .22 + i / 6 + n * .3) % 1; c.fillStyle = 'rgba(255,255,255,' + (.7 * (1 - ph)) + ')'; c.beginPath(); c.arc(b[0] - ph * 34 * SC, b[1] - ph * 95 * SC, (7 + ph * 20) * SC, 0, 6.3); c.fill(); }
  });
  c.restore();
  OX = s0[0]; OY = s0[1]; SC = s0[2]; PXS = s0[3]; G.vw = s0[4]; G.vh = s0[5]; G.ctx = s0[6];
  return door;
}

function alturaOp() { return 38; }
function alturaRb() { return 54; }
