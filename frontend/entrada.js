/* MaBiYama · animação de entrada das páginas em iframe (painel, simulador, replay).
   Ao entrar numa aba, cada bloco surge quando chega à tela: sobe e aparece; cartões com barra colorida na lateral
   (como o aviso "Atenção" e os indicadores) nascem da barra e deslizam para a direita, e o conteúdo vem atrás.
   Só anima na primeira vez que a aba é aberta (window.ENTRADA muda a cada entrada na aba); recarregar a página por um
   filtro não repete a animação. */
(function () {
  var TOK = window.ENTRADA, NOME = window.ENTRADA_NOME || "pagina";
  if (!TOK) return;
  var chave = "mbyEnt:" + TOK + ":" + NOME, visto = false;
  try { var P = window.parent; P.__mbyEnt = P.__mbyEnt || {}; visto = !!P.__mbyEnt[chave]; P.__mbyEnt[chave] = 1; }
  catch (e) { try { visto = !!sessionStorage.getItem(chave); sessionStorage.setItem(chave, "1"); } catch (x) { } }
  try { if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) visto = true; } catch (e) { }
  if (visto) return;

  var css = document.createElement("style");
  css.textContent =
    "html.ent-pend #root{opacity:0}" +
    ".ent:not(.ent-on){opacity:0}" +
    ".ent.ent-on{animation:entSobe .62s cubic-bezier(.2,.75,.25,1) backwards;animation-delay:var(--ent-d,0s)}" +
    ".ent-barra.ent-on{animation:entBarra .95s cubic-bezier(.65,0,.3,1) backwards;animation-delay:var(--ent-d,0s)}" +
    ".ent-barra.ent-on>*{animation:entDesliza .6s cubic-bezier(.2,.75,.25,1) backwards;animation-delay:calc(var(--ent-d,0s) + .42s)}" +
    ".ent-barra.ent-on .grid>*{animation:entDesliza .55s cubic-bezier(.2,.75,.25,1) backwards}" +
    ".ent-barra.ent-on .grid>*:nth-child(1){animation-delay:calc(var(--ent-d,0s) + .55s)}.ent-barra.ent-on .grid>*:nth-child(2){animation-delay:calc(var(--ent-d,0s) + .62s)}" +
    ".ent-barra.ent-on .grid>*:nth-child(3){animation-delay:calc(var(--ent-d,0s) + .69s)}.ent-barra.ent-on .grid>*:nth-child(4){animation-delay:calc(var(--ent-d,0s) + .76s)}" +
    ".ent-barra.ent-on .grid>*:nth-child(5){animation-delay:calc(var(--ent-d,0s) + .83s)}.ent-barra.ent-on .grid>*:nth-child(n+6){animation-delay:calc(var(--ent-d,0s) + .9s)}" +
    "@keyframes entSobe{from{opacity:0;transform:translateY(22px) scale(.985)}to{opacity:1;transform:none}}" +
    "@keyframes entBarra{0%{opacity:1;clip-path:inset(50% calc(100% - 6px) 50% 0)}32%{opacity:1;clip-path:inset(0 calc(100% - 6px) 0 0)}100%{opacity:1;clip-path:inset(0 0 0 0)}}" +
    "@keyframes entDesliza{from{opacity:0;transform:translateX(-26px)}to{opacity:1;transform:none}}";
  document.head.appendChild(css);
  var raiz = document.documentElement; raiz.classList.add("ent-pend");

  function temBarra(el) {   // borda esquerda grossa e colorida, demais bordas finas
    var cs = getComputedStyle(el), l = parseFloat(cs.borderLeftWidth) || 0, t = parseFloat(cs.borderTopWidth) || 0;
    return l >= 3 && l > t + 1 && cs.borderLeftStyle !== "none" && !/rgba?\(0, 0, 0, 0\)/.test(cs.borderLeftColor);
  }
  function eGrade(el) {
    var cs = getComputedStyle(el);
    return (cs.display === "grid" || cs.display === "flex") && el.children.length > 1 && !temBarra(el) &&
      !/^(SECTION|ARTICLE|BUTTON|TABLE|svg)$/i.test(el.tagName) && !el.querySelector(":scope > svg");
  }
  function blocos(el, prof, out) {
    for (var i = 0; i < el.children.length; i++) {
      var c = el.children[i], r = c.getBoundingClientRect();
      if (r.height < 8 || r.width < 8 || /^(STYLE|SCRIPT)$/.test(c.tagName)) continue;
      if (prof < 3 && eGrade(c) && r.height > 60) blocos(c, prof + 1, out);
      else out.push(c);
    }
    return out;
  }
  function iniciar() {
    var base = document.querySelector("#root main") || document.querySelector("#root > div") || document.getElementById("root");
    var lista = blocos(base, 0, []);
    if (!lista.length) { raiz.classList.remove("ent-pend"); return; }
    lista.forEach(function (el) { el.classList.add("ent"); if (temBarra(el)) el.classList.add("ent-barra"); });
    raiz.classList.remove("ent-pend");
    // revela ao entrar na tela (o observador vê a janela do app inteiro, não só o iframe); quem chega junto entra em cascata
    var fila = [], agendado = false;
    function soltar() {
      agendado = false;
      fila.sort(function (a, b) { var ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect(); return (ra.top - rb.top) || (ra.left - rb.left); });
      fila.forEach(function (el, i) { el.style.setProperty("--ent-d", Math.min(i, 9) * 0.075 + "s"); el.classList.add("ent-on"); });
      fila = [];
    }
    var io = "IntersectionObserver" in window ? new IntersectionObserver(function (ents) {
      ents.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); fila.push(e.target); } });
      if (fila.length && !agendado) { agendado = true; requestAnimationFrame(soltar); }
    }, { threshold: 0.12 }) : null;
    // na primeira entrada do dia a cena de boas-vindas cobre a tela: espera ela acabar para a entrada ser vista
    function emCena() { try { var M = window.parent.__MBY; return !!(M && M.S && (M.S.modo === "intro" || M.S.modo === "transicao")); } catch (e) { return false; } }
    (function observar() {
      if (emCena()) return setTimeout(observar, 250);
      lista.forEach(function (el) { if (io) io.observe(el); else el.classList.add("ent-on"); });
      // segurança: o que não entrou na tela em 40 s aparece sem animação
      setTimeout(function () { lista.forEach(function (el) { if (!el.classList.contains("ent-on")) el.classList.remove("ent"); }); }, 40000);
    })();
  }
  var tentativas = 0;
  (function esperar() {
    var r = document.getElementById("root");
    if (r && r.children.length && r.getBoundingClientRect().height > 40) return setTimeout(iniciar, 30);
    if (++tentativas > 200) { raiz.classList.remove("ent-pend"); return; }
    requestAnimationFrame(esperar);
  })();
})();
