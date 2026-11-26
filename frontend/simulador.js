/* MaBiYama · Simulador de política de manutenção (gêmeo digital da frota).
   Recebe window.EXTRAS ({replay, simul}). Usa os 9 meses da validação temporal de 2023, onde as falhas reais são conhecidas:
   cada dia tem as peças na janela de risco (véspera da preventiva da grade) com a probabilidade do modelo e o desfecho real. */
const { useState, useEffect, useMemo, useRef } = React;
const html = htm.bind(React.createElement);
const {
  ResponsiveContainer, ComposedChart, LineChart, BarChart, Bar, Line, Area, XAxis, YAxis, Tooltip, CartesianGrid,
  ReferenceLine, ReferenceDot, Legend, Cell,
} = Recharts;
const EX = window.EXTRAS;
const R = EX.replay, S = EX.simul;
const DIAS = R.porDia, N = DIAS.length;
const CAP = R.maquinas.map((m) => m.cap);
const NFALHAS = DIAS.reduce((a, d) => a + d.c.filter((e) => e[3]).length + d.f.length, 0);
const NFORA = DIAS.reduce((a, d) => a + d.f.length, 0);
const MESES = N / 30.4;

const css = `
body{font-family:Nunito,system-ui,sans-serif;color:var(--foreground)}
.sm-wrap{max-width:80rem;margin:0 auto;padding:1.5rem 1rem 2rem}
.sm-card{border-radius:calc(var(--radius) + 4px);border:1px solid var(--border);background:var(--card);padding:1.25rem;box-shadow:var(--shadow-card);border-left:4px solid var(--brand);min-width:0}
.sm-h{font-weight:800;font-size:1rem;margin:0 0 .2rem}
.sm-sub{font-size:.78rem;color:var(--muted-foreground);margin:0;line-height:1.45}
.sm-hero{border-radius:1rem;padding:1.4rem 1.5rem;background:linear-gradient(120deg,var(--violet-soft),color-mix(in oklab,var(--brand-sky) 22%,var(--card)));border:1px solid var(--border);color:var(--foreground);margin-bottom:1.25rem;display:flex;flex-wrap:wrap;gap:1rem;justify-content:space-between;align-items:flex-end}
.sm-hero h2{margin:.15rem 0 .3rem;font-size:1.5rem;font-weight:800;color:var(--brand-deep)}
.sm-hero p{margin:0;max-width:44rem;font-size:.88rem;color:var(--muted-foreground);line-height:1.5}
.sm-eyebrow{font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--violet)}
.sm-grid{display:grid;gap:1.25rem;grid-template-columns:minmax(0,1fr)}
@media(min-width:1024px){.sm-grid{grid-template-columns:20rem minmax(0,1fr)}}
.sm-cols{display:grid;gap:1.25rem;grid-template-columns:minmax(0,1fr)}
@media(min-width:900px){.sm-cols{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}}
.sm-ctl{display:grid;gap:1.05rem;align-content:start;align-self:start}
.sm-ctl label{display:block;font-size:.8rem;font-weight:700}
.sm-ctl .v{float:right;font-weight:800;color:var(--brand-deep)}
.sm-ctl input[type=range]{width:100%;accent-color:var(--brand);margin:.35rem 0 .1rem}
.sm-ctl small{display:block;font-size:.7rem;color:var(--muted-foreground);line-height:1.35}
.sm-sec{font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-foreground);border-top:1px solid var(--border);padding-top:.8rem;margin-top:.1rem}
.sm-btn{display:inline-flex;align-items:center;justify-content:center;gap:.4rem;border:1px solid var(--input);background:var(--card);border-radius:.55rem;height:2.2rem;padding:0 .9rem;font:inherit;font-size:.8rem;font-weight:700;color:var(--foreground);cursor:pointer}
.sm-btn:hover{background:var(--accent)}
.sm-btn.pri{background:var(--brand);border-color:var(--brand);color:#fff}.sm-btn.pri:hover{background:var(--brand-deep)}
.sm-kpis{display:grid;gap:.9rem;grid-template-columns:repeat(2,minmax(0,1fr))}
@media(min-width:900px){.sm-kpis{grid-template-columns:repeat(4,minmax(0,1fr))}}
.sm-kpi{border-radius:.8rem;border:1px solid var(--border);background:var(--card);padding:.9rem 1rem;box-shadow:var(--shadow-card)}
.sm-kpi .l{font-size:.72rem;font-weight:700;color:var(--muted-foreground)}
.sm-kpi .n{font-size:1.55rem;font-weight:800;line-height:1.15;margin:.15rem 0}
.sm-kpi .s{font-size:.7rem;color:var(--muted-foreground)}
.sm-heat{display:grid;gap:3px;font-size:.66rem}
.sm-heat button{border:0;border-radius:4px;height:1.9rem;cursor:pointer;font:inherit;font-weight:800;color:var(--foreground);transition:transform .12s,outline-color .12s;outline:2px solid transparent;outline-offset:1px}
.sm-heat button:hover{transform:scale(1.08);z-index:1}
.sm-heat button.at{outline-color:var(--foreground)}
.sm-heat .ax{display:flex;align-items:center;justify-content:center;color:var(--muted-foreground);font-weight:700}
.sm-nota{font-size:.74rem;color:var(--muted-foreground);line-height:1.5;margin-top:1rem;border-top:1px solid var(--border);padding-top:.8rem}
.sm-pol{display:inline-flex;align-items:center;gap:.35rem;margin-right:.9rem;font-size:.72rem;font-weight:700;color:var(--muted-foreground)}
.sm-pol i{display:inline-block;width:.9rem;height:.25rem;border-radius:2px}
`;
document.head.insertAdjacentHTML("beforeend", `<style>${css}</style>`);

