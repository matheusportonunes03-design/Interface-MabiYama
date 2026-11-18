/* MaBiYama · conteúdo do painel (porte do componente do Lovable para React + Recharts sem build).
   Recebe window.DADOS (montado pelo app.py) e window.ABA ("model" | "eda"). */
const { useState } = React;
const html = htm.bind(React.createElement);
const {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  LineChart, Line, ReferenceLine, AreaChart, Area, Legend, Cell,
} = Recharts;

const D = window.DADOS;
const Q = { brand: "var(--chart-1)", amber: "var(--chart-2)", violet: "var(--chart-3)", sky: "var(--chart-4)", red: "var(--chart-5)" };
const T = { fontSize: 11, fill: "var(--muted-foreground)" };
const CA = { contentStyle: { borderRadius: 10, border: "1px solid var(--border)", fontSize: 12 } };

/* ícones lucide (mesmos traçados do Lovable) */
const ICONES = {
  "triangle-alert": ["m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3", "M12 9v4", "M12 17h.01"],
  gauge: ["m12 14 4-4", "M3.34 19a10 10 0 1 1 17.32 0"],
  wrench: ["M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z"],
  "chevron-down": ["m6 9 6 6 6-6"],
  "arrow-right": ["M5 12h14", "m12 5 7 7-7 7"],
  database: ["M3 5V19A9 3 0 0 0 21 19V5", "M3 12A9 3 0 0 0 21 12"],
  cpu: ["M12 20v2", "M12 2v2", "M17 20v2", "M17 2v2", "M2 12h2", "M2 17h2", "M2 7h2", "M20 12h2", "M20 17h2", "M20 7h2", "M7 20v2", "M7 2v2"],
};
function Icone({ nome, className = "" }) {
  const extra = nome === "database"
    ? html`<ellipse cx="12" cy="5" rx="9" ry="3" />`
    : nome === "cpu"
      ? html`<rect x="4" y="4" width="16" height="16" rx="2" /><rect x="8" y="8" width="8" height="8" rx="1" />`
      : null;
  return html`<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class=${"lucide " + className}>
    ${extra}${ICONES[nome].map((d, i) => html`<path key=${i} d=${d} />`)}</svg>`;
}

/* classes do Button (shadcn) já resolvidas como o tailwind-merge faria */
const BTN = "inline-flex items-center gap-2 rounded-md text-sm font-medium cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 disabled:cursor-not-allowed [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0";
const BTN_GHOST_KPI = BTN + " hover:text-accent-foreground h-auto w-full justify-start whitespace-normal p-0 text-left hover:bg-transparent";
const BTN_OUTLINE = BTN + " justify-center whitespace-nowrap border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground h-9 px-4 py-2";
const BTN_ALERTA = BTN + " border border-input shadow-sm hover:bg-accent hover:text-accent-foreground h-auto justify-between whitespace-normal bg-card p-3 text-left";

function irPara(id) {
  const t = document.getElementById(id);
  t?.scrollIntoView({ behavior: "smooth", block: "start" });
  t?.focus({ preventScroll: true });
}

function Cartao({ title, accent = "border-l-brand", children, className = "", id }) {
  return html`<section id=${id} tabIndex="-1" class=${`card-canvas min-w-0 scroll-mt-6 ${accent} ${className}`}>
    <h3 class="mb-3 text-base font-extrabold text-foreground">${title}</h3>${children}</section>`;
}

function Kpi({ icone, label, value, sub, accent, detail, target }) {
  const [aberto, setAberto] = useState(false);
  const corpo = html`
    <div class="rounded-lg bg-secondary p-3 text-brand"><${Icone} nome=${icone} className="h-5 w-5" /></div>
    <div class="min-w-0">
      <p class="text-xs font-semibold text-muted-foreground">${label}</p>
      <p class="text-2xl font-extrabold text-foreground">${value}</p>
      <p class="text-xs text-muted-foreground">${sub}</p>
    </div>`;
  return html`<div class=${`card-canvas min-w-0 ${accent}`}>
    ${detail
      ? html`<button class=${BTN_GHOST_KPI} aria-expanded=${aberto} onClick=${() => setAberto(!aberto)}>
          ${corpo}<${Icone} nome="chevron-down" className=${`ml-auto transition-transform ${aberto ? "rotate-180" : ""}`} /></button>`
      : html`<div class="flex items-center gap-4">${corpo}</div>`}
    ${aberto && html`<div class="mt-4 border-t border-border pt-3">
      <p class="text-sm text-muted-foreground">${detail}</p>
      <button class=${BTN_OUTLINE + " mt-3"} onClick=${() => target && irPara(target)}>Ver insight principal <${Icone} nome="arrow-right" /></button>
    </div>`}
  </div>`;
}

