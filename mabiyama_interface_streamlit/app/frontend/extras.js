/* MaBiYama · peças extras da aba de modelagem: Replay da frota e Raio-X da falha.
   Recebe window.EXTRAS ({replay, raiox}) e expõe window.Replay e window.RaioX para o painel.js. */
(function () {
  const { useState, useEffect, useRef, useMemo } = React;
  const html = htm.bind(React.createElement);
  const EX = window.EXTRAS || {};

  /* ------------------------------------------------------------------ estilos próprios */
  const css = `
  .xp-card{border-radius:calc(var(--radius) + 4px);border:1px solid var(--border);background:var(--card);padding:1.25rem;box-shadow:var(--shadow-card);border-left:4px solid var(--brand)}
  .xp-top{display:flex;flex-wrap:wrap;align-items:flex-start;justify-content:space-between;gap:.75rem;margin-bottom:.9rem}
  .xp-titulo{font-weight:800;font-size:1rem;margin:0;color:var(--foreground)}
  .xp-sub{font-size:.78rem;color:var(--muted-foreground);margin:.2rem 0 0;max-width:46rem;line-height:1.45}
  .xp-tag{display:inline-flex;align-items:center;gap:.35rem;border-radius:999px;padding:.2rem .65rem;font-size:.7rem;font-weight:700;background:var(--violet-soft);color:var(--violet)}
  .xp-btn{display:inline-flex;align-items:center;justify-content:center;gap:.4rem;border:1px solid var(--input);background:var(--card);border-radius:.55rem;height:2.1rem;padding:0 .8rem;font:inherit;font-size:.8rem;font-weight:700;color:var(--foreground);cursor:pointer;transition:background .15s,border-color .15s}
  .xp-btn:hover{background:var(--accent)}
  .xp-btn.on{background:var(--brand-deep);border-color:var(--brand-deep);color:var(--primary-foreground)}
  .xp-play{background:var(--brand);border-color:var(--brand);color:#fff;width:2.6rem;height:2.6rem;border-radius:999px;padding:0}
  .xp-play:hover{background:var(--brand-deep)}
  .xp-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;margin:.25rem 0 .75rem}
  .xp-range{flex:1 1 220px;accent-color:var(--brand);min-width:180px}
  .xp-grid{display:grid;gap:1rem;grid-template-columns:minmax(0,1fr)}
  @media (min-width:1024px){.xp-grid{grid-template-columns:minmax(0,2.2fr) minmax(0,1fr)}}
  .xp-mapa{position:relative;border-radius:.75rem;background:linear-gradient(180deg,color-mix(in oklab,var(--brand-sky) 12%,var(--card)),var(--card));border:1px solid var(--border);padding:.5rem .5rem .25rem}
  .xp-mapa svg{display:block;width:100%;height:auto}
  .xp-q{transition:fill .35s ease}
  .xp-dia{font-size:1.6rem;font-weight:800;line-height:1.1;color:var(--foreground)}
  .xp-mini{font-size:.7rem;color:var(--muted-foreground);font-weight:700;text-transform:uppercase;letter-spacing:.04em}
  .xp-kpis{display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin:.75rem 0}
  .xp-kpi{border-radius:.6rem;background:var(--secondary);padding:.55rem .7rem}
  .xp-kpi b{display:block;font-size:1.25rem;font-weight:800;color:var(--foreground)}
  .xp-feed{list-style:none;margin:0;padding:0;display:grid;gap:.35rem;max-height:13.5rem;overflow:auto}
  .xp-feed li{display:flex;align-items:center;justify-content:space-between;gap:.5rem;font-size:.78rem;border-radius:.5rem;padding:.35rem .55rem;background:var(--secondary);animation:xpEntra .45s ease}
  .xp-ok{color:var(--success);font-weight:800}.xp-ko{color:var(--chart-5);font-weight:800}
  .xp-leg{display:flex;flex-wrap:wrap;gap:.75rem;font-size:.72rem;color:var(--muted-foreground);margin-top:.4rem;align-items:center}
  .xp-leg i{display:inline-block;width:.8rem;height:.8rem;border-radius:.2rem;margin-right:.3rem;vertical-align:-.1rem}
  .xp-tip{position:absolute;pointer-events:none;background:var(--primary);color:var(--primary-foreground);font-size:.72rem;border-radius:.5rem;padding:.45rem .6rem;box-shadow:0 6px 18px rgb(0 0 0/.18);white-space:nowrap;z-index:3}
  @keyframes xpEntra{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
  @keyframes xpPulso{0%{r:9;opacity:.95;stroke-width:4}100%{r:30;opacity:0;stroke-width:1}}
  .xp-pulso{animation:xpPulso 1.3s ease-out infinite;fill:none}
  .xp-narr{min-height:3.1rem;border-radius:.6rem;padding:.6rem .8rem;font-size:.83rem;line-height:1.45;background:color-mix(in oklab,var(--amber) 12%,transparent);border-left:3px solid var(--amber);transition:background .3s}
  .xp-chips{display:flex;flex-wrap:wrap;gap:.4rem}
  .xp-svgwrap svg{display:block;width:100%;height:auto;overflow:visible}
  .xp-fade{transition:opacity .4s}
  `;
  if (!document.getElementById("xp-css")) {
    const s = document.createElement("style"); s.id = "xp-css"; s.textContent = css; document.head.appendChild(s);
  }

  const PLAY = html`<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`;
  const PAUSA = html`<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>`;
  const REINICIO = html`<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/></svg>`;
  const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  const SEMANA = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];
  function dataBR(iso, longo) {
    const [a, m, d] = iso.split("-").map(Number);
    const dt = new Date(a, m - 1, d);
    return longo ? `${SEMANA[dt.getDay()]}, ${d} ${MESES[m - 1]} ${a}` : `${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}`;
  }
  const pc = (v) => String(v).replace(".", ",");
  function corRisco(p) {
    if (p === undefined) return "color-mix(in oklab, var(--border) 70%, var(--card))";
    if (p < 5) return "color-mix(in oklab, var(--brand) 22%, var(--card))";
    if (p < 20) return "color-mix(in oklab, var(--brand) 50%, var(--card))";
    if (p < 40) return "var(--brand)";
    if (p < 60) return "var(--amber)";
    return "var(--violet)";
  }

  /* ================================================================== REPLAY DA FROTA */
  function Replay() {
    const R = EX.replay;
    if (!R) return null;
    const N = R.dias.length, TOP = 10;
    const [i, setI] = useState(0);
    const [rodando, setRodando] = useState(false);
    const [vel, setVel] = useState(1);
    const [revelar, setRevelar] = useState(true);
    const [tip, setTip] = useState(null);
    const ref = useRef(null);

    /* estatísticas acumuladas por dia (falhas, previstas no top-10) */
    const acum = useMemo(() => {
      let f = 0, ok = 0, alarmes = 0;
      return R.porDia.map((d) => {
        const top = new Set(d.c.slice(0, TOP).map((e) => e[0] * 4 + e[1]));
        const falhas = [...d.c.filter((e) => e[3]).map((e) => ({ m: e[0], p: e[1], prob: e[2], rank: d.c.indexOf(e) + 1, cand: true })),
          ...d.f.map((e) => ({ m: e[0], p: e[1], prob: null, rank: null, cand: false }))];
        falhas.forEach((x) => { x.top = top.has(x.m * 4 + x.p); });
        f += falhas.length; ok += falhas.filter((x) => x.top).length;
        alarmes += d.c.slice(0, TOP).filter((e) => !e[3]).length;
        return { falhas, top, f, ok, alarmes };
      });
    }, []);

    useEffect(() => {
      if (!rodando) return;
      const passo = 900 / vel;
      setRevelar(false);
      const t1 = setTimeout(() => setRevelar(true), passo * 0.45);
      const t2 = setTimeout(() => {
        if (i >= N - 1) { setRodando(false); return; }
        setI(i + 1);
      }, passo);
      return () => { clearTimeout(t1); clearTimeout(t2); };
    }, [rodando, i, vel]);

    const dia = R.porDia[i], st = acum[i];
    const risco = useMemo(() => { const m = {}; dia.c.forEach((e) => { m[e[0] * 4 + e[1]] = e[2]; }); return m; }, [i]);
    const falhaMaq = useMemo(() => { const m = {}; if (revelar) st.falhas.forEach((x) => { m[x.m] = m[x.m] || x; if (x.top) m[x.m] = x; }); return m; }, [i, revelar]);

    /* feed: últimos eventos até o dia atual */
    const feed = useMemo(() => {
      const out = [];
      for (let k = i; k >= 0 && out.length < 8; k--) {
        if (k === i && !revelar) continue;
        acum[k].falhas.forEach((x) => out.length < 8 && out.push({ ...x, dia: R.dias[k] }));
      }
      return out;
    }, [i, revelar]);

    /* série da taxa de captura acumulada (para o mini-gráfico) */
    const serie = useMemo(() => acum.map((a) => (a.f ? a.ok / a.f : 0)), []);

    /* layout da planta: 6 linhas de produção, máquinas lado a lado */
    const linhas = useMemo(() => {
      const g = {};
      R.maquinas.forEach((m, k) => { (g[m.linha] = g[m.linha] || []).push(k); });
      return Object.keys(g).sort().map((l) => ({ linha: l, maq: g[l] }));
    }, []);
    const CEL = 34, GAP = 6, X0 = 46, Y0 = 26, LH = 58;
    const maxN = Math.max(...linhas.map((l) => l.maq.length));
    const W = X0 + maxN * (CEL + GAP) + 10, H = Y0 + linhas.length * LH + 6;
    const janelaDe = (k) => R.janelas.filter((a) => a <= R.dias[k]).length - 1;
    const irJanela = (j) => { const k = R.dias.findIndex((d) => d >= R.janelas[j]); setI(Math.max(0, k)); setRevelar(true); };

    function mostrarTip(ev, k) {
      const caixa = ref.current.getBoundingClientRect();
      const m = R.maquinas[k];
      const ps = R.pecas.map((p, j) => [p, risco[k * 4 + j]]).filter((x) => x[1] !== undefined);
      setTip({ x: ev.clientX - caixa.left + 12, y: ev.clientY - caixa.top + 12, m, ps, f: falhaMaq[k] });
    }

    const pct = st.f ? Math.round((st.ok / st.f) * 100) : 0;
    const w = 260, h = 54;
    const path = serie.slice(0, i + 1).map((v, k) => `${k ? "L" : "M"}${(k / (N - 1)) * w},${h - v * h}`).join("");

    return html`<section class="xp-card" style=${{ borderLeftColor: "var(--violet)" }} aria-label="Replay da frota">
      <div class="xp-top">
        <div>
          <h3 class="xp-titulo">Replay da frota · o modelo contra os fatos</h3>
          <p class="xp-sub">Cada quadrado é uma máquina, dividido nas peças A, B, C e D. A cor é o risco que o modelo calculou às 05:00 daquele dia,
            antes de saber o que ia acontecer. Quando uma falha real ocorre, a máquina pulsa: <b>verde</b> se estava entre as ${TOP} prioridades do dia, <b>vermelho</b> se escapou.</p>
        </div>
        <span class="xp-tag">Validação temporal · ${dataBR(R.dias[0])}/${R.dias[0].slice(0, 4)} a ${dataBR(R.dias[N - 1])}/${R.dias[N - 1].slice(0, 4)}</span>
      </div>
      <div class="xp-ctrl">
        <button class="xp-btn xp-play" aria-label=${rodando ? "Pausar" : "Reproduzir"}
          onClick=${() => { if (i >= N - 1) setI(0); setRodando(!rodando); }}>${rodando ? PAUSA : PLAY}</button>
        <button class="xp-btn" aria-label="Recomeçar" onClick=${() => { setI(0); setRevelar(true); }}>${REINICIO}</button>
        <input class="xp-range" type="range" min="0" max=${N - 1} value=${i} aria-label="Dia"
          onInput=${(e) => { setRodando(false); setI(+e.target.value); setRevelar(true); }} />
        ${[1, 2, 4, 8].map((v) => html`<button key=${v} class=${"xp-btn" + (vel === v ? " on" : "")} onClick=${() => setVel(v)}>${v}×</button>`)}
      </div>
      <div class="xp-ctrl" style=${{ marginTop: "-.25rem" }}>
        <span class="xp-mini">Ir para</span>
        ${["jan–mar", "abr–jun", "jul–set"].map((r, j) => html`<button key=${r} class=${"xp-btn" + (janelaDe(i) === j ? " on" : "")}
          onClick=${() => irJanela(j)}>${r}</button>`)}
      </div>
      <div class="xp-grid">
        <div class="xp-mapa" ref=${ref} onMouseLeave=${() => setTip(null)}>
          <svg viewBox=${`0 0 ${W} ${H}`} role="img" aria-label="Mapa de risco das máquinas por linha de produção">
            ${linhas.map((l, r) => html`<g key=${l.linha}>
              <rect x=${X0 - 8} y=${Y0 + r * LH - 6} width=${l.maq.length * (CEL + GAP) + 10} height=${CEL + 12} rx="8"
                fill="color-mix(in oklab, var(--muted-foreground) 9%, transparent)" />
              <line x1=${X0 - 8} x2=${X0 + l.maq.length * (CEL + GAP)} y1=${Y0 + r * LH + CEL + 10} y2=${Y0 + r * LH + CEL + 10}
                stroke="var(--border)" stroke-width="2" stroke-dasharray="5 4" />
              <text x="4" y=${Y0 + r * LH + CEL / 2 + 4} font-size="12" font-weight="800" fill="var(--muted-foreground)">${l.linha}</text>
              ${l.maq.map((k, c) => {
                const x = X0 + c * (CEL + GAP), y = Y0 + r * LH, q = (CEL - 3) / 2, f = falhaMaq[k];
                const noTop = [0, 1, 2, 3].some((j) => st.top.has(k * 4 + j));
                return html`<g key=${k} onMouseMove=${(e) => mostrarTip(e, k)} style=${{ cursor: "default" }}>
                  ${noTop && html`<rect x=${x - 3} y=${y - 3} width=${CEL + 6} height=${CEL + 6} rx="7" fill="none" stroke="var(--violet)" stroke-width="2" />`}
                  ${[0, 1, 2, 3].map((j) => html`<rect key=${j} class="xp-q" x=${x + (j % 2) * (q + 3)} y=${y + Math.floor(j / 2) * (q + 3)}
                    width=${q} height=${q} rx="3" fill=${corRisco(risco[k * 4 + j])} />`)}
                  ${f && html`<circle class="xp-pulso" cx=${x + CEL / 2} cy=${y + CEL / 2} r="9"
                    stroke=${f.top ? "var(--success)" : "var(--chart-5)"} />`}
                  ${f && html`<circle cx=${x + CEL / 2} cy=${y + CEL / 2} r="7" fill=${f.top ? "var(--success)" : "var(--chart-5)"} stroke="#fff" stroke-width="2" />`}
                </g>`;
              })}
            </g>`)}
            <text x=${X0 - 8} y="14" font-size="11" fill="var(--muted-foreground)">Planta SP-01 · ${R.maquinas.length} máquinas · moldura roxa = top-${TOP} do dia</text>
          </svg>
          ${tip && html`<div class="xp-tip" style=${{ left: tip.x, top: tip.y }}>
            <b>${tip.m.id}</b> · modelo ${tip.m.modelo} · ${tip.m.linha}${tip.m.idade !== null ? ` · ${tip.m.idade} anos` : ""}<br/>
            ${tip.ps.length ? tip.ps.map((x) => html`<span key=${x[0]}>Peça ${x[0]}: <b>${x[1].toFixed(0)}%</b>  </span>`) : "Nenhuma peça na janela de risco hoje"}
            ${tip.f && html`<br/><b style=${{ color: tip.f.top ? "#7ee2a8" : "#ff9b8a" }}>Falhou (peça ${R.pecas[tip.f.p]}) · ${tip.f.top ? "estava no top-" + TOP : "escapou"}</b>`}
          </div>`}
          <${Linha} acum=${acum} i=${i} N=${N} dias=${R.dias} ir=${(k) => { setRodando(false); setI(k); setRevelar(true); }} />
          <div class="xp-leg">
            <span><i style=${{ background: corRisco(undefined) }}></i>fora da janela</span>
            <span><i style=${{ background: corRisco(2) }}></i>até 5%</span>
            <span><i style=${{ background: corRisco(10) }}></i>5–20%</span>
            <span><i style=${{ background: corRisco(30) }}></i>20–40%</span>
            <span><i style=${{ background: corRisco(50) }}></i>40–60%</span>
            <span><i style=${{ background: corRisco(80) }}></i>acima de 60%</span>
          </div>
        </div>
        <aside>
          <p class="xp-mini">Dia simulado · previsão das 05:00</p>
          <p class="xp-dia">${dataBR(R.dias[i], true)}</p>
          <div class="xp-kpis">
            <div class="xp-kpi"><span class="xp-mini">Falhas até aqui</span><b>${st.f}</b></div>
            <div class="xp-kpi"><span class="xp-mini">No top-${TOP}</span><b style=${{ color: "var(--success)" }}>${st.ok} · ${pct}%</b></div>
            <div class="xp-kpi"><span class="xp-mini">Na janela hoje</span><b>${dia.c.length}</b></div>
            <div class="xp-kpi"><span class="xp-mini">Falhas hoje</span><b style=${{ color: revelar && st.falhas.length ? "var(--chart-5)" : "inherit" }}>${revelar ? st.falhas.length : "…"}</b></div>
          </div>
          <p class="xp-mini" style=${{ marginBottom: ".2rem" }}>Taxa de antecipação acumulada</p>
          <svg viewBox=${`0 0 ${w} ${h + 4}`} style=${{ width: "100%", height: "auto", display: "block" }}>
            <line x1="0" x2=${w} y1=${h / 2} y2=${h / 2} stroke="var(--border)" stroke-dasharray="3 3" />
            <text x=${w - 2} y=${h / 2 - 3} font-size="9" text-anchor="end" fill="var(--muted-foreground)">50%</text>
            <path d=${path} fill="none" stroke="var(--success)" stroke-width="2.5" stroke-linejoin="round" />
          </svg>
          <p class="xp-mini" style=${{ margin: ".8rem 0 .35rem" }}>Últimas falhas</p>
          ${feed.length === 0 ? html`<p style=${{ fontSize: ".8rem", color: "var(--muted-foreground)" }}>Aperte play para começar.</p>` : html`<ul class="xp-feed">
            ${feed.map((x, k) => html`<li key=${x.dia + x.m + x.p}>
              <span><b>${R.maquinas[x.m].id}</b> · peça ${R.pecas[x.p]} · ${dataBR(x.dia)}</span>
              <span class=${x.top ? "xp-ok" : "xp-ko"}>${x.top ? `✓ #${x.rank} · ${x.prob.toFixed(0)}%` : x.cand ? `✗ #${x.rank} · ${x.prob.toFixed(0)}%` : "✗ fora da grade"}</span>
            </li>`)}
          </ul>`}
        </aside>
      </div>
    </section>`;
  }

  /* linha do tempo: falhas por dia até o dia atual (verde = estava no top-10, vermelho = escapou); clique para pular */
  function Linha({ acum, i, N, dias, ir }) {
    const W = 760, H = 62, bw = W / N, mx = Math.max(...acum.map((a) => a.falhas.length), 1);
    const ref = useRef(null);
    const clicar = (ev) => {
      const r = ref.current.getBoundingClientRect();
      ir(Math.max(0, Math.min(N - 1, Math.floor(((ev.clientX - r.left) / r.width) * N))));
    };
    const meses = dias.map((d, k) => [d, k]).filter(([d], k) => (k === 0 || d.slice(5, 7) !== dias[k - 1].slice(5, 7)) && k < N - 8
      && !(k === 0 && dias.slice(1, 8).some((x) => x.slice(5, 7) !== d.slice(5, 7))));
    return html`<div style=${{ marginTop: ".6rem" }}>
      <p class="xp-mini" style=${{ margin: "0 0 .2rem .2rem" }}>Linha do tempo · falhas por dia (clique para pular)</p>
      <svg ref=${ref} viewBox=${`0 0 ${W} ${H + 14}`} style=${{ cursor: "pointer" }} onClick=${clicar} role="img" aria-label="Falhas por dia">
        <rect x="0" y="0" width=${W} height=${H} rx="6" fill="color-mix(in oklab, var(--muted-foreground) 6%, transparent)" />
        ${acum.map((a, k) => {
          if (k > i) return null;
          const ok = a.falhas.filter((x) => x.top).length, ko = a.falhas.length - ok;
          const hOk = (ok / mx) * (H - 6), hKo = (ko / mx) * (H - 6);
          return html`<g key=${k}>
            ${ok > 0 && html`<rect x=${k * bw} y=${H - hOk} width=${Math.max(bw - 0.6, 1)} height=${hOk} fill="var(--success)" />`}
            ${ko > 0 && html`<rect x=${k * bw} y=${H - hOk - hKo} width=${Math.max(bw - 0.6, 1)} height=${hKo} fill="var(--chart-5)" />`}
          </g>`;
        })}
        <line x1=${(i + 0.5) * bw} x2=${(i + 0.5) * bw} y1="0" y2=${H} stroke="var(--brand-deep)" stroke-width="2" />
        ${meses.map(([d, k]) => html`<text key=${d} x=${k * bw + 2} y=${H + 11} font-size="9.5" fill="var(--muted-foreground)">${MESES[+d.slice(5, 7) - 1]}</text>`)}
      </svg>
    </div>`;
  }

  /* ================================================================== RAIO-X DA FALHA */
  function RaioX() {
    const L = EX.raiox || [];
    if (!L.length) return null;
    const [sel, setSel] = useState(0);
    const [t, setT] = useState(null);           // hora atual do cursor (null = mostra tudo)
    const [rodando, setRodando] = useState(false);
    const e = L[sel];
    const H0 = e.h[0], H1 = e.h[e.h.length - 1];

    useEffect(() => { setT(null); setRodando(false); }, [sel]);
    useEffect(() => {
      if (!rodando) return;
      const atual = t === null ? H0 : t;
      if (atual >= H1) { setRodando(false); return; }
      const id = setTimeout(() => setT(atual + 1), atual < -8 ? 45 : 110);
      return () => clearTimeout(id);
    }, [rodando, t]);

    const cur = t === null ? H1 : t;
    const W = 760, PX = 46, PR = 14, h1 = 190, h2 = 120, GAPV = 34;
    const sx = (h) => PX + ((h - H0) / (H1 - H0)) * (W - PX - PR);
    const zs = e.z.filter((v) => v !== null);
    const zmin = Math.min(-3, ...zs), zmax = Math.max(3, ...zs);
    const sy = (v) => 12 + (1 - (v - zmin) / (zmax - zmin)) * (h1 - 24);
    const py = (p) => h1 + GAPV + (1 - p / 100) * (h2 - 10);
    const vis = e.h.map((h, k) => [h, e.z[k]]).filter(([h, v]) => h <= cur && v !== null);
    const linhaZ = vis.map(([h, v], k) => `${k ? "L" : "M"}${sx(h).toFixed(1)},${sy(v).toFixed(1)}`).join("");
    const nPost = e.post.length;                         // detector só até o corte (h = 0)
    const visP = e.post.map((p, k) => [e.h[k], p]).filter(([h]) => h <= cur);
    const linhaP = visP.map(([h, p], k) => `${k ? "L" : "M"}${sx(h).toFixed(1)},${py(p).toFixed(1)}`).join("");
    const pAgora = visP.length ? visP[visP.length - 1][1] : e.post[0];
    const detectou = e.det[nPost - 1] > 2 && e.inicio < 0;
    const mostraPatamar = detectou && cur >= e.inicio + 6;
    const janela96 = Math.min(cur, 0);

    let narr;
    if (cur < (detectou ? e.inicio : -10)) narr = `O ${e.sensor} (sensor ligado à peça ${e.peca}) oscila em torno do normal da máquina ${e.maquina} (desvios-padrão em relação ao histórico dela). O filtro casado compara as últimas 96 h com o formato típico de um patamar de falha.`;
    else if (cur < 0) narr = detectou && cur >= e.inicio
      ? (pAgora > 50 ? `Patamar reconhecido. A evidência acumulada passa de ${pAgora.toFixed(0)}%: o filtro soma hora a hora o desvio na direção esperada para a peça ${e.peca}.`
        : `O sinal começa a se afastar do normal. Ainda pode ser ruído, então o detector só acumula evidência devagar (${pAgora.toFixed(0)}%).`)
      : `Nada de anormal: a evidência continua perto da taxa base do ciclo (${pc(e.p0)}%).`;
    else if (cur < 1) narr = `05:00 de ${e.dia}: corte. O modelo completo (22 listas fundidas) entrega ${pc(e.prob)}% para a peça ${e.peca} da ${e.maquina}. Tudo à direita deste ponto o modelo não vê.`;
    else narr = e.falhou ? `Falha registrada às 06:00 de ${e.diaFalha}. ${e.texto}` : `A janela terminou às 06:00 de ${e.diaFalha} sem falha. ${e.texto}`;

    const cor = { pega: "var(--success)", sutil: "var(--brand)", perdida: "var(--chart-5)", alarme: "var(--amber)" }[e.chave];

    return html`<section class="xp-card" style=${{ borderLeftColor: "var(--amber)" }} aria-label="Raio-X da falha">
      <div class="xp-top">
        <div>
          <h3 class="xp-titulo">Raio-X da falha · como o modelo enxerga um sensor</h3>
          <p class="xp-sub">Casos reais da validação. A linha azul é o sensor da peça em desvios do normal; a linha de baixo é a evidência do${" "}<b>filtro casado</b> (a variável mais importante do modelo) convertida em probabilidade a partir da taxa base do ciclo.</p>
        </div>
        <div class="xp-chips">${L.map((x, k) => html`<button key=${x.chave} class=${"xp-btn" + (k === sel ? " on" : "")} onClick=${() => setSel(k)}>${x.titulo}</button>`)}</div>
      </div>
      <div class="xp-ctrl">
        <button class="xp-btn xp-play" aria-label=${rodando ? "Pausar" : "Reproduzir"}
          onClick=${() => { if (cur >= H1) setT(H0); setRodando(!rodando); }}>${rodando ? PAUSA : PLAY}</button>
        <input class="xp-range" type="range" min=${H0} max=${H1} value=${cur} aria-label="Hora"
          onInput=${(ev) => { setRodando(false); setT(+ev.target.value); }} />
        <span class="xp-mini" style=${{ minWidth: "8.5rem", textAlign: "right" }}>${cur === 0 ? "05:00 · corte" : cur < 0 ? `${-cur} h antes do corte` : `${cur} h depois do corte`}</span>
      </div>
      <div class="xp-svgwrap">
        <svg viewBox=${`0 0 ${W} ${h1 + GAPV + h2 + 22}`} role="img" aria-label="Sensor e evidência ao longo do tempo">
          <rect x=${sx(0)} y="0" width=${sx(H1) - sx(0)} height=${h1 + GAPV + h2} fill="color-mix(in oklab, var(--muted-foreground) 10%, transparent)" />
          <text x=${sx(0) + 6} y=${h1 + GAPV + h2 - 20} font-size="10.5" fill="var(--muted-foreground)" font-weight="700">depois do corte</text>
          <text x=${sx(0) + 6} y=${h1 + GAPV + h2 - 7} font-size="10.5" fill="var(--muted-foreground)" font-weight="700">o modelo não vê</text>
          ${cur <= 0 && html`<rect x=${Math.max(PX, sx(janela96 - 95))} y="4" width=${sx(janela96) - Math.max(PX, sx(janela96 - 95))} height=${h1 - 8} rx="6"
            fill="color-mix(in oklab, var(--brand) 7%, transparent)" stroke="color-mix(in oklab, var(--brand) 35%, transparent)" stroke-dasharray="4 3" />`}
          ${mostraPatamar && html`<rect class="xp-fade" x=${sx(e.inicio)} y=${sy(zmax) - 2} width=${sx(Math.min(cur, H1)) - sx(e.inicio)} height=${sy(zmin) - sy(zmax) + 4}
            fill=${`color-mix(in oklab, ${cor} 14%, transparent)`} />`}
          ${[-2, 0, 2].map((v) => html`<g key=${v}><line x1=${PX} x2=${W - PR} y1=${sy(v)} y2=${sy(v)} stroke="var(--border)" stroke-dasharray=${v ? "3 4" : ""} />
            <text x=${PX - 6} y=${sy(v) + 3} font-size="10" text-anchor="end" fill="var(--muted-foreground)">${v > 0 ? "+" + v : v}σ</text></g>`)}
          <path d=${linhaZ} fill="none" stroke="var(--brand)" stroke-width="1.6" stroke-linejoin="round" />
          ${vis.length > 0 && html`<circle cx=${sx(vis[vis.length - 1][0])} cy=${sy(vis[vis.length - 1][1])} r="4" fill="var(--brand-deep)" />`}
          <line x1=${sx(0)} x2=${sx(0)} y1="0" y2=${h1 + GAPV + h2} stroke="var(--foreground)" stroke-width="1.5" />
          <text x=${sx(0) - 5} y=${h1 + 14} font-size="10.5" text-anchor="end" font-weight="800" fill="var(--foreground)">05:00 · corte</text>
          ${cur >= 25 && html`<g><line x1=${sx(25)} x2=${sx(25)} y1="0" y2=${h1} stroke=${e.falhou ? "var(--chart-5)" : "var(--success)"} stroke-width="2.5" />
            <text x=${sx(25) - 5} y="30" font-size="11" text-anchor="end" font-weight="800" fill=${e.falhou ? "var(--chart-5)" : "var(--success)"}>${e.falhou ? "falha" : "sem falha"}</text></g>`}
          <line x1=${PX} x2=${W - PR} y1=${py(50)} y2=${py(50)} stroke="var(--border)" stroke-dasharray="3 4" />
          ${[0, 50, 100].map((v) => html`<text key=${v} x=${PX - 6} y=${py(v) + 3} font-size="10" text-anchor="end" fill="var(--muted-foreground)">${v}%</text>`)}
          <text x=${PX} y=${h1 + GAPV - 6} font-size="10.5" font-weight="700" fill="var(--muted-foreground)">evidência do filtro casado (probabilidade)</text>
          <path d=${linhaP} fill="none" stroke=${cor} stroke-width="2.6" stroke-linejoin="round" />
          ${cur >= 0 && html`<g><circle cx=${sx(0)} cy=${py(e.prob)} r="7" fill="var(--violet)" stroke="#fff" stroke-width="2" />
            <text x=${sx(0) + 11} y=${py(e.prob) + 4} font-size="11.5" font-weight="800" fill="var(--violet)">modelo: ${pc(e.prob)}%</text></g>`}
          ${[-120, -96, -72, -48, -24, 0, 24].map((v) => html`<text key=${v} x=${sx(v)} y=${h1 + GAPV + h2 + 16} font-size="10" text-anchor="middle" fill="var(--muted-foreground)">${v === 0 ? "0 h" : (v > 0 ? "+" : "") + v + " h"}</text>`)}
        </svg>
      </div>
      <div class="xp-narr" style=${{ borderLeftColor: cor }}>${narr}</div>
      <p class="xp-sub" style=${{ marginTop: ".6rem" }}>Máquina ${e.maquina} · peça ${e.peca} · ciclo ${e.k} desde a última preventiva (taxa base ${pc(e.p0)}%) · previsão para a janela de 06:00 de ${e.dia} a 06:00 de ${e.diaFalha}.
        O retângulo tracejado é a janela de 96 h que o filtro examina a cada hora.</p>
    </section>`;
  }

  window.Replay = Replay;
  window.RaioX = RaioX;
})();
