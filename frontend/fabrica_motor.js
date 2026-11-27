/* MaBiYama · animação de boas-vindas (motor): roteiro, balões, rolagem e ajudantes. Fragmento embutido por animacao.py. */
var VERSAO = '@@VERSAO@@', FORA = 3.6;
var Wn = window, D = document, PULOU = { pulou: true }, RB_ESC = .82;
var CSS = '@@CSS@@';

var S = { ordem: 0, foraT: 99, ritmo: 1, gutOn: null, bolhaEtapa: 0, pronto: false, tok: null, modo: 'oculto', aba: null, cfg: null, pular: false, pend: [], t: 0, ocultar: false, tr: 0, bolhas: [], travado: false,
  ultScroll: 0, ultMedida: 0, ultResolve: 0, rolou: false, dicaAte: 0, fase: 0,
  esperando: false, prontoDesde: 0, esperaIni: 0, persoN: null,
  bl: -1, cand: -2, candDesde: 0, rects: [], vistos: {}, dlg: null, dlgId: 0, dlgPend: false, fechado: null, ptr: null, porMouse: false, reduzir: false };
var E = { t: 0, porta: 0, armario: { aberto: false, itens: { cap: true, oc: true, col: true, lu: true } }, banca: { ferr: true, caixa: true }, maq: [] };
var op, rb, elFoco, cv, ctx, fundoCv, raiz, elBolhas, elDica, elPular, elTg, elTopo, raf = 0, ultimo = 0, ouv = [];

function novoAtor(tipo, nome) {
  return { tipo: tipo, nome: nome, x: 0, y: 0, dir: 'se', andando: false, fase: 0, t: Math.random() * 9, eq: {}, pose: '', fala: false, vis: 0, caminho: [], vel: 2.6,
    fim: null, tela: false, sx: 0, sy: 0, k: 1, ponta: 0, ky: 0, alvoY: 0 };
}
function resetCena() {
  E.porta = 0; E.armario = { aberto: false, itens: { cap: true, oc: true, col: true, lu: true } }; E.banca = { ferr: true, caixa: true };
  E.maq = [0, 1, 2, 3, 4].map(function (i) { return { i: i, x: 1.7 + i * 2.15, y: .25, w: 1.75, d: 1.3, h: [2.9, 3.2, 2.7, 3.1, 2.9][i], luz: 1, placa: '', rank: 0, prob: 0, peca: '', mostrar: 0, alvoMostrar: 0, destaque: 0 }; });
  op = novoAtor('op', 'Beto'); rb = novoAtor('rb', 'Floco'); aplicarPerso(op);
}

/* ------------------------------------------------------------------ DOM */
function criarDOM() {
  if (D.getElementById('mby')) D.getElementById('mby').remove();
  var st = D.getElementById('mby-css'); if (st) st.remove();
  st = D.createElement('style'); st.id = 'mby-css'; st.textContent = CSS; D.head.appendChild(st);
  raiz = D.createElement('div'); raiz.id = 'mby';
  raiz.innerHTML = '<canvas></canvas><div class="mby-foco"></div><div class="mby-bolhas"></div><div class="mby-topo"></div>' +
    '<div class="mby-dica" aria-hidden="true"><span>Role a página</span><i></i></div>' +
    '<button type="button" class="mby-pular">Pular animação <b>»</b></button><div class="mby-acoes"><button type="button" class="mby-pz-abrir" title="Mudar nome, aparência, roupas e EPIs">Personalizar</button><button type="button" class="mby-tg">Ocultar ajudantes</button></div>';
  D.body.appendChild(raiz);
  cv = raiz.querySelector('canvas'); ctx = cv.getContext('2d'); G.ctx = ctx;
  elBolhas = raiz.querySelector('.mby-bolhas'); elDica = raiz.querySelector('.mby-dica'); elPular = raiz.querySelector('.mby-pular');
  elTg = raiz.querySelector('.mby-tg'); elFoco = raiz.querySelector('.mby-foco'); elTopo = raiz.querySelector('.mby-topo');
  elPular.addEventListener('click', pularTudo);
  raiz.querySelector('.mby-pz-abrir').addEventListener('click', function () { abrirPerso(); });
  elTg.addEventListener('click', function () { S.ocultar = !S.ocultar; try { localStorage.setItem('mby_ocultar', S.ocultar ? '1' : '0'); } catch (e) { } rotuloTg(); });
  try { S.ocultar = localStorage.getItem('mby_ocultar') === '1'; } catch (e) { }
  rotuloTg();
}
function rotuloTg() { if (elTg) elTg.textContent = S.ocultar ? 'Mostrar ajudantes' : 'Ocultar ajudantes'; }
function ouvir(alvo, ev, fn, opt) { alvo.addEventListener(ev, fn, opt); ouv.push([alvo, ev, fn, opt]); }