function corBarra(p) { return p > 60 ? "bg-violet" : p > 40 ? "bg-amber" : "bg-brand"; }

function Modelagem({ dia }) {
  const k = D.kpi;
  return html`<div class="grid gap-5">
    <div class="grid gap-5 md:grid-cols-4">
      <${Kpi} icone="triangle-alert" label="Peças em alto risco" value=${String(dia.altoRisco)} sub="prob. > 50% até 06:00 amanhã"
        accent="border-l-violet" target="prioridades"
        detail=${`${dia.altoRisco} pares máquina–peça apresentam risco acima de 50% para ${dia.fimCurto}. A lista ordena as prioridades de inspeção para a próxima janela de manutenção.`} />
      <${Kpi} icone="gauge" label="AUC-PR (validação temporal)" value=${k.ap} sub=${`Kaggle público: ${k.apKaggle}`} accent="border-l-brand" target="desempenho"
        detail=${`AUC-PR (precisão média) resume precisão e recall, útil para falhas raras. Na validação temporal (3 janelas de 2023) o modelo fica em ${k.ap}, contra ${k.baseline} de uma escolha ao acaso. No Kaggle público a previsão atual marca ${k.apKaggle}.`} />
      <${Kpi} icone="wrench" label="Recall @ top-20" value=${k.recall20} sub="falhas capturadas na lista" accent="border-l-amber" target="confusao"
        detail=${`Na validação, as 20 maiores prioridades de cada dia capturam ${k.recall20} das falhas. A matriz mostra acertos e erros no limiar de 0,5; é uma avaliação distinta do corte top-20.`} />
      <${Kpi} icone="cpu" label="Última previsão" value="05:00" sub=${`${dia.execCurto} · ${k.pares} pares máquina×peça`} accent="border-l-brand-sky" target="execucao"
        detail=${`Execução às 05:00 de ${dia.execCurto}, avaliando quatro peças em cada uma das ${k.maquinas} máquinas. A previsão considera a janela até 06:00 do dia seguinte.`} />
    </div>
    <div class="grid gap-5 lg:grid-cols-5">
      <${Cartao} id="prioridades" title="Prioridade de manutenção · hoje" accent="border-l-violet" className="lg:col-span-3 bg-violet-soft/40">
        <div class="overflow-x-auto"><table class="w-full min-w-[560px] text-sm">
          <thead><tr class="text-left text-xs text-muted-foreground">
            <th class="pb-2">#</th><th>Máquina</th><th>Modelo</th><th>Peça</th><th>Idade</th><th class="w-2/5">Prob. de falha</th></tr></thead>
          <tbody>${dia.top.map((e, t) => html`<tr key=${t} class="border-t border-border">
            <td class="py-2 font-bold text-muted-foreground">${t + 1}</td><td class="font-bold">${e.machine}</td>
            <td>${e.model}</td><td>${e.comp}</td><td>${e.age === null ? "–" : `${e.age} a`}</td>
            <td><div class="flex items-center gap-2"><div class="h-2 flex-1 rounded-full bg-secondary">
              <div class=${`h-2 rounded-full ${corBarra(e.prob)}`} style=${{ width: `${e.prob}%` }}></div></div>
              <span class="w-9 text-right font-bold">${e.prob}%</span></div></td></tr>`)}</tbody>
        </table></div>
      <//>
      <${Cartao} title="Importância das variáveis" className="lg:col-span-2">
        <${ResponsiveContainer} width="100%" height=${380}>
          <${BarChart} data=${D.imp} layout="vertical" margin=${{ left: 30 }}>
            <${XAxis} type="number" tick=${T} /><${YAxis} dataKey="f" type="category" tick=${T} width=${110} />
            <${Tooltip} ...${CA} /><${Bar} dataKey="v" name="importância" fill=${Q.brand} radius=${[0, 6, 6, 0]} />
          <//>
        <//>
      <//>
    </div>
    <div class="grid gap-5 lg:grid-cols-3">
      <${Cartao} id="desempenho" title="Precisão × recall (validação temporal)" accent="border-l-brand">
        <${ResponsiveContainer} width="100%" height=${240}>
          <${LineChart} data=${D.pr}>
            <${CartesianGrid} stroke="var(--border)" /><${XAxis} dataKey="recall" tick=${T} type="number" domain=${[0, 1]} />
            <${YAxis} tick=${T} domain=${[0, 1]} /><${Tooltip} ...${CA} />
            <${Line} dataKey="precision" name="Precisão" stroke=${Q.brand} strokeWidth=${3} dot=${false} />
            <${Line} dataKey="baseline" name="Ao acaso" stroke=${Q.sky} strokeDasharray="5 5" dot=${false} />
          <//>
        <//>
      <//>
      <${Cartao} title="Calibração das probabilidades" accent="border-l-amber">
        <${ResponsiveContainer} width="100%" height=${240}>
          <${LineChart} data=${D.cal}>
            <${CartesianGrid} stroke="var(--border)" /><${XAxis} dataKey="bin" tick=${T} type="number" domain=${[0, 1]} />
            <${YAxis} tick=${T} domain=${[0, 1]} /><${Tooltip} ...${CA} />
            <${ReferenceLine} segment=${[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke=${Q.sky} strokeDasharray="5 5" />
            <${Line} dataKey="real" name="Taxa real" stroke=${Q.amber} strokeWidth=${3} />
          <//>
        <//>
      <//>
      <${Cartao} id="confusao" title="Matriz de confusão (limiar 0,5)" accent="border-l-violet">
        <div class="grid grid-cols-[auto_1fr_1fr] gap-2 text-center text-sm">
          <div></div>
          <div class="text-xs font-bold text-muted-foreground">Prev. ok</div>
          <div class="text-xs font-bold text-muted-foreground">Prev. falha</div>
          <div class="self-center text-xs font-bold text-muted-foreground">Real ok</div>
          <div class="rounded-lg bg-secondary py-8 text-2xl font-extrabold">${D.cm.tn}</div>
          <div class="rounded-lg bg-amber/30 py-8 text-2xl font-extrabold">${D.cm.fp}</div>
          <div class="self-center text-xs font-bold text-muted-foreground">Real falha</div>
          <div class="rounded-lg bg-amber/30 py-8 text-2xl font-extrabold">${D.cm.fn}</div>
          <div class="rounded-lg bg-brand py-8 text-2xl font-extrabold text-primary-foreground">${D.cm.tp}</div>
        </div>
      <//>
    </div>
    <section id="execucao" tabIndex="-1" class="scroll-mt-6 border-t border-border py-4">
      <h3 class="font-extrabold">Resumo da última previsão</h3>
      <dl class="mt-3 grid gap-4 sm:grid-cols-3">
        <div><dt class="text-sm text-muted-foreground">Execução</dt><dd class="font-bold">${dia.execCurto} · 05:00</dd></div>
        <div><dt class="text-sm text-muted-foreground">Cobertura</dt><dd class="font-bold">${k.maquinas} máquinas · ${k.pares} pares máquina×peça</dd></div>
        <div><dt class="text-sm text-muted-foreground">Fim da janela</dt><dd class="font-bold">${dia.fimCurto} · 06:00</dd></div>
      </dl>
    </section>
  </div>`;
}