const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const mil = (v) => (Math.abs(v) >= 1e6 ? `R$ ${(v / 1e6).toFixed(2).replace(".", ",")} mi` : `R$ ${Math.round(v / 1e3).toLocaleString("pt-BR")} mil`);
const T = { fontSize: 11, fill: "var(--muted-foreground)" };
const CA = { contentStyle: { borderRadius: 10, border: "1px solid var(--border)", fontSize: 12 } };
const COR = { grade: "var(--chart-5)", acaso: "var(--chart-2)", modelo: "var(--chart-1)" };

/* gerador pseudoaleatório reprodutível */
function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6d2b79f5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const exp = (u) => -Math.log(1 - u);
const pctl = (a, q) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.max(0, Math.floor(q * (s.length - 1))))]; };

/* política do modelo num dia: candidatas já vêm ordenadas por probabilidade */
function escolhidas(d, lim, cap) {
  let n = 0;
  while (n < d.c.length && n < cap && d.c[n][2] >= lim) n++;
  return n;
}

/* valor esperado (sem sorteio) de uma política: usado na curva e no mapa de decisão */
function esperado(P, lim, cap) {
  let custo = 0, evit = 0, ant = 0, uteis = 0;
  const cf = (m) => P.horas * CAP[m] * P.margem;
  for (const d of DIAS) {
    const n = escolhidas(d, lim, cap);
    ant += n;
    d.c.forEach((e, k) => {
      if (!e[3]) return;
      if (k < n) { uteis++; evit += P.efic; custo += (1 - P.efic) * cf(e[0]); } else custo += cf(e[0]);
    });
    d.f.forEach((e) => { custo += cf(e[0]); });
  }
  custo += ant * P.custoAnt;
  return { custo, evit, ant, uteis };
}
function statusQuo(P) {
  let c = 0;
  for (const d of DIAS) { d.c.forEach((e) => { if (e[3]) c += P.horas * CAP[e[0]] * P.margem; }); d.f.forEach((e) => { c += P.horas * CAP[e[0]] * P.margem; }); }
  return c;
}