function ajustar() {
  var vw = Wn.innerWidth, vh = Wn.innerHeight, dpr = Math.min(2, Wn.devicePixelRatio || 1);
  G.dpr = dpr; cv.width = Math.round(vw * dpr); cv.height = Math.round(vh * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  layout(vw, vh);
  if (S.modo === 'login') assarFundoLogin();
  fundoCv = D.createElement('canvas'); fundoCv.width = cv.width; fundoCv.height = cv.height;
  var fc = fundoCv.getContext('2d'); fc.setTransform(dpr, 0, 0, dpr, 0, 0);
  var tmp = G.ctx; G.ctx = fc; desenharFundo(fc); G.ctx = tmp;
}

/* ------------------------------------------------------------------ controle de rolagem */
function principal() { return D.querySelector('[data-testid="stMain"]') || D.querySelector('section.main') || D.querySelector('[data-testid="stAppViewContainer"]'); }
function travarRolagem(v) {
  S.travado = v; var m = principal();
  if (m) { m.style.overflow = v ? 'hidden' : ''; if (v) m.scrollTop = 0; }
  raiz.classList.toggle('travado', v); D.body.classList.toggle('mby-travado', v);
}
function teclas(e) { if (S.travado && [32, 33, 34, 35, 36, 37, 38, 39, 40].indexOf(e.keyCode) >= 0) { var t = e.target; if (!t || !/input|textarea|select/i.test(t.tagName)) e.preventDefault(); } if (S.travado && e.key === 'Escape') pularTudo(); }
function noScroll() { S.ultScroll = performance.now(); var m = principal(); if (m && m.scrollTop > 60) S.rolou = true; }

/* ------------------------------------------------------------------ roteiro */
function chk() { if (S.pular) throw PULOU; }
function esp(ms) { return new Promise(function (res) { var h = setTimeout(res, ms / S.ritmo); S.pend.push(function () { clearTimeout(h); res(); }); }).then(chk); }
function andar(a, pts, vel) { return new Promise(function (res) { a.caminho = pts.slice(); a.vel = (vel || 2.5) * S.ritmo; a.fim = res; if (!pts.length) res(); }).then(chk); }
function olhar(a, d) { a.dir = d; }

function criarBolha(a, lado) {
  var el = D.createElement('div'); el.className = 'mby-b ' + a.tipo + ' t-' + (lado || 'cima');
  el.innerHTML = '<span class="mby-n">' + a.nome + '</span><div class="mby-t"></div>'; elBolhas.appendChild(el);
  var b = { el: el, t: el.querySelector('.mby-t'), a: a, lado: lado || 'cima', morta: false, ordem: ++S.ordem, cy: null };
  if (b.lado !== 'cima') S.bolhas.slice().forEach(function (x) { if (x !== b && x.lado !== 'cima') matarBolha(x); });
  S.bolhas.push(b); requestAnimationFrame(function () { el.classList.add('on'); }); return b;
}
function matarBolha(b) {
  if (b.morta) return; b.morta = true; b.a.fala = false; b.el.classList.remove('on');
  setTimeout(function () { b.el.remove(); S.bolhas = S.bolhas.filter(function (x) { return x !== b; }); }, 320);
}
function limparBolhas(a) { S.bolhas.slice().forEach(function (b) { if (!a || b.a === a) matarBolha(b); }); }
function escrever(b, txt, v) {
  return new Promise(function (res) {
    var i = 0; b.a.fala = true;
    (function passo() {
      if (S.pular || b.morta) { b.t.textContent = txt; b.a.fala = false; return res(); }
      i++; b.t.textContent = txt.slice(0, i);
      if (i >= txt.length) { b.a.fala = false; return res(); }
      setTimeout(passo, (v || 24) / S.ritmo);
    })();
  }).then(chk);
}
/* balão estilo Habbo: nasce sobre o personagem, empurra os anteriores para cima e some depois de alguns segundos */
function fala(a, txt, pausa, vida, vel) {
  var b = criarBolha(a, 'cima');
  return escrever(b, txt, vel).then(function () { setTimeout(function () { matarBolha(b); }, (vida || 4800) / S.ritmo); return esp(pausa || 600); }).then(function () { return b; });
}
function aviso(a, txt) {
  var el = D.createElement('div'); el.className = 'mby-toast'; el.textContent = txt; elBolhas.appendChild(el);
  var p = posCab(a); el.style.left = p[0] + 'px'; el.style.top = (p[1] - 8) + 'px'; setTimeout(function () { el.remove(); }, 1700);
}
function posCab(a) {
  var alt = (a.tipo === 'op' ? 38 : 49 * RB_ESC);
  if (a.tela) return [a.sx, a.sy - alt * a.k];
  var p = pj(a.x, a.y, 0); return [p[0], p[1] - alt * PXS];
}

function saudacao() { var h = new Date().getHours(); return h < 12 ? 'Bom dia' : h < 18 ? 'Boa tarde' : 'Boa noite'; }
function corProb(p) { return p > 60 ? 3 : p > 40 ? 2 : 1; }

function revelar(i) {
  var t = S.cfg.top5[i], m = E.maq[i]; if (!t) return;
  m.placa = t.machine; m.rank = i + 1; m.prob = t.prob; m.peca = t.comp; m.luz = corProb(t.prob); m.alvoMostrar = 1;
}
function destacar(i) { E.maq.forEach(function (m, j) { m.destaque = j === i ? 1 : 0; }); }

function esperarFora() {
  return new Promise(function (res) {
    var iv = setInterval(function () { if (S.foraT >= FORA || S.pular) { clearInterval(iv); res(); } }, 60);
    S.pend.push(function () { clearInterval(iv); res(); });
  }).then(chk);
}

async function roteiro() {
  var cfg = S.cfg, nome = (cfg.nome || '').split(' ')[0], t5 = cfg.top5 || [];
  try {
    await esperarFora();
    elTopo.innerHTML = '<b>MaBiYama</b> · turno da manutenção' + (nome ? '<br><span>' + saudacao() + ', ' + nome + '!</span>' : '');
    elTopo.classList.add('on');
    await esp(500);
    // 1. o operário chega
    E.porta = 1; await esp(500);
    op.x = .35; op.y = 4.95; op.dir = 'se'; op.vis = 1;
    await andar(op, [[1.7, 4.95]]); E.porta = 0;
    await fala(op, saudacao() + '! Mais um dia na fábrica.', 300, 2600);
    // 2. armário: equipamentos
    await andar(op, [[1.7, 2.35]]); olhar(op, 'nw'); op.pose = 'ocupado'; E.armario.aberto = true; await esp(600);
    var eq = [['cap', 'capacete', 'Capacete de segurança'], ['col', 'colete', 'Colete refletivo'], ['lu', 'luvas', 'Luvas de proteção'], ['oc', 'oculos', 'Óculos de proteção']];
    for (var i = 0; i < eq.length; i++) { E.armario.itens[eq[i][0]] = false; op.eq[eq[i][1]] = true; aviso(op, '+ ' + eq[i][2]); await esp(640); }
    E.armario.aberto = false; op.pose = ''; await esp(300);
    // 3. bancada: ferramentas
    await andar(op, [[1.7, 7.4]]); olhar(op, 'nw'); op.pose = 'ocupado'; await esp(500);
    E.banca.ferr = false; op.eq.ferr = true; aviso(op, '+ Chave inglesa'); await esp(700);
    E.banca.caixa = false; op.eq.caixa = true; aviso(op, '+ Caixa de ferramentas'); await esp(800); op.pose = '';
    // 4. frente das máquinas: a pergunta
    await andar(op, [[3.6, 7.4], [3.6, 3.9]]); olhar(op, 'ne'); await esp(800);
    olhar(op, 's'); await esp(350);
    await fala(op, 'E agora? Em qual máquina devo fazer manutenção primeiro?', 1400, 9000, 30);
    // 5. o robô chega e responde, balão por balão, subindo
    E.porta = 1; await esp(450);
    rb.x = .35; rb.y = 4.95; rb.dir = 'se'; rb.vis = 1;
    await andar(rb, [[5.4, 4.95], [5.4, 3.9]], 2.7); E.porta = 0; olhar(rb, 's');
    await esp(300);
    await fala(rb, 'Bip-bop! Eu sou o Floco, o modelo de previsão. Todo dia às 05:00 eu calculo o risco de falha de ' + (cfg.pares || 'todas as') + ' peças da frota.', 450, 9000, 16);
    await fala(rb, 'Estas são as ' + t5.length + ' em que eu vejo mais risco' + (cfg.dia ? ' até 06:00 de ' + cfg.dia : '') + ':', 450, 9000, 16);
    for (var r = 0; r < t5.length; r++) {
      var t = t5[r]; revelar(r); destacar(r);
      await fala(rb, '#' + (r + 1) + ' · ' + t.machine + ' · ' + t.comp + ' · ' + t.prob + '%', 350, 7500, 14);
    }
    destacar(-1);
    if (t5.length) await fala(rb, 'Comece pela ' + t5[0].machine + '! Agora role a página: eu vou do seu lado e explico cada parte do painel.', 500, 6000, 16);
    olhar(op, 'se'); await fala(op, 'Combinado, Floco! Pode ir explicando.', 300, 3800, 22);
    await esp(1600);
  } catch (e) { if (e !== PULOU) { try { console.error(e); } catch (x) { } } }
  limparBolhas(); await finalizar();
}

function estadoFinal() {
  var cfg = S.cfg;
  E.porta = 0; E.armario.aberto = false; E.armario.itens = { cap: false, oc: false, col: false, lu: false }; E.banca.ferr = false; E.banca.caixa = false;
  op.eq = { capacete: true, colete: true, luvas: true, oculos: true, ferr: true, caixa: true }; op.pose = ''; op.vis = 1; op.caminho = []; op.andando = false;
  rb.vis = 1; rb.caminho = []; rb.andando = false; rb.pose = '';
  op.x = 3.6; op.y = 3.9; rb.x = 5.4; rb.y = 3.9;
  op.dir = 's'; rb.dir = 's';
  (cfg.top5 || []).forEach(function (t, i) { revelar(i); }); E.maq.forEach(function (m) { m.destaque = 0; });
}

async function finalizar() {
  var rapido = S.pular; S.pular = false;
  estadoFinal();
  if (rapido) await new Promise(function (r) { setTimeout(r, 150); });
  elTopo.classList.remove('on');
  await paraCompanhia(rapido ? 900 : 1700);
}

function pularTudo() {
  if (S.modo !== 'intro') return;
  if (S.esperando) { S.esperando = false; tirarCapa(); S.pular = true; roteiro(); return; }
  S.pular = true; S.foraT = FORA; S.pend.splice(0).forEach(function (f) { f(); });
  [op, rb].forEach(function (a) { var f = a.fim; a.caminho = []; a.fim = null; if (f) f(); });
}

/* ------------------------------------------------------------------ transição e companhia
   Na companhia, Beto e Floco ficam juntos numa faixa à direita do conteúdo (GUT px). O Floco (o modelo) fica do lado do
   conteúdo e aponta para o bloco; o Beto fica por fora, pergunta, e o Floco explica num balão de diálogo embaixo. */
var GUT = 150;
function areaMain() {
  var x0 = 0, x1 = Wn.innerWidth, sb = D.querySelector('[data-testid="stSidebar"]'), mn = principal();
  if (sb) { var r = sb.getBoundingClientRect(); if (r.width > 40 && r.right > 40 && r.left > -5) x0 = r.right; }
  if (mn) { var rm = mn.getBoundingClientRect(); x1 = rm.left + mn.clientWidth; if (rm.left > x0) x0 = rm.left; }
  return { x0: x0, x1: x1 };
}
function kComp() { return clamp(GUT / 80, 1.4, 1.9); }
function cabeNaTela() { var A = areaMain(); return A.x1 - A.x0 >= 760; }
function gutter(on) { D.body.classList.toggle('mby-gut', !!on); D.body.style.setProperty('--mby-g', GUT + 'px'); }
function gutAtual() { return D.body.classList.contains('mby-gut') ? GUT : 0; }

function paraCompanhia(ms) {
  return new Promise(function (res) {
    var kc = kComp(), A = areaMain();
    [op, rb].forEach(function (a) {
      var p = pj(a.x, a.y, 0); a.tela = true; a.sx = p[0]; a.sy = p[1]; a.k = PXS; a.vis = 1; a.caminho = [];
      a.dir = 's'; a.ini = { x: p[0], y: p[1], k: PXS }; a.alvoY = 0;
    });
    S.modo = 'transicao'; S.tr = 0; var t0 = performance.now(); ms = ms || 1700;
    travarRolagem(false); raiz.classList.remove('travado'); S.rolou = false; gutter(cabeNaTela() && S.cfg.aba !== 'perfil');
    elPular.style.display = 'none';
    (function passo() {
      S.tr = clamp((performance.now() - t0) / ms, 0, 1);
      var e = ease(S.tr); A = areaMain(); kc = kComp();
      [op, rb].forEach(function (a) {
        var alvo = alvoCompanhia(a, kc, A), nx = lerp(a.ini.x, alvo[0], e), ny = lerp(a.ini.y, alvo[1], e);
        a.andando = S.tr < 1; a.dir = (alvo[0] < a.ini.x) ? 'sw' : 'se'; if (Math.abs(alvo[0] - a.ini.x) < 8) a.dir = 's';
        a.sx = nx; a.sy = ny; a.k = lerp(a.ini.k, kc, e); a.fase += .22;
      });
      if (S.tr < 1) return requestAnimationFrame(passo);
      S.modo = 'companhia'; S.dicaAte = performance.now() + 9000; zerarBloco();
      [op, rb].forEach(function (a) { a.andando = false; a.sy = alvoCompanhia(a, kc, areaMain())[1]; a.alvoY = a.sy; a.dir = 'sw'; });
      res();
    })();
  });
}
/* Floco por dentro (perto do conteúdo), Beto por fora, os dois na mesma altura */
function xCompanhia(a, A) { return a.tipo === 'rb' ? A.x1 - GUT * .66 : A.x1 - GUT * .24; }
function alvoCompanhia(a, kc, A) {
  var y = a.alvoY || Wn.innerHeight * .74;
  return [xCompanhia(a, A), clamp(y, 60 * kc + 24, Wn.innerHeight - 22)];
}

function iniciarCompanhia() {
  var kc = kComp(), A = areaMain();
  resetCena(); estadoFinal();
  [op, rb].forEach(function (a) { var al = alvoCompanhia(a, kc, A); a.tela = true; a.sx = al[0]; a.sy = al[1]; a.k = kc; a.dir = 'sw'; a.vis = 0; });
  sairLogin(); S.modo = 'companhia'; zerarBloco(); S.vistos = {}; S.dicaAte = 0; S.gutOn = null;
  elPular.style.display = 'none'; elTopo.classList.remove('on'); travarRolagem(false);
}

/* ------------------------------------------------------------------ achar os blocos na página (documento + iframes) */
var SEL_TXT = 'h1,h2,h3,h4,p,span,dt,strong,label,div.l,div.r';
var SEL_IFR = '.card-canvas,.xg-card,.xp-card,.sm-card,.sm-hero,.sm-kpis,article,section';
var SEL_PAI = '.cartoes,[data-testid="stTabs"],[data-testid="stExpander"]';
var FORA_DO_CONTEUDO = '[data-testid="stSidebar"],#mby,.st-key-cab,.mby-capa,[data-testid="stHeader"]';

function listaDocs() {
  var arr = [{ doc: D, ifr: null }], fs = D.querySelectorAll('iframe');
  for (var i = 0; i < fs.length; i++) {
    try { var d = fs[i].contentDocument; if (d && d.body && d.getElementById('root')) { arr.push({ doc: d, ifr: fs[i] }); escutarDoc(d, fs[i]); } } catch (e) { }
  }
  return arr;
}
function visivelEl(el) { return !!(el && el.isConnected && el.getClientRects().length); }
function textos(doc, pai) {
  var els = doc.querySelectorAll(SEL_TXT), out = [];
  for (var i = 0; i < els.length; i++) {
    var el = els[i];
    if (pai && el.closest(FORA_DO_CONTEUDO)) continue;
    var s = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (s && s.length <= 160) out.push([s.toLowerCase(), el]);
  }
  return out;
}
function resolver() {
  var bls = (S.cfg && S.cfg.blocos) || [], agora = performance.now();
  var falta = bls.some(function (b) { return !visivelEl(b._el); });
  if (!falta || agora - S.ultResolve < 450) return;
  S.ultResolve = agora;
  var docs = listaDocs(), cache = docs.map(function (d) { return textos(d.doc, !d.ifr); });
  bls.forEach(function (b) {
    if (visivelEl(b._el)) return;
    b._el = null; b._cont = null;
    var ex = b.alvo.charAt(0) === '=', t = (ex ? b.alvo.slice(1) : b.alvo).toLowerCase().replace(/\s+/g, ' ');
    for (var i = docs.length - 1; i >= 0 && !b._el; i--) {
      var c = cache[i];
      for (var j = 0; j < c.length; j++) {
        if ((ex ? c[j][0] === t : c[j][0].indexOf(t) === 0) && visivelEl(c[j][1])) { b._el = c[j][1]; b._ifr = docs[i].ifr; break; }
      }
    }
  });
}
function contDe(b) {
  if (b._cont && b._cont.isConnected && b._contDe === b._el) return b._cont;
  var el = b._el, c = null;
  if (b.cont) c = el.closest(b.cont);
  if (!c) c = el.closest(b._ifr ? SEL_IFR : SEL_PAI);
  var m = principal();
  if (c && !b._ifr && m && (c === m || c.contains(m))) c = null;
  b._cont = c; b._contDe = el; return c;
}
/* retângulo do bloco na tela do app. Cartão em volta do título quando existe; nas páginas nativas do Streamlit, a
   região que vai do título até o próximo bloco (completada em medir()). */
function rectBruto(b) {
  if (!visivelEl(b._el)) return null;
  var off = { left: 0, top: 0 };
  if (b._ifr) { if (!b._ifr.isConnected) return null; off = b._ifr.getBoundingClientRect(); }
  var c = contDe(b);
  if (c) {
    var r = c.getBoundingClientRect();
    return { left: off.left + r.left, top: off.top + r.top, right: off.left + r.right, bottom: off.top + r.bottom };
  }
  var ec = b._el.closest('[data-testid="stElementContainer"]') || b._el, pg = b._el.closest('.st-key-pg') || principal();
  var re = ec.getBoundingClientRect(), rp = pg ? pg.getBoundingClientRect() : re;
  return { left: off.left + rp.left, right: off.left + rp.right, top: off.top + re.top, bottom: off.top + rp.bottom, regiao: true };
}

/* ---- mouse: se ele parar sobre um bloco, esse bloco ganha do centro da tela (até a próxima rolagem) */
function escutarDoc(doc, ifr) {
  if (doc.__mbyPtr) return; doc.__mbyPtr = true;
  try {
    doc.addEventListener('mousemove', function (e) { noMouse(e, ifr); }, { passive: true, capture: true });
    doc.addEventListener('wheel', noScroll, { passive: true, capture: true });
    doc.addEventListener('mouseleave', function () { S.ptr = null; }, { passive: true });
  } catch (e) { }
}
function noMouse(e, ifr) {
  var p = S.ptr;
  if (p && Math.abs(p.sx - e.screenX) < 4 && Math.abs(p.sy - e.screenY) < 4) return;   // evento sintético depois da rolagem
  var x = e.clientX, y = e.clientY;
  if (ifr) { try { var o = ifr.getBoundingClientRect(); x += o.left; y += o.top; } catch (er) { return; } }
  S.ptr = { x: x, y: y, sx: e.screenX, sy: e.screenY, t: performance.now() };
}

function medir() {
  resolver();
  var bls = S.cfg.blocos || [], A = areaMain(), vh = Wn.innerHeight;
  var rs = bls.map(function (b) { return rectBruto(b); });
  rs.forEach(function (r, i) {
    if (!r || !r.regiao) return;
    var fim = r.bottom;
    rs.forEach(function (o, j) { if (j !== i && o && o.top > r.top + 8 && o.top - 14 < fim) fim = o.top - 14; });
    r.bottom = Math.max(r.top + 40, fim);
  });
  S.rects = rs;
  // linha de leitura: o centro da tela; no começo da página ela sobe e no fim ela desce, para os primeiros e os
  // últimos blocos (que nunca chegam ao centro) também serem explicados
  var cy = vh * .46, m = principal();
  if (m) {
    var resto = m.scrollHeight - m.clientHeight - m.scrollTop, topo = m.scrollTop;
    if (resto < vh * .5) cy = vh * (.46 + .36 * (1 - Math.max(0, resto) / (vh * .5)));
    else if (topo < vh * .3) cy = vh * (.46 - .14 * (1 - topo / (vh * .3)));
  }
  var cx = (A.x0 + A.x1 - gutAtual()) / 2, melhor = -1, bd = 1e9, ba = 1e15;
  rs.forEach(function (r, i) {
    if (!r) return;
    var h = r.bottom - r.top, w = r.right - r.left; if (h < 8 || w < 8) return;
    var vis = Math.min(r.bottom, vh) - Math.max(r.top, 0); if (vis < Math.min(70, h * .45)) return;
    var dx = cx < r.left ? r.left - cx : cx > r.right ? cx - r.right : 0, dy = cy < r.top ? r.top - cy : cy > r.bottom ? cy - r.bottom : 0;
    var d = Math.sqrt(dx * dx * .3 + dy * dy), a = w * h;
    if (d < bd - 2 || (Math.abs(d - bd) <= 2 && a < ba)) { melhor = i; bd = d; ba = a; }
  });
  if (bd > vh * .42) melhor = -1;
  // cartões lado a lado na linha de leitura: o Floco explica da esquerda para a direita, um de cada vez
  if (melhor >= 0) {
    var rb0 = rs[melhor], larg = A.x1 - A.x0 - gutAtual(), linha = [];
    rs.forEach(function (r, i) {
      if (!r || r.top > cy || r.bottom < cy || r.right - r.left > larg * .8) return;
      if (i !== melhor && ((r.left <= rb0.left && r.right >= rb0.right && r.top <= rb0.top && r.bottom >= rb0.bottom) ||
        (rb0.left <= r.left && rb0.right >= r.right && rb0.top <= r.top && rb0.bottom >= r.bottom))) return;   // um dentro do outro
      linha.push(i);
    });
    if (linha.length > 1 && linha.indexOf(melhor) >= 0) {
      linha.sort(function (a, b) { return rs[a].left - rs[b].left; });
      var agora = performance.now(), k = linha.indexOf(S.bl), visto = function (i) { return !!S.vistos[bls[i].alvo]; };
      var feito = k >= 0 && visto(S.bl) && agora > S.vistos[bls[S.bl].alvo];
      if (k >= 0 && !feito) melhor = S.bl;
      else {
        var novos = linha.filter(function (i) { return !visto(i); }), depois = novos.filter(function (i) { return linha.indexOf(i) > k; });
        if (novos.length) melhor = k >= 0 && depois.length ? depois[0] : novos[0];
        else if (k >= 0) melhor = S.bl;
      }
    }
  }
  // o mouse manda: vale o bloco que está sob ele. Fora de qualquer bloco (ou sem mouse: toque, ponteiro fora da janela)
  // vale a linha de leitura no centro da tela
  S.porMouse = false;
  var p = S.ptr;
  if (p && p.x > A.x0 && p.x < A.x1 - gutAtual() && p.y > 0 && p.y < vh) {
    var pm = -1, pa = 1e15;
    rs.forEach(function (r, i) { if (r && p.x >= r.left && p.x <= r.right && p.y >= r.top && p.y <= r.bottom) { var a = (r.right - r.left) * (r.bottom - r.top); if (a < pa) { pa = a; pm = i; } } });
    if (pm >= 0) { melhor = pm; S.porMouse = true; }
  }
  return melhor;
}

/* ------------------------------------------------------------------ diálogo: o Beto pergunta, o Floco explica */
function zerarBloco() { encerrarDialogo(); S.bl = -1; S.cand = -2; S.candDesde = 0; S.dlgPend = false; S.rects = []; }
function encerrarDialogo() {
  S.dlgId++; var d = S.dlg; S.dlg = null; op.fala = false; rb.fala = false; rb.pose = ''; op.pose = '';
  if (d) { d.el.classList.remove('on'); setTimeout(function () { d.el.remove(); }, 300); }
}
function digitar(el, txt, v, id) {
  return new Promise(function (res) {
    var i = 0;
    (function passo() {
      if (id !== S.dlgId) return res(false);
      if (S.dlg && S.dlg.completo || S.reduzir) { el.textContent = txt; return res(true); }
      i = Math.min(txt.length, i + (txt.length > 220 ? 2 : 1)); el.textContent = txt.slice(0, i);
      if (i >= txt.length) return res(true);
      setTimeout(passo, v);
    })();
  });
}
function pausaD(ms, id) { return new Promise(function (r) { setTimeout(function () { r(id === S.dlgId); }, S.dlg && S.dlg.completo ? 0 : ms); }); }
function iniciarDialogo(b) {
  S.dlgPend = false; encerrarDialogo(); var id = S.dlgId;
  var el = D.createElement('div'); el.className = 'mby-dlg';
  el.innerHTML = '<div class="mby-dlg-cab"><span class="mby-rot"></span><span class="mby-dlg-dica">clique para ler tudo</span><button type="button" class="mby-x" aria-label="Fechar">×</button></div>' +
    '<p class="mby-fl op"><span class="mby-n"></span><span class="mby-t"></span></p>' +
    '<p class="mby-fl rb"><span class="mby-n">Floco · modelo</span><span class="mby-t"></span></p>';
  el.querySelector('.mby-rot').textContent = b.rot || ''; el.querySelector('.op .mby-n').textContent = nomeOp();
  elBolhas.appendChild(el);
  var d = { el: el, b: b, fase: 'beto', ate: 0, completo: false, chave: chaveBloco(b) };
  S.dlg = d;
  el.addEventListener('click', function (ev) {
    if (ev.target.closest('.mby-x')) { S.vistos[b.alvo] = performance.now() - 1; encerrarDialogo(); S.fechado = d.chave; return; }
    d.completo = true;
  });
  requestAnimationFrame(function () { el.classList.add('on'); });
  var lb = el.querySelector('.op .mby-t'), lf = el.querySelector('.rb .mby-t'), pf = el.querySelector('.mby-fl.rb');
  (async function () {
    op.fala = true; var ok = await digitar(lb, trocarNome(b.beto), 20, id); op.fala = false; if (!ok) return;
    if (!(await pausaD(380, id))) return;
    d.fase = 'floco'; pf.classList.add('on'); rb.fala = true;
    ok = await digitar(lf, trocarNome(b.floco), 13, id); rb.fala = false; if (!ok) return;
    d.fase = 'lido'; el.classList.add('lido'); d.ate = performance.now() + 9000 + b.floco.length * 45; S.vistos[b.alvo] = performance.now() + Math.max(3000, b.floco.length * 38);  // tempo de leitura antes de passar ao vizinho
  })();
}
function chaveBloco(b) { return b ? b.alvo + '|' + b.floco : ''; }

/* ------------------------------------------------------------------ laço da companhia */
function atualizarCompanhia(dt) {
  var cfg = S.cfg, kc = kComp(), A = areaMain(), agora = performance.now(), vh = Wn.innerHeight;
  var escondidos = S.ocultar || cfg.aba === 'perfil' || !cabeNaTela();
  if (S.gutOn !== !escondidos) { S.gutOn = !escondidos; gutter(S.gutOn); }
  [op, rb].forEach(function (a) { a.vis = clamp(a.vis + dt * (escondidos ? -3 : 1.6), 0, 1); });

  // 1. qual bloco está no centro (ou sob o mouse)? troca só quando a escolha fica estável
  if (!escondidos && agora - S.ultMedida > 140) {
    S.ultMedida = agora;
    var m = medir();
    if (m !== S.cand) { S.cand = m; S.candDesde = agora; }
    var espera = S.porMouse ? 320 : (S.bl < 0 ? 0 : 220);
    if (S.cand !== S.bl && agora - S.candDesde >= espera && (S.porMouse || agora - S.ultScroll > 200)) {
      S.bl = S.cand; encerrarDialogo(); S.dlgPend = S.bl >= 0; S.fechado = null;
    }
  }
  if (escondidos && S.dlg) encerrarDialogo();
  var b = S.bl >= 0 ? (cfg.blocos || [])[S.bl] : null, r = b ? (S.rects || [])[S.bl] : null;

  // 2. os dois andam juntos até a altura do bloco
  var yc = null;
  if (r) yc = (Math.max(r.top, 56) + Math.min(r.bottom, vh - 40)) / 2;
  [rb, op].forEach(function (a) {
    var ty = yc != null ? clamp(yc + 34 * kc, 70 * kc + 30, vh - 22) : (a.alvoY || vh * .78);
    a.alvoY = ty; a.k = kc;
    var ax = xCompanhia(a, A), dx = ax - a.sx, dy = ty - a.sy, vel = (a.tipo === 'rb' ? 360 : 320) * dt, dist = Math.sqrt(dx * dx + dy * dy);
    if (dist > 1.5) {
      var f = Math.min(1, vel / dist); a.sx += dx * f; a.sy += dy * f; a.andando = true; a.fase += dt * 11; a.pose = '';
      a.dir = Math.abs(dy) > Math.abs(dx) * .6 ? (dy > 0 ? 's' : (a.tipo === 'rb' ? 'nw' : 'ne')) : (dx > 0 ? 'se' : 'sw');
    } else { a.andando = false; a.sx = ax; a.sy = ty; }
  });
  var parados = !op.andando && !rb.andando;

  // 3. diálogo: começa quando os dois chegam e a rolagem para
  if (b && S.dlgPend && parados && !escondidos && agora - S.ultScroll > 420 && S.fechado !== chaveBloco(b)) iniciarDialogo(b);
  var d = S.dlg;
  if (d && d.fase === 'lido' && agora > d.ate) { encerrarDialogo(); }
  d = S.dlg;
  if (parados) {
    op.dir = 'sw';
    if (d && d.fase === 'beto') { rb.dir = 'se'; rb.pose = ''; op.pose = 'aceno'; }
    else if (d && r) {
      op.pose = ''; rb.dir = 'sw'; rb.pose = 'ponta'; rb.ponta = -1;
      var ya = rb.sy - 21 * kc * RB_ESC, cy2 = (Math.max(r.top, 0) + Math.min(r.bottom, vh)) / 2; rb.ky = clamp((cy2 - ya) / 80, -1, 1);
    } else { rb.dir = 'sw'; rb.pose = ''; op.pose = ''; }
  }

  // 4. moldura no bloco enquanto o Floco fala dele
  var fr = (d && r && !escondidos) ? limitarFoco(r) : null;
  if (fr && fr.height > 10) {
    elFoco.className = 'mby-foco on rb'; elFoco.style.left = (fr.left - 6) + 'px'; elFoco.style.top = (fr.top - 6) + 'px';
    elFoco.style.width = (fr.width + 12) + 'px'; elFoco.style.height = (fr.height + 12) + 'px';
  } else elFoco.className = 'mby-foco';
  if (S.rolou || agora > S.dicaAte) elDica.classList.remove('on'); else if (agora < S.dicaAte && parados) elDica.classList.add('on');
  raiz.classList.toggle('mby-fora', escondidos);
}
function limitarFoco(r) {
  var A = areaMain(), vh = Wn.innerHeight, l = Math.max(r.left, A.x0 + 4), rt = Math.min(r.right, A.x1 - gutAtual() - 4);
  var t = Math.max(r.top, -8), bt = Math.min(r.bottom, vh + 8);
  return { left: l, top: t, width: Math.max(40, rt - l), height: bt - t };
}

/* ------------------------------------------------------------------ posicionar balões */
function posicionarBolhas(dt) {
  var vw = Wn.innerWidth, vh = Wn.innerHeight, topo = Infinity;
  S.bolhas.filter(function (b) { return b.lado === 'cima'; }).sort(function (x, y) { return y.ordem - x.ordem; }).forEach(function (b) {
    var p = posCab(b.a), w = b.el.offsetWidth, h = b.el.offsetHeight, alvo = p[1] - h - 16;
    if (topo < Infinity) alvo = Math.min(alvo, topo - h - 15);
    if (b.cy == null) b.cy = alvo; b.cy += (alvo - b.cy) * Math.min(1, (dt || .016) * 9); topo = b.cy;
    var x = clamp(p[0] - w / 2, 8, vw - w - 8);
    b.el.style.setProperty('--tx', clamp(p[0] - x, 16, w - 16) + 'px'); b.el.style.left = Math.round(x) + 'px'; b.el.style.top = Math.round(b.cy) + 'px';
    b.el.style.opacity = b.cy < 40 && !b.morta ? String(clamp((b.cy + h * .3) / (h * .6 + 40), 0, 1)) : '';
  });
  var d = S.dlg;
  if (d) {
    var A = areaMain(), g = gutAtual(), livre = A.x1 - A.x0 - g;
    var w = Math.max(240, Math.min(640, livre - 32)); d.el.style.width = w + 'px';
    var h = d.el.offsetHeight, x = A.x0 + livre - w - 14, cyR = rb.sy - 30 * rb.k;
    // se o bloco já ocupa a parte de baixo da tela, o diálogo sobe para o topo
    var r = (S.rects || [])[S.bl], emBaixo = r && r.bottom > vh - h - 30 && r.top > vh * .52;
    d.el.style.left = Math.round(x) + 'px'; d.el.style.top = Math.round(emBaixo ? 52 : vh - h - 16) + 'px';
    d.el.style.setProperty('--ty', clamp(cyR - (emBaixo ? 52 : vh - h - 16), 18, h - 18) + 'px');
  }
  // dica "Role a página": no meio da área do conteúdo, acima do diálogo quando ele está embaixo
  if (S.modo === 'companhia') {
    var A2 = areaMain(), g2 = gutAtual(), dh = elDica.offsetHeight || 44, topoD = vh - 118 - dh;
    if (d && parseFloat(d.el.style.top) > vh / 2) topoD = parseFloat(d.el.style.top) - dh - 14;
    elDica.style.left = Math.round(A2.x0 + (A2.x1 - A2.x0 - g2) / 2) + 'px'; elDica.style.top = Math.round(topoD) + 'px'; elDica.style.bottom = 'auto';
  }
}

/* ------------------------------------------------------------------ laço principal */
function mover(a, dt) {
  if (!a.caminho.length) { a.andando = false; return; }
  var alvo = a.caminho[0], dx = alvo[0] - a.x, dy = alvo[1] - a.y, dist = Math.sqrt(dx * dx + dy * dy), passo = a.vel * dt;
  if (dist <= passo) { a.x = alvo[0]; a.y = alvo[1]; a.caminho.shift(); if (!a.caminho.length) { a.andando = false; var f = a.fim; a.fim = null; if (f) f(); } return; }
  a.x += dx / dist * passo; a.y += dy / dist * passo; a.andando = true; a.fase += dt * 9.5;
  a.dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'se' : 'nw') : (dy > 0 ? 'sw' : 'ne');
}