function Exploratoria() {
  const e = D.eda;
  return html`<div class="grid gap-5">
    <div class="grid gap-5 md:grid-cols-4">
      <${Kpi} icone="cpu" label="Máquinas" value=${e.kpi.maquinas} sub=${e.kpi.maquinasSub} accent="border-l-brand" />
      <${Kpi} icone="triangle-alert" label="Falhas no período" value=${e.kpi.falhas} sub=${e.kpi.falhasSub} accent="border-l-violet" />
      <${Kpi} icone="wrench" label="Manutenções" value=${e.kpi.manut} sub="preventivas · grade de 15 dias" accent="border-l-amber" />
      <${Kpi} icone="database" label="Leituras de sensores" value=${e.kpi.leituras} sub="sensores A–D · vibração · clima" accent="border-l-brand-sky" />
    </div>
    <div class="grid gap-5 lg:grid-cols-3">
      <${Cartao} title="Sinal antes da falha · sensor da peça (48h)" accent="border-l-violet" className="lg:col-span-2">
        <${ResponsiveContainer} width="100%" height=${260}>
          <${LineChart} data=${e.sinal}>
            <${CartesianGrid} stroke="var(--border)" /><${XAxis} dataKey="h" tick=${T} unit="h" />
            <${YAxis} tick=${T} domain=${["auto", "auto"]} /><${Tooltip} ...${CA} /><${Legend} wrapperStyle=${{ fontSize: 12 }} />
            <${ReferenceLine} x=${-24} stroke=${Q.amber} strokeDasharray="4 4" label=${{ value: "janela 24h", fontSize: 11, fill: "var(--muted-foreground)" }} />
            <${Line} dataKey="antes" name="Antes de falha" stroke=${Q.violet} strokeWidth=${2.5} dot=${false} />
            <${Line} dataKey="normal" name="Operação normal" stroke=${Q.sky} strokeWidth=${2} dot=${false} />
          <//>
        <//>
      <//>
      <${Cartao} title="Falhas por peça">
        <${ResponsiveContainer} width="100%" height=${260}>
          <${BarChart} data=${e.porPeca}>
            <${CartesianGrid} stroke="var(--border)" vertical=${false} /><${XAxis} dataKey="c" tick=${T} /><${YAxis} tick=${T} />
            <${Tooltip} ...${CA} />
            <${Bar} dataKey="n" name="Falhas" radius=${[6, 6, 0, 0]}>
              ${e.porPeca.map((_, i) => html`<${Cell} key=${i} fill=${[Q.brand, Q.violet, Q.sky, Q.amber][i]} />`)}
            <//>
          <//>
        <//>
      <//>
    </div>
    <div class="grid gap-5 lg:grid-cols-3">
      <${Cartao} title="Falhas × manutenções por mês" accent="border-l-amber" className="lg:col-span-2">
        <${ResponsiveContainer} width="100%" height=${240}>
          <${AreaChart} data=${e.mensal}>
            <${CartesianGrid} stroke="var(--border)" /><${XAxis} dataKey="m" tick=${T} />
            <${YAxis} yAxisId="a" tick=${T} /><${YAxis} yAxisId="b" orientation="right" tick=${T} />
            <${Tooltip} ...${CA} /><${Legend} wrapperStyle=${{ fontSize: 12 }} />
            <${Area} yAxisId="b" dataKey="manut" name="Manutenções" stroke=${Q.sky} fill=${Q.sky} fillOpacity=${0.25} />
            <${Area} yAxisId="a" dataKey="falhas" name="Falhas" stroke=${Q.amber} fill=${Q.amber} fillOpacity=${0.4} />
          <//>
        <//>
      <//>
      <${Cartao} title="Falhas por máquina, por idade (anos)" accent="border-l-brand">
        <${ResponsiveContainer} width="100%" height=${240}>
          <${BarChart} data=${e.idade}>
            <${XAxis} dataKey="faixa" tick=${T} /><${YAxis} tick=${T} /><${Tooltip} ...${CA} />
            <${Bar} dataKey="taxa" name="Falhas por máquina" fill=${Q.brand} radius=${[4, 4, 0, 0]} />
          <//>
        <//>
      <//>
    </div>
    <div class="grid gap-5 lg:grid-cols-3">
      <${Cartao} title="Alertas de erro: volume × 24h antes de falha" accent="border-l-violet">
        <${ResponsiveContainer} width="100%" height=${220}>
          <${BarChart} data=${e.erros}>
            <${XAxis} dataKey="e" tick=${T} /><${YAxis} yAxisId="a" tick=${T} /><${YAxis} yAxisId="b" orientation="right" tick=${T} unit="%" />
            <${Tooltip} ...${CA} /><${Legend} wrapperStyle=${{ fontSize: 12 }} />
            <${Bar} yAxisId="a" dataKey="total" name="Total" fill=${Q.sky} radius=${[4, 4, 0, 0]} />
            <${Bar} yAxisId="b" dataKey="antes" name="Antes de falha (%)" fill=${Q.violet} radius=${[4, 4, 0, 0]} />
          <//>
        <//>
      <//>
      <${Cartao} title="Falhas por modelo de máquina" accent="border-l-amber">
        <${ResponsiveContainer} width="100%" height=${220}>
          <${BarChart} data=${e.modelos}>
            <${XAxis} dataKey="m" tick=${T} /><${YAxis} tick=${T} /><${Tooltip} ...${CA} /><${Legend} wrapperStyle=${{ fontSize: 12 }} />
            <${Bar} dataKey="maquinas" name="Máquinas" fill=${Q.brand} radius=${[4, 4, 0, 0]} />
            <${Bar} dataKey="falhas" name="Falhas/máquina" fill=${Q.amber} radius=${[4, 4, 0, 0]} />
          <//>
        <//>
      <//>
      <${Cartao} title="Qualidade da base recebida" accent="border-l-brand-sky">
        <table class="w-full text-sm">
          <thead><tr class="text-left text-xs text-muted-foreground"><th class="pb-2">Tabela</th><th>Linhas</th><th>Nulos</th><th>Duplic.</th><th></th></tr></thead>
          <tbody>${e.qualidade.map((q) => html`<tr key=${q.t} class="border-t border-border">
            <td class="py-2 font-bold">${q.t}</td><td>${q.rows}</td><td>${q.miss}%</td><td>${q.dup}%</td>
            <td><span class="rounded-full bg-success/15 px-2 py-0.5 text-xs font-bold text-success">OK</span></td></tr>`)}</tbody>
        </table>
      <//>
    </div>
  </div>`;
}