/* Monte Carlo: horas de parada ~ Gama(2), eficácia ~ Bernoulli, política ao acaso sorteada; dias reamostrados (bootstrap) */
function monteCarlo(P, seed) {
  const r = rng(seed);
  const parada = () => (exp(r()) + exp(r())) * P.horas / 2;
  function rodada(ordem, acumular) {
    const tot = { grade: 0, acaso: 0, modelo: 0, evit: 0 };
    const serie = acumular ? [] : null;
    for (const di of ordem) {
      const d = DIAS[di];
      const n = escolhidas(d, P.lim, P.cap);
      const sorteio = new Set();
      while (sorteio.size < n) sorteio.add(Math.floor(r() * d.c.length));
      tot.modelo += n * P.custoAnt; tot.acaso += n * P.custoAnt;
      d.c.forEach((e, k) => {
        if (!e[3]) return;
        const c = parada() * CAP[e[0]] * P.margem;
        tot.grade += c;
        const evitaM = k < n && r() < P.efic, evitaA = sorteio.has(k) && r() < P.efic;
        if (!evitaM) tot.modelo += c; else tot.evit++;
        if (!evitaA) tot.acaso += c;
      });
      d.f.forEach((e) => { const c = parada() * CAP[e[0]] * P.margem; tot.grade += c; tot.modelo += c; tot.acaso += c; });
      if (serie) serie.push([tot.grade, tot.acaso, tot.modelo]);
    }
    return { tot, serie };
  }
  const crono = [...Array(N).keys()];
  const series = [];
  for (let k = 0; k < Math.min(200, Math.max(80, RUNS / 4)); k++) series.push(rodada(crono, true).serie);
  const banda = crono.map((i) => {
    const g = series.map((s) => s[i][0]), a = series.map((s) => s[i][1]), m = series.map((s) => s[i][2]);
    const media = (v) => v.reduce((x, y) => x + y, 0) / v.length;
    return { dia: R.dias[i].slice(5).split("-").reverse().join("/"), grade: media(g), acaso: media(a), modelo: media(m), faixa: [pctl(m, 0.1), pctl(m, 0.9)] };
  });
  const eco = [], ecoA = [], evit = [];
  for (let k = 0; k < RUNS; k++) {
    const ordem = Array.from({ length: N }, () => Math.floor(r() * N));
    const { tot } = rodada(ordem, false);
    eco.push(tot.grade - tot.modelo); ecoA.push(tot.grade - tot.acaso); evit.push(tot.evit);
  }
  return { banda, eco, ecoA, evit };
}

function Contador({ valor, fmt }) {
  const [v, setV] = useState(valor);
  const ref = useRef(valor);
  useEffect(() => {
    const de = ref.current, ate = valor, t0 = performance.now();
    let id;
    const passo = (t) => {
      const f = Math.min(1, (t - t0) / 700), e = 1 - Math.pow(1 - f, 3);
      setV(de + (ate - de) * e);
      if (f < 1) id = requestAnimationFrame(passo); else ref.current = ate;
    };
    id = requestAnimationFrame(passo);
    return () => { cancelAnimationFrame(id); ref.current = ate; };
  }, [valor]);
  return fmt(v);
}

function Controle({ rotulo, valor, txt, min, max, step, onChange, ajuda }) {
  return html`<div><label>${rotulo}<span class="v">${txt}</span></label>
    <input type="range" min=${min} max=${max} step=${step} value=${valor} onInput=${(e) => onChange(+e.target.value)} />
    ${ajuda && html`<small>${ajuda}</small>`}</div>`;
}

const PADRAO = window.INICIAL || { lim: 30, cap: 6, margem: 8, horas: 8, custoAnt: 400, efic: 0.9 };
const RUNS = window.RUNS || 500;