function objetosSala() {
  var L = [], i;
  for (i = 0; i < 3; i++) (function (i) { var y0 = .85 + i * 1; L.push({ x0: 0, x1: .95, y0: y0, y1: y0 + .96, f: function () { armarioUm(i); } }); })(i);
  L.push({ x0: 0, x1: 1.05, y0: 6.4, y1: 8.5, f: function () { bancada(E); } });
  E.maq.forEach(function (m) { L.push({ x0: m.x, x1: m.x + m.w, y0: m.y, y1: m.y + m.d, f: function () { maquina(m, E.t); } }); });
  L.push({ x0: 10.7, x1: 12.0, y0: 6.1, y1: 7.4, f: caixotes1 });
  L.push({ x0: 11.7, x1: 12.7, y0: 8.2, y1: 9.2, f: function () { cilindro(12.2, 8.7, .5, 0, 1.15, '#4aa3df', '#2a74b0', '#1d5a8d'); cilindro(12.2, 8.7, .5, .55, .16, '#ffc21a', '#e5a400', '#c98e00'); } });
  L.push({ x0: 10.8, x1: 11.8, y0: 8.6, y1: 9.6, f: function () { cilindro(11.3, 9.1, .42, 0, .9, '#7fa88c', '#4d7a60', '#3b6049'); } });
  [op, rb].forEach(function (a) { if (!a.tela && a.vis > 0) L.push({ x0: a.x - .25, x1: a.x + .25, y0: a.y - .25, y1: a.y + .25, a: a, f: function () { desenharAtor(a); } }); });
  return ordenar(L);
}
function armarioUm(i) {
  var y0 = .85 + i * 1, ab = E.armario.aberto, it = E.armario.itens;
  caixa(0, y0, .95, .96, 2.9, 0, '#b4c2d8', '#7b8fb0', '#8fa3c4');
  sobre('x', .95, y0, 0, function (c) {
    var u = .06, w = .84;
    if (i === 1 && ab) {
      rc(c, u, .08, w, 2.74, '#26324f'); rc(c, u + .05, 1.5, w - .1, .06, '#5e6f93');
      var VV = (op && op.visual) || VISUAL_PADRAO;
      if (it.cap) { c.fillStyle = VV.capacete; c.beginPath(); c.arc(u + w * .5, 2.3, .2, Math.PI, 0); c.fill(); rc(c, u + w * .5 - .27, 2.27, .54, .07, tom(VV.capacete, .86)); }
      if (it.oc) { rc(c, u + .1, 2.0, .62, .12, '#1f2937'); rc(c, u + .14, 1.95, .24, .18, '#bfefff'); rc(c, u + .46, 1.95, .24, .18, '#bfefff'); }
      if (it.col) { rc(c, u + .15, .9, .54, .95, VV.colete); rc(c, u + .25, .9, .09, .95, tom(VV.colete, 1.75)); rc(c, u + .5, .9, .09, .95, tom(VV.colete, 1.75)); }
      if (it.lu) { rc(c, u + .12, .45, .2, .3, VV.luva); rc(c, u + .5, .45, .2, .3, VV.luva); }
      c.fillStyle = '#9fb2d0'; c.beginPath(); c.moveTo(u + w, .08); c.lineTo(u + w + .28, .02); c.lineTo(u + w + .28, 2.7); c.lineTo(u + w, 2.82); c.fill();
    } else {
      rc(c, u, .08, w, 2.74, '#9bb0d2'); rc(c, u, .08, w, .06, '#c9d7ee');
      for (var s = 0; s < 4; s++) rc(c, u + .15, 2.35 + s * .09, w - .3, .04, '#4c5d82');
      rc(c, u + w - .2, 1.35, .08, .3, '#2a3656'); rc(c, u + .3, .25, .28, .16, '#fff'); txtL(c, String(i + 1), u + .44, .29, .13, INK);
    }
  });
}
function caixotes1() {
  caixa(10.7, 6.1, 1.3, 1.3, 1.05, 0, '#c9a46c', '#9a7440', '#ad8450');
  sobre('y', 7.4, 10.7, 0, function (c) { rc(c, .1, .08, 1.1, .08, '#6c4d27'); rc(c, .1, .88, 1.1, .08, '#6c4d27'); lin(c, .1, .1, 1.2, .94, '#6c4d27', .06); });
  caixa(11.0, 6.4, .85, .85, .8, 1.05, '#d6b37b', '#a97f4a', '#bb8f56');
}
function ordenar(L) {
  var n = L.length, vis = [], out = [], i;
  function antes(a, b) {
    var ax = a.x1 <= b.x0 + 1e-6, bx = b.x1 <= a.x0 + 1e-6, ay = a.y1 <= b.y0 + 1e-6, by = b.y1 <= a.y0 + 1e-6;
    if ((ax || ay) && !(bx || by)) return true;
    if ((bx || by) && !(ax || ay)) return false;
    return (a.x0 + a.x1 + a.y0 + a.y1) < (b.x0 + b.x1 + b.y0 + b.y1);
  }
  L.sort(function (a, b) { return (a.x0 + a.x1 + a.y0 + a.y1) - (b.x0 + b.x1 + b.y0 + b.y1); });
  function visita(k) { if (vis[k]) return; vis[k] = true; for (var j = 0; j < n; j++) if (j !== k && !vis[j] && antes(L[j], L[k])) visita(j); out.push(L[k]); }
  for (i = 0; i < n; i++) visita(i);
  return out;
}