function Painel() {
  const [iDia, setIDia] = useState(D.diaInicial);
  const dia = D.dias[iDia];
  return html`<div class="bg-background font-sans">
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <section aria-label="Máquinas com maior risco" class="mb-6 border-l-4 border-amber bg-amber/10 p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="flex items-center gap-2 font-extrabold"><${Icone} nome="triangle-alert" className="h-5 w-5 text-violet" /> Atenção: cinco máquinas com maior risco</h2>
          <span class="flex items-center gap-1 text-xs text-muted-foreground">Até 06:00 de
            <select aria-label="Dia da previsão" class="seletor-dia" value=${iDia} onChange=${(ev) => setIDia(Number(ev.target.value))}>
              ${D.dias.map((d, i) => html`<option key=${i} value=${i}>${d.fimLongo}</option>`)}
            </select></span>
        </div>
        <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          ${dia.top.slice(0, 5).map((e) => html`<button key=${e.machine + e.comp} class=${BTN_ALERTA}
              onClick=${() => { if (window.ABA !== "model") return; requestAnimationFrame(() => irPara("prioridades")); }}>
            <span><strong class="block">${e.machine}</strong><span class="text-xs text-muted-foreground">${e.comp} · ${e.model}</span></span>
            <span class="text-xl font-extrabold text-violet">${e.prob}%</span></button>`)}
        </div>
      </section>
      ${window.ABA === "model" ? html`<${Modelagem} dia=${dia} />` : html`<${Exploratoria} />`}
    </main>
    <footer class="mx-auto max-w-7xl px-6 pb-8 text-xs text-muted-foreground">Dados & IA por Poli Júnior · MaBiYama</footer>
  </div>`;
}

ReactDOM.createRoot(document.getElementById("root")).render(html`<${Painel} />`);

/* ajusta a altura do iframe do Streamlit ao conteúdo */
function ajustarAltura() {
  const f = window.frameElement;
  if (!f) return;
  const h = Math.ceil(document.getElementById("root").getBoundingClientRect().height);
  f.style.height = h + "px";
  f.setAttribute("height", h);
  if (f.parentElement) f.parentElement.style.height = h + "px";
}
new ResizeObserver(ajustarAltura).observe(document.getElementById("root"));
window.addEventListener("load", ajustarAltura);
setTimeout(ajustarAltura, 300);
