/* MaBiYama · personalização do operário (Beto): nome, sexo, pele, cabelo, barba, roupas e EPIs.
   Fragmento embutido por animacao.py, depois de fabrica_cena.js e fabrica_motor.js. Fica salvo no navegador (localStorage). */
var PERSO_CHAVE = 'mby_operario';
var PERSO_OP = {
  pele: [['#f6d5b5', 'Clara'], ['#f0c08a', 'Média clara'], ['#d9a066', 'Média'], ['#b37445', 'Morena'], ['#8a5532', 'Escura'], ['#5c3a22', 'Muito escura']],
  cabelo: [['curto', 'Curto'], ['raspado', 'Raspado'], ['cacheado', 'Cacheado'], ['rabo', 'Rabo de cavalo'], ['longo', 'Longo']],
  corCabelo: [['#1f1712', 'Preto'], ['#5a3b22', 'Castanho'], ['#8a5a2b', 'Castanho claro'], ['#d9a441', 'Loiro'], ['#b8462c', 'Ruivo'], ['#a3a8b0', 'Grisalho']],
  camisa: [['#6d7f96', 'Cinza azulado'], ['#2f5d9e', 'Azul'], ['#3f8a5a', 'Verde'], ['#8a4fa8', 'Roxo'], ['#c0503a', 'Vermelho'], ['#2b2f3a', 'Grafite'], ['#e9edf3', 'Branco']],
  calca: [['#34507f', 'Jeans'], ['#2b2f3a', 'Preta'], ['#5b4636', 'Marrom'], ['#56606e', 'Cinza'], ['#3d6b4f', 'Verde']],
  calcado: [['#3b2c22', 'Marrom'], ['#1d1f26', 'Preto'], ['#7a5232', 'Caramelo'], ['#8a1f1f', 'Vinho']],
  capacete: [['#ffc21a', 'Amarelo'], ['#f4f6fa', 'Branco'], ['#2f6fd1', 'Azul'], ['#36a565', 'Verde'], ['#e0453a', 'Vermelho'], ['#ff8a1f', 'Laranja']],
  colete: [['#ff7a1a', 'Laranja'], ['#c8e62a', 'Verde-limão'], ['#ffd21a', 'Amarelo'], ['#2fb36b', 'Verde'], ['#e04a8a', 'Rosa']],
  luva: [['#e8a317', 'Couro'], ['#3a3f4b', 'Preta'], ['#e9edf3', 'Branca'], ['#3c7fd6', 'Azul']]
};
var PERSO_GRUPOS = [
  ['Pele', 'pele'], ['Cor do cabelo', 'corCabelo'], ['Camisa', 'camisa'], ['Calça', 'calca'], ['Calçado', 'calcado'],
  ['Capacete', 'capacete'], ['Colete', 'colete'], ['Luvas', 'luva']
];
var PERSO = null, PZ = null;

function persoPadrao(sexo) {
  var v = JSON.parse(JSON.stringify(VISUAL_PADRAO));
  if (sexo === 'f') { v.sexo = 'f'; v.cabelo = 'rabo'; v.corCabelo = '#5a3b22'; }
  return { nome: sexo === 'f' ? 'Bia' : 'Beto', visual: v };
}
function carregarPerso() {
  var p = persoPadrao('m');
  try {
    var s = JSON.parse(localStorage.getItem(PERSO_CHAVE) || 'null');
    if (s && typeof s === 'object') {
      if (typeof s.nome === 'string' && s.nome.trim()) p.nome = s.nome.trim().slice(0, 16);
      if (s.visual) for (var k in p.visual) if (s.visual[k] !== undefined && typeof s.visual[k] === typeof p.visual[k]) p.visual[k] = s.visual[k];
    }
  } catch (e) { }
  PERSO = p; return p;
}
function aplicarPerso(a) {
  if (!PERSO) carregarPerso();
  if (a) { a.nome = PERSO.nome; a.visual = PERSO.visual; }
}
function nomeOp() { return (PERSO && PERSO.nome) || 'Beto'; }
function trocarNome(txt) { return String(txt == null ? '' : txt).replace(/\{beto\}/g, nomeOp()); }