function desenharAtor(a) {
  var c = ctx, al = c.globalAlpha, sx, sy, k;
  if (a.tela) { sx = a.sx; sy = a.sy; k = a.k; } else { var p = pj(a.x, a.y, 0); sx = p[0]; sy = p[1]; k = PXS; }
  c.globalAlpha = al * clamp(a.vis, 0, 1);
  if (a.tipo === 'op') operador(a, sx, sy, k); else robo(a, sx, sy, k * RB_ESC);
  c.globalAlpha = al;
}

function desenhar() {
  var c = ctx, vw = Wn.innerWidth, vh = Wn.innerHeight;
  c.setTransform(G.dpr, 0, 0, G.dpr, 0, 0); c.clearRect(0, 0, vw, vh);
  if (S.modo === 'intro' || S.modo === 'transicao') {
    var T = S.modo === 'intro' ? S.foraT : FORA, aFora = T < FORA ? 1 - ease((T - 2.3) / 1.2) : 0, aDentro = T < FORA ? ease((T - 2.3) / 1.2) : 1;
    if (T < FORA) { c.fillStyle = '#0f2455'; c.fillRect(0, 0, vw, vh); }
    if (aFora > .003) { c.save(); c.globalAlpha = aFora; desenharFora(c, vw, vh, E.t, 1 + ease((T - .5) / 2.6) * 1.9); c.restore(); }
    var al = (S.modo === 'transicao' ? 1 - ease(S.tr * 1.25) : 1) * aDentro;
    if (al > 0.003) {
      c.save(); c.globalAlpha = al;
      if (T < FORA) { var zi = 1 + .16 * (1 - aDentro); c.translate(vw / 2, vh / 2); c.scale(zi, zi); c.translate(-vw / 2, -vh / 2); }
      c.drawImage(fundoCv, 0, 0, vw, vh);
      porta(E);
      var L = objetosSala(); for (var i = 0; i < L.length; i++) L[i].f();
      E.maq.forEach(function (m) { etiqueta(m, E.t); });
      c.restore();
    }
  }
  if (S.modo === 'transicao' || S.modo === 'companhia') {
    [op, rb].forEach(function (a) { if (a.vis > 0.01) { c.save(); desenharAtor(a); c.restore(); } });
  }
}