function Simulador() {
  const [P, setP] = useState(PADRAO);
  const [seed, setSeed] = useState(7);
  const [Pd, setPd] = useState(P);                // parâmetros "assentados" (debounce do Monte Carlo)
  useEffect(() => { const id = setTimeout(() => setPd(P), 180); return () => clearTimeout(id); }, [P]);
  const set = (k) => (v) => setP({ ...P, [k]: v });

  const base = useMemo(() => statusQuo(Pd), [Pd.horas, Pd.margem]);
  const ev = useMemo(() => esperado(Pd, Pd.lim, Pd.cap), [Pd]);
  const mc = useMemo(() => monteCarlo(Pd, seed), [Pd, seed]);
  const curva = useMemo(() => {
    const out = [];
    for (let l = 0; l <= 95; l += 5) { const e = esperado(Pd, l, Pd.cap); out.push({ lim: l, custo: e.custo, ant: e.ant }); }
    return out;
  }, [Pd]);
  const otimo = curva.reduce((a, b) => (b.custo < a.custo ? b : a));
  const LIMS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90], CAPS = [1, 2, 3, 4, 6, 8, 10, 12, 15, 20];
  const mapa = useMemo(() => CAPS.map((c) => LIMS.map((l) => base - esperado(Pd, l, c).custo)), [Pd, base]);
  const mapaMax = Math.max(...mapa.flat().map(Math.abs), 1);

  const ecoMedia = mc.eco.reduce((a, b) => a + b, 0) / mc.eco.length;
  const ecoA = mc.ecoA.reduce((a, b) => a + b, 0) / mc.ecoA.length;
  const p10 = pctl(mc.eco, 0.1), p90 = pctl(mc.eco, 0.9);
  const probPositiva = mc.eco.filter((v) => v > 0).length / mc.eco.length;
  const gastoAnt = ev.ant * Pd.custoAnt;
  const hist = useMemo(() => {
    const lo = Math.min(...mc.eco, ...mc.ecoA), hi = Math.max(...mc.eco, ...mc.ecoA), nb = 24, w = (hi - lo) / nb || 1;
    const b = Array.from({ length: nb }, (_, k) => ({ x: lo + (k + 0.5) * w, modelo: 0, acaso: 0 }));
    mc.eco.forEach((v) => b[Math.min(nb - 1, Math.floor((v - lo) / w))].modelo++);
    mc.ecoA.forEach((v) => b[Math.min(nb - 1, Math.floor((v - lo) / w))].acaso++);
    return b;
  }, [mc]);

  const corMapa = (v) => v >= 0 ? `color-mix(in oklab, var(--success) ${Math.round(12 + 78 * v / mapaMax)}%, var(--card))`
    : `color-mix(in oklab, var(--chart-5) ${Math.round(12 + 78 * -v / mapaMax)}%, var(--card))`;

  return html`<div class="sm-wrap">
    <section class="sm-hero">
      <div><span class="sm-eyebrow">Gêmeo digital da manutenção · cenário ${window.CENARIO || "Padrão"}</span>
        <h2>E se a fábrica tivesse seguido o modelo?</h2>
        <p>Escolha uma política e as premissas de custo. O simulador repete os ${Math.round(MESES)} meses de 2023 da validação temporal, com as falhas reais e
          as probabilidades que o modelo deu às 05:00 de cada dia, e roda ${mc.eco.length} cenários de Monte Carlo para mostrar a incerteza.</p></div>
      <div style=${{ display: "flex", gap: ".5rem" }}>
        <button class="sm-btn" onClick=${() => setSeed(seed + 1)}>Sortear novos cenários</button>
        <button class="sm-btn pri" onClick=${() => setP({ ...P, lim: otimo.lim })}>Usar limiar ótimo (${otimo.lim}%)</button>
      </div>
    </section>

    <div class="sm-grid">
      <aside class="sm-card sm-ctl" aria-label="Parâmetros">
        <div><h3 class="sm-h">Política</h3><p class="sm-sub">Antecipar = fazer a preventiva da peça na própria manhã, antes da janela de risco, em vez de esperar o dia da grade.</p></div>
        <${Controle} rotulo="Limiar de risco" valor=${P.lim} txt=${P.lim + "%"} min=${0} max=${95} step=${5} onChange=${set("lim")}
          ajuda="Antecipa só peças com probabilidade acima deste valor." />
        <${Controle} rotulo="Capacidade da equipe" valor=${P.cap} txt=${P.cap + " por dia"} min=${1} max=${20} step=${1} onChange=${set("cap")}
          ajuda="Máximo de antecipações por dia, das mais arriscadas para as menos." />
        <p class="sm-sec">Premissas de custo</p>
        <${Controle} rotulo="Margem por unidade produzida" valor=${P.margem} txt=${BRL.format(P.margem)} min=${1} max=${30} step=${1} onChange=${set("margem")}
          ajuda=${`Custo da hora parada = capacidade nominal da máquina (80 a 150 un/h, do cadastro) × margem.`} />
        <${Controle} rotulo="Parada não planejada por falha" valor=${P.horas} txt=${P.horas + " h"} min=${1} max=${24} step=${1} onChange=${set("horas")}
          ajuda=${`Média; cada falha sorteia uma duração (distribuição Gama). O reparo em si leva ~${S.duracaoMin.corretiva} min nos registros; o resto é espera e diagnóstico.`} />
        <${Controle} rotulo="Custo de uma antecipação" valor=${P.custoAnt} txt=${BRL.format(P.custoAnt)} min=${50} max=${3000} step=${50} onChange=${set("custoAnt")}
          ajuda="Equipe fora da programação + parada planejada curta. A peça em si não entra: seria trocada no dia seguinte de qualquer forma." />
        <${Controle} rotulo="Eficácia da antecipação" valor=${Math.round(P.efic * 100)} txt=${Math.round(P.efic * 100) + "%"} min=${50} max=${100} step=${5} onChange=${(v) => setP({ ...P, efic: v / 100 })}
          ajuda="Chance de a antecipação realmente evitar a falha." />
        <button class="sm-btn" onClick=${() => setP(PADRAO)}>Restaurar padrão</button>
      </aside>

      <div style=${{ display: "grid", gap: "1.25rem", minWidth: 0 }}>
        <div class="sm-kpis">
          <div class="sm-kpi" style=${{ borderLeft: "4px solid var(--success)" }}><div class="l">Economia vs. só a grade</div>
            <div class="n" style=${{ color: ecoMedia >= 0 ? "var(--success)" : "var(--chart-5)" }}><${Contador} valor=${ecoMedia} fmt=${mil} /></div>
            <div class="s">em ${Math.round(MESES)} meses · 80% dos cenários entre ${mil(p10)} e ${mil(p90)}</div></div>
          <div class="sm-kpi" style=${{ borderLeft: "4px solid var(--brand)" }}><div class="l">Falhas evitadas</div>
            <div class="n"><${Contador} valor=${ev.evit} fmt=${(v) => Math.round(v)} /> <span style=${{ fontSize: ".9rem", color: "var(--muted-foreground)" }}>de ${NFALHAS}</span></div>
            <div class="s">${Math.round((100 * ev.evit) / NFALHAS)}% das paradas não planejadas</div></div>
          <div class="sm-kpi" style=${{ borderLeft: "4px solid var(--amber)" }}><div class="l">Antecipações</div>
            <div class="n"><${Contador} valor=${ev.ant} fmt=${(v) => Math.round(v).toLocaleString("pt-BR")} /></div>
            <div class="s">${ev.ant ? Math.round((100 * ev.uteis) / ev.ant) : 0}% acertaram uma peça que ia falhar · ${(ev.ant / N).toFixed(1).replace(".", ",")} por dia</div></div>
          <div class="sm-kpi" style=${{ borderLeft: "4px solid var(--violet)" }}><div class="l">Retorno por real investido</div>
            <div class="n">${gastoAnt ? `${((ecoMedia + gastoAnt) / gastoAnt).toFixed(1).replace(".", ",")}×` : "–"}</div>
            <div class="s">${Math.round(probPositiva * 100)}% dos cenários com economia · ao acaso: ${mil(ecoA)}</div></div>
        </div>

        <section class="sm-card" style=${{ borderLeftColor: "var(--brand)" }}>
          <h3 class="sm-h">Custo acumulado de paradas e antecipações · 2023</h3>
          <p class="sm-sub">Mesmo número de antecipações por dia nas duas políticas ativas: a diferença entre a linha amarela e a azul é o valor da ordem dada pelo modelo. Faixa = 80% dos cenários.</p>
          <div style=${{ margin: ".6rem 0 .2rem" }}>
            <span class="sm-pol"><i style=${{ background: COR.grade }}></i>Só a grade de 15 dias</span>
            <span class="sm-pol"><i style=${{ background: COR.acaso }}></i>Antecipar ao acaso</span>
            <span class="sm-pol"><i style=${{ background: COR.modelo }}></i>Antecipar pelo modelo</span>
          </div>
          <${ResponsiveContainer} width="100%" height=${300}>
            <${ComposedChart} data=${mc.banda} key=${seed + JSON.stringify(Pd)} margin=${{ left: 10, right: 10 }}>
              <${CartesianGrid} stroke="var(--border)" vertical=${false} />
              <${XAxis} dataKey="dia" tick=${T} interval=${29} />
              <${YAxis} tick=${T} tickFormatter=${mil} width=${80} />
              <${Tooltip} ...${CA} formatter=${(v, n) => [Array.isArray(v) ? `${mil(v[0])} – ${mil(v[1])}` : mil(v), n]} />
              <${Area} dataKey="faixa" name="faixa do modelo (80%)" stroke="none" fill=${COR.modelo} fillOpacity=${0.15} animationDuration=${1600} />
              <${Line} dataKey="grade" name="Só a grade" stroke=${COR.grade} strokeWidth=${2.5} dot=${false} animationDuration=${1600} />
              <${Line} dataKey="acaso" name="Ao acaso" stroke=${COR.acaso} strokeWidth=${2.5} dot=${false} animationDuration=${1600} />
              <${Line} dataKey="modelo" name="Pelo modelo" stroke=${COR.modelo} strokeWidth=${3} dot=${false} animationDuration=${1600} />
            <//>
          <//>
        </section>

        <div class="sm-cols">
          <section class="sm-card" style=${{ borderLeftColor: "var(--amber)" }}>
            <h3 class="sm-h">Custo total × limiar de risco</h3>
            <p class="sm-sub">Com capacidade de ${Pd.cap}/dia. Limiar baixo gasta com antecipações inúteis; alto deixa falhas passarem. Clique na curva para escolher.</p>
            <${ResponsiveContainer} width="100%" height=${250}>
              <${LineChart} data=${curva} margin=${{ left: 10, right: 16, top: 10 }} onClick=${(e) => e && e.activeLabel !== undefined && setP({ ...P, lim: +e.activeLabel })}>
                <${CartesianGrid} stroke="var(--border)" vertical=${false} />
                <${XAxis} dataKey="lim" tick=${T} tickFormatter=${(v) => v + "%"} />
                <${YAxis} tick=${T} tickFormatter=${mil} width=${80} domain=${["auto", "auto"]} />
                <${Tooltip} ...${CA} labelFormatter=${(v) => `limiar ${v}%`} formatter=${(v) => [mil(v), "custo total"]} />
                <${ReferenceLine} y=${base} stroke=${COR.grade} strokeDasharray="5 4" label=${{ value: "só a grade", fontSize: 10, fill: "var(--muted-foreground)", position: "insideTopRight" }} />
                <${ReferenceLine} x=${Pd.lim} stroke="var(--foreground)" strokeDasharray="3 3" />
                <${Line} dataKey="custo" stroke="var(--amber)" strokeWidth=${3} dot=${{ r: 3 }} activeDot=${{ r: 6 }} />
                <${ReferenceDot} x=${otimo.lim} y=${otimo.custo} r=${7} fill="var(--success)" stroke="#fff" strokeWidth=${2}
                  label=${{ value: `ótimo ${otimo.lim}%`, position: "top", fontSize: 11, fontWeight: 800, fill: "var(--success)" }} />
              <//>
            <//>
          </section>
          <section class="sm-card" style=${{ borderLeftColor: "var(--success)" }}>
            <h3 class="sm-h">Distribuição da economia (${mc.eco.length} cenários)</h3>
            <p class="sm-sub">Cada cenário reamostra os dias de 2023 e sorteia durações de parada e sucesso das antecipações. Modelo em azul, ao acaso em amarelo.</p>
            <${ResponsiveContainer} width="100%" height=${250}>
              <${BarChart} data=${hist} barGap=${0} margin=${{ left: 0, right: 10, top: 10 }}>
                <${CartesianGrid} stroke="var(--border)" vertical=${false} />
                <${XAxis} dataKey="x" tick=${T} tickFormatter=${mil} interval=${5} />
                <${YAxis} tick=${T} width=${30} />
                <${Tooltip} ...${CA} labelFormatter=${(v) => `economia ≈ ${mil(v)}`} />
                <${ReferenceLine} x=${hist.reduce((a, b) => (Math.abs(b.x) < Math.abs(a.x) ? b : a)).x} stroke="var(--foreground)" />
                <${Bar} dataKey="acaso" name="ao acaso" fill=${COR.acaso} fillOpacity=${0.7} radius=${[3, 3, 0, 0]} />
                <${Bar} dataKey="modelo" name="pelo modelo" fill=${COR.modelo} fillOpacity=${0.85} radius=${[3, 3, 0, 0]} />
              <//>
            <//>
          </section>
        </div>

        <section class="sm-card" style=${{ borderLeftColor: "var(--violet)" }}>
          <h3 class="sm-h">Mapa de decisão · economia por limiar e capacidade</h3>
          <p class="sm-sub">Cada célula é uma política (valor esperado em ${Math.round(MESES)} meses). Verde economiza, vermelho custa mais que só seguir a grade. Clique para aplicar.</p>
          <div class="sm-heat" style=${{ gridTemplateColumns: `3.2rem repeat(${LIMS.length}, minmax(0,1fr))`, marginTop: ".8rem" }}>
            <div class="ax">cap. ↓</div>${LIMS.map((l) => html`<div key=${l} class="ax">${l}%</div>`)}
            ${CAPS.map((c, i) => html`<${React.Fragment} key=${c}>
              <div class="ax">${c}/dia</div>
              ${LIMS.map((l, j) => html`<button key=${l} class=${P.cap === c && P.lim === l ? "at" : ""} style=${{ background: corMapa(mapa[i][j]) }}
                title=${`limiar ${l}% · ${c}/dia · ${mil(mapa[i][j])}`} onClick=${() => setP({ ...P, lim: l, cap: c })}>${Math.round(mapa[i][j] / 1e3)}</button>`)}
            <//>`)}
          </div>
          <p class="sm-sub" style=${{ marginTop: ".5rem" }}>Valores em R$ mil. Eixo horizontal: limiar de risco.</p>
          <p class="sm-nota"><b>Como ler.</b> Os dados de manutenção mostram o mesmo custo de peça na preventiva e na corretiva
            (mediana: A ${BRL.format(S.custoPeca.A)}, B ${BRL.format(S.custoPeca.B)}, C ${BRL.format(S.custoPeca.C)}, D ${BRL.format(S.custoPeca.D)}),
            então o ganho vem só de trocar parada não planejada por parada planejada. Margem, horas de parada e custo da antecipação são premissas: ajuste-as à realidade da planta.${" "}${NFORA} das ${NFALHAS} falhas aconteceram fora da janela de risco da grade e não podem ser antecipadas por nenhuma política.
            Período: validação temporal (${R.dias[0].split("-").reverse().join("/")} a ${R.dias[N - 1].split("-").reverse().join("/")}); o período de teste do Kaggle tem falhas ocultas e não entra aqui.</p>
        </section>
      </div>
    </div>
  </div>`;
}

ReactDOM.createRoot(document.getElementById("root")).render(html`<${Simulador} />`);

function ajustarAltura() {
  const f = window.frameElement;
  if (!f) return;
  const h = Math.ceil(document.getElementById("root").getBoundingClientRect().height) + 4;
  f.style.height = h + "px"; f.setAttribute("height", h);
  if (f.parentElement) f.parentElement.style.height = h + "px";
}
new ResizeObserver(ajustarAltura).observe(document.getElementById("root"));
window.addEventListener("load", ajustarAltura);
setTimeout(ajustarAltura, 300);