/* ------------------------------------------------------------------ painel */
function htmlSw(chave, lista) {
  return '<div class="mby-pz-sw" data-k="' + chave + '">' + lista.map(function (o) {
    return '<button type="button" data-v="' + o[0] + '" title="' + o[1] + '" aria-label="' + o[1] + '" style="--c:' + o[0] + '"></button>';
  }).join('') + '<label class="mby-pz-cor" title="Outra cor"><input type="color" data-k="' + chave + '"><span>+</span></label></div>';
}
function abrirPerso() {
  if (PZ) return;
  if (!PERSO) carregarPerso();
  var rasc = JSON.parse(JSON.stringify(PERSO)), giro = 0, dirs = ['s', 'se', 'ne', 'nw', 'sw'], andando = true, epi = true;
  var el = D.createElement('div'); el.className = 'mby-pz';
  el.innerHTML =
    '<div class="mby-pz-card" role="dialog" aria-modal="true" aria-label="Personalizar operário">' +
    '<div class="mby-pz-cab"><div><b>Personalize o seu operário</b><span>Fica salvo neste navegador.</span></div><button type="button" class="mby-x" data-a="cancelar" aria-label="Fechar">×</button></div>' +
    '<div class="mby-pz-corpo">' +
    '<div class="mby-pz-prev"><div class="mby-pz-palco"><canvas></canvas><span class="mby-pz-nome"></span></div>' +
    '<div class="mby-pz-giro"><button type="button" data-g="-1" aria-label="Girar para a esquerda">◀</button><span>Girar</span><button type="button" data-g="1" aria-label="Girar para a direita">▶</button></div>' +
    '<div class="mby-pz-tg"><label><input type="checkbox" data-t="andar" checked> Andando</label><label><input type="checkbox" data-t="epi" checked> Com EPIs</label></div></div>' +
    '<div class="mby-pz-ctrl">' +
    '<label class="mby-pz-l">Nome<input type="text" maxlength="16" data-k="nome" autocomplete="off" spellcheck="false"></label>' +
    '<div class="mby-pz-l">Sexo<div class="mby-pz-seg" data-k="sexo"><button type="button" data-v="m">Masculino</button><button type="button" data-v="f">Feminino</button></div></div>' +
    '<div class="mby-pz-l">Cabelo<div class="mby-pz-seg mby-pz-wrap" data-k="cabelo">' + PERSO_OP.cabelo.map(function (o) { return '<button type="button" data-v="' + o[0] + '">' + o[1] + '</button>'; }).join('') + '</div></div>' +
    '<div class="mby-pz-l">Barba<div class="mby-pz-seg" data-k="barba"><button type="button" data-v="0">Sem</button><button type="button" data-v="1">Com</button></div></div>' +
    '<div class="mby-pz-grade">' + PERSO_GRUPOS.map(function (g) { return '<div class="mby-pz-l">' + g[0] + htmlSw(g[1], PERSO_OP[g[1]]) + '</div>'; }).join('') + '</div>' +
    '</div></div>' +
    '<div class="mby-pz-pe"><button type="button" class="sec" data-a="sortear">Sortear</button><button type="button" class="sec" data-a="padrao">Restaurar padrão</button><i></i>' +
    '<button type="button" class="sec" data-a="cancelar">Cancelar</button><button type="button" class="pri" data-a="salvar">Salvar</button></div></div>';
  raiz.appendChild(el);
  var cvp = el.querySelector('canvas'), cp = cvp.getContext('2d'), nomeEl = el.querySelector('.mby-pz-nome'), inp = el.querySelector('input[data-k="nome"]');
  var dpr = Math.min(2, Wn.devicePixelRatio || 1), CW = 230, CH = 270;
  cvp.width = CW * dpr; cvp.height = CH * dpr; cvp.style.width = CW + 'px'; cvp.style.height = CH + 'px';
  var ator = novoAtor('op', rasc.nome); ator.eq = { capacete: true, colete: true, luvas: true, oculos: true, ferr: true, caixa: true }; ator.visual = rasc.visual;

  function marcar() {
    inp.value = rasc.nome; nomeEl.textContent = rasc.nome || '—';
    el.querySelectorAll('.mby-pz-seg').forEach(function (sg) {
      var k = sg.getAttribute('data-k'), v = k === 'barba' ? (rasc.visual.barba ? '1' : '0') : rasc.visual[k];
      sg.querySelectorAll('button').forEach(function (b) { var on = b.getAttribute('data-v') === v; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); });
    });
    el.querySelectorAll('.mby-pz-sw').forEach(function (sw) {
      var k = sw.getAttribute('data-k'), v = String(rasc.visual[k]).toLowerCase(), achou = false;
      sw.querySelectorAll('button').forEach(function (b) { var on = b.getAttribute('data-v').toLowerCase() === v; achou = achou || on; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); });
      var ci = sw.querySelector('input'), lb = sw.querySelector('.mby-pz-cor'); ci.value = /^#[0-9a-f]{6}$/i.test(v) ? v : '#888888';
      lb.classList.toggle('on', !achou); lb.style.setProperty('--c', achou ? 'transparent' : v);
    });
  }
  function sortear() {
    var pick = function (l) { return l[Math.floor(Math.random() * l.length)][0]; }, v = rasc.visual;
    v.sexo = Math.random() < .5 ? 'm' : 'f'; v.cabelo = pick(PERSO_OP.cabelo); v.barba = v.sexo === 'm' && Math.random() < .35;
    PERSO_GRUPOS.forEach(function (g) { v[g[1]] = pick(PERSO_OP[g[1]]); });
    if (rasc.nome === 'Beto' || rasc.nome === 'Bia') rasc.nome = v.sexo === 'f' ? 'Bia' : 'Beto';
  }
  function fechar(salvar) {
    if (salvar) {
      rasc.nome = (inp.value || '').trim().slice(0, 16) || (rasc.visual.sexo === 'f' ? 'Bia' : 'Beto');
      PERSO = rasc; try { localStorage.setItem(PERSO_CHAVE, JSON.stringify(PERSO)); } catch (e) { }
      aplicarPerso(op); if (S.dlg) { var n = S.dlg.el.querySelector('.op .mby-n'); if (n) n.textContent = nomeOp(); }
    }
    cancelAnimationFrame(PZ.raf); D.removeEventListener('keydown', PZ.tecla, true);
    el.classList.remove('on'); setTimeout(function () { el.remove(); }, 220); PZ = null;
  }
  el.addEventListener('click', function (ev) {
    var t = ev.target;
    if (t === el) return fechar(false);
    var a = t.closest('[data-a]'); if (a) { var ac = a.getAttribute('data-a');
      if (ac === 'salvar') return fechar(true); if (ac === 'cancelar') return fechar(false);
      if (ac === 'sortear') sortear(); if (ac === 'padrao') rasc = persoPadrao(rasc.visual.sexo); ator.visual = rasc.visual; marcar(); return; }
    var g = t.closest('[data-g]'); if (g) { giro = (giro + +g.getAttribute('data-g') + dirs.length) % dirs.length; return; }
    var b = t.closest('.mby-pz-seg button, .mby-pz-sw button');
    if (b) {
      var k = b.parentNode.getAttribute('data-k'), v = b.getAttribute('data-v');
      if (k === 'barba') rasc.visual.barba = v === '1';
      else if (k === 'sexo') {
        var antes = rasc.visual.sexo; rasc.visual.sexo = v;
        if (antes !== v) {   // troca o padrão junto, sem mexer no que a pessoa já escolheu
          if (rasc.nome === (antes === 'f' ? 'Bia' : 'Beto')) rasc.nome = v === 'f' ? 'Bia' : 'Beto';
          if (v === 'f') { rasc.visual.barba = false; if (rasc.visual.cabelo === 'curto' || rasc.visual.cabelo === 'raspado') rasc.visual.cabelo = 'rabo'; }
          else if (rasc.visual.cabelo === 'rabo' || rasc.visual.cabelo === 'longo') rasc.visual.cabelo = 'curto';
        }
      } else rasc.visual[k] = v;
      marcar();
    }
  });
  el.addEventListener('input', function (ev) {
    var t = ev.target, k = t.getAttribute('data-k');
    if (k === 'nome') { rasc.nome = t.value.slice(0, 16); nomeEl.textContent = rasc.nome || '—'; return; }
    if (t.type === 'color' && k) { rasc.visual[k] = t.value; marcar(); }
  });
  el.addEventListener('change', function (ev) {
    var t = ev.target.getAttribute('data-t'); if (t === 'andar') andando = ev.target.checked; if (t === 'epi') epi = ev.target.checked;
  });
  var tecla = function (e) { if (e.key === 'Escape') { e.stopPropagation(); fechar(false); } else if (e.key === 'Enter' && e.target === inp) fechar(true); };
  D.addEventListener('keydown', tecla, true);

  var t0 = performance.now();
  function quadroPz(t) {
    PZ.raf = requestAnimationFrame(quadroPz);
    var dt = Math.min(.05, (t - t0) / 1000); t0 = t;
    ator.t += dt; ator.andando = andando; if (andando) ator.fase += dt * 9.5; ator.dir = dirs[giro]; ator.fala = false;
    ator.eq = epi ? { capacete: true, colete: true, luvas: true, oculos: true, ferr: true, caixa: true } : {};
    var salvo = G.ctx, sk = [K, BX, BY];
    cp.setTransform(dpr, 0, 0, dpr, 0, 0); cp.clearRect(0, 0, CW, CH);
    var gr = cp.createRadialGradient(CW / 2, CH - 46, 6, CW / 2, CH - 46, 110); gr.addColorStop(0, 'rgba(95,140,224,.18)'); gr.addColorStop(1, 'rgba(95,140,224,0)');
    cp.fillStyle = gr; cp.fillRect(0, 0, CW, CH);
    G.ctx = cp; try { operador(ator, CW / 2, CH - 52, 4.7); } catch (e) { }
    G.ctx = salvo; K = sk[0]; BX = sk[1]; BY = sk[2];
  }
  PZ = { el: el, raf: 0, tecla: tecla };
  marcar(); PZ.raf = requestAnimationFrame(quadroPz);
  requestAnimationFrame(function () { el.classList.add('on'); setTimeout(function () { try { inp.focus({ preventScroll: true }); inp.select(); } catch (e) { } }, 60); });
}