function quadro(t) {
  raf = requestAnimationFrame(quadro);
  var dt = Math.min(.05, (t - ultimo) / 1000 || .016); ultimo = t; S.t += dt; E.t = S.t;
  if (D.hidden) return;
  [op, rb].forEach(function (a) { a.t += dt; });
  if (S.modo === 'intro') { vigiarEspera(); if (!S.esperando) { mover(op, dt); mover(rb, dt); if (S.foraT < FORA) S.foraT = Math.min(FORA, S.foraT + dt * S.ritmo); } }
  E.maq.forEach(function (m) { m.mostrar += (m.alvoMostrar - m.mostrar) * Math.min(1, dt * 5); });
  if (S.modo === 'companhia') atualizarCompanhia(dt);
  desenhar(); posicionarBolhas(dt);
}


/* ------------------------------------------------------------------ API */
function iniciarIntro() {
  resetCena(); sairLogin(); zerarBloco(); S.vistos = {}; S.modo = 'intro'; S.pular = false; S.pend = []; S.foraT = 0;
  elPular.style.display = ''; travarRolagem(true); limparBolhas();
  S.ritmo = clamp(+(S.cfg.ritmo || 1), .4, 3);
  // segura a cena (atrás da capa) até a página terminar de carregar: script parado, iframes prontos e fontes carregadas
  S.esperando = true; S.prontoDesde = 0; S.esperaIni = performance.now();
}
/* a página está pronta? O Streamlit parou de rodar o script, os iframes do conteúdo carregaram e as fontes também */
function paginaPronta() {
  var app = D.querySelector('.stApp');
  if (app && app.getAttribute('data-test-script-state') === 'running') return false;
  if (D.querySelector('[data-testid="stSkeleton"]')) return false;
  if (D.fonts && D.fonts.status !== 'loaded') return false;
  var m = principal(), fs = m ? m.querySelectorAll('iframe') : [];
  for (var i = 0; i < fs.length; i++) {
    if (fs[i].title === 'mby' || !visivelEl(fs[i])) continue;
    try { var d = fs[i].contentDocument; if (!d || d.readyState !== 'complete') return false; var r = d.getElementById('root'); if (r && !r.children.length) return false; } catch (e) { }
  }
  return true;
}
function vigiarEspera() {
  if (!S.esperando) return;
  var agora = performance.now();
  if (paginaPronta()) { if (!S.prontoDesde) S.prontoDesde = agora; } else S.prontoDesde = 0;
  // pronta e estável por 0,6 s (ou 15 s de espera, para nunca travar): tira a capa e só então começa
  if ((S.prontoDesde && agora - S.prontoDesde > 600) || agora - S.esperaIni > 15000) {
    S.esperando = false; tirarCapa();
    setTimeout(function () { if (S.modo === 'intro') roteiro(); }, 450);
  }
}
function tirarCapa() {
  var cp = D.querySelectorAll('.mby-capa');
  for (var j = 0; j < cp.length; j++) cp[j].setAttribute('data-fora', '1');
  for (var i = 0; i < cp.length; i++) (function (c) { c.style.animation = 'none'; c.style.opacity = '0'; c.style.pointerEvents = 'none'; setTimeout(function () { c.style.visibility = 'hidden'; }, 600); })(cp[i]);
}
/* mantém o que já foi achado na página quando um rerun reenvia os mesmos blocos */
function normalizar(cfg, velho) {
  var porAlvo = {};
  ((velho && velho.blocos) || []).forEach(function (b) { porAlvo[b.alvo] = b; });
  (cfg.blocos || []).forEach(function (b) { var v = porAlvo[b.alvo]; if (v) { b._el = v._el; b._ifr = v._ifr; b._cont = v._cont; b._contDe = v._contDe; } });
  return cfg;
}
function assarFundoLogin() {
  var w = Math.max(80, Math.round(Wn.innerWidth / 8)), h = Math.max(50, Math.round(Wn.innerHeight / 8)), c2 = D.createElement('canvas'); c2.width = w; c2.height = h;
  desenharFora(c2.getContext('2d'), w, h, 3);
  D.documentElement.style.setProperty('--mby-bg', 'url(' + c2.toDataURL('image/png') + ')'); D.body.classList.add('mby-login'); raiz.classList.add('mby-login');
}
function sairLogin() { D.body.classList.remove('mby-login'); raiz.classList.remove('mby-login'); }
function atualizar(cfg) {
  if (cfg.modo === 'login') { encerrarDialogo(); S.cfg = cfg; S.modo = 'login'; S.tok = null; gutter(false); assarFundoLogin(); return; }
  if (cfg.abrirPerso && cfg.abrirPerso !== S.persoN) { S.persoN = cfg.abrirPerso; setTimeout(abrirPerso, S.modo === 'intro' ? 0 : 120); }
  var velho = S.cfg, blAntes = S.bl >= 0 && velho && velho.blocos ? velho.blocos[S.bl] : null;
  S.cfg = normalizar(cfg, velho);
  if (cfg.tok !== S.tok) {
    S.tok = cfg.tok; S.aba = cfg.aba;
    if (cfg.intro && !S.reduzir) iniciarIntro(); else { iniciarCompanhia(); tirarCapa(); }
    return;
  }
  if (cfg.aba !== S.aba) { S.aba = cfg.aba; zerarBloco(); S.vistos = {}; S.ultResolve = 0; if (S.modo !== 'intro') tirarCapa(); return; }
  // mesma página: se o bloco ativo continua o mesmo, a conversa segue; se o texto dele mudou (outro dia, outro filtro), recomeça
  var blAgora = S.bl >= 0 ? (cfg.blocos || [])[S.bl] : null;
  if (!blAgora || !blAntes || blAgora.alvo !== blAntes.alvo) zerarBloco();
  else if (chaveBloco(blAgora) !== chaveBloco(blAntes)) { encerrarDialogo(); S.dlgPend = true; S.fechado = null; }
  else if (S.dlg) S.dlg.b = blAgora;
  S.ultResolve = 0;
  if (S.modo !== 'intro') tirarCapa();
  if (S.modo !== 'intro') (cfg.top5 || []).forEach(function (t, i) { revelar(i); });
}
function destruir() {
  cancelAnimationFrame(raf); ouv.forEach(function (o) { o[0].removeEventListener(o[1], o[2], o[3]); }); ouv = [];
  var m = principal(); if (m) m.style.overflow = ''; D.body.classList.remove('mby-travado'); D.body.classList.remove('mby-gut');
  if (raiz) raiz.remove(); var st = D.getElementById('mby-css'); if (st) st.remove(); delete Wn.__MBY;
}

function boot() {
  resetCena(); criarDOM(); ajustar();
  try { S.reduzir = Wn.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { }
  ouvir(Wn, 'resize', function () { ajustar(); });
  ouvir(D, 'keydown', teclas, true); ouvir(D, 'scroll', noScroll, true); ouvir(D, 'wheel', noScroll, { passive: true, capture: true });
  ouvir(D, 'mousemove', function (e) { if (!e.target.closest || !e.target.closest('#mby')) noMouse(e, null); }, { passive: true, capture: true });
  ouvir(D.documentElement, 'mouseleave', function () { S.ptr = null; }, { passive: true });
  Wn.__MBY = { versao: VERSAO, atualizar: atualizar, destruir: destruir, S: S };
  raf = requestAnimationFrame(quadro);
}
