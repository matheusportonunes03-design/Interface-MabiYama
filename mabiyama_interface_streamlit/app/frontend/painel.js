/* MaBiYama · conteúdo do painel (porte do componente do Lovable para React + Recharts sem build).
   Recebe window.DADOS (montado pelo app.py) e window.ABA ("model" | "eda"). */
const { useState } = React;
const html = htm.bind(React.createElement);
const {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  LineChart, Line, ReferenceLine, AreaChart, Area, Legend, Cell,
} = Recharts;

const D = window.DADOS;
const F = Object.assign({ dia: 0, pecas: [], modelos: [], riscoMin: 0, busca: "", grupos: [], expandir: false }, window.FILTROS || {});
function filtrar(lista) {
  const b = (F.busca || "").trim().toUpperCase();
  return lista.filter((e) => (!F.pecas.length || F.pecas.includes(e.comp)) && (!F.modelos.length || F.modelos.includes(e.model))
    && e.prob >= F.riscoMin && (!b || e.machine.toUpperCase().includes(b)));
}
function resumoFiltros() {
  const p = [];
  if (F.pecas.length) p.push(F.pecas.join(", "));
  if (F.modelos.length) p.push(F.modelos.join(", "));
  if (F.riscoMin > 0) p.push(`risco ≥ ${F.riscoMin}%`);
  if ((F.busca || "").trim()) p.push(`máquina "${F.busca.trim()}"`);
  return p.join(" · ");
}
const Q = { brand: "var(--chart-1)", amber: "var(--chart-2)", violet: "var(--chart-3)", sky: "var(--chart-4)", red: "var(--chart-5)" };
const T = { fontSize: 11, fill: "var(--muted-foreground)" };
const CA = { contentStyle: { borderRadius: 10, border: "1px solid var(--border)", fontSize: 12 } };

/* ícones lucide (mesmos traçados do Lovable) */
const ICONES = {
  "triangle-alert": ["m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3", "M12 9v4", "M12 17h.01"],
  gauge: ["m12 14 4-4", "M3.34 19a10 10 0 1 1 17.32 0"],
  wrench: ["M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z"],
  "chevron-down": ["m6 9 6 6 6-6"],
  lightbulb: ["M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5", "M9 18h6", "M10 22h4"],
  filter: ["M10 20a1 1 0 0 0 .553.895l2 1A1 1 0 0 0 14 21v-7a2 2 0 0 1 .517-1.341L21.74 4.67A1 1 0 0 0 21 3H3a1 1 0 0 0-.742 1.67l7.225 7.989A2 2 0 0 1 10 14z"],
  maximize: ["M15 3h6v6", "M9 21H3v-6", "M21 3l-7 7", "M3 21l7-7"],
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

function Cartao({ title, accent = "border-l-brand", children, className = "", id, insight }) {
  const [aberto, setAberto] = useState(F.expandir);
  return html`<section id=${id} tabIndex="-1" class=${`card-canvas min-w-0 scroll-mt-6 ${accent} ${className}`}>
    <div class="mb-3 flex items-start justify-between gap-3">
      <h3 class="text-base font-extrabold text-foreground">${title}</h3>
      ${insight && html`<button class="insight-btn" aria-expanded=${aberto} onClick=${() => setAberto(!aberto)}>
        <${Icone} nome="lightbulb" className="h-4 w-4" />${aberto ? "Fechar" : "Insight"}</button>`}
    </div>
    ${children}
    ${insight && aberto && html`<p class="insight-txt">${insight}</p>`}</section>`;
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
  const rf = resumoFiltros();
  const num = (t) => parseFloat(String(t).replace("%", "").replace(",", "."));
  const maxAlto = Math.max(1, dia.altoRisco, ...D.dias.map((x) => (x.lista || []).filter((e) => e.prob > 50).length));
  const G = window.Galao;
  return html`<div class="grid gap-5">
    ${G ? html`<div class="xg-grid">
      <${G} label="Peças em alto risco" value=${String(dia.altoRisco)} estado=${dia.altoRisco ? "atenção" : "tranquilo"} alerta=${dia.altoRisco > 0}
        nivel=${(100 * dia.altoRisco) / maxAlto} sub=${`prob. > 50% até 06:00 · nível em relação ao pico do horizonte (${maxAlto})`} onIr=${() => irPara("prioridades")}
        detail=${`${dia.altoRisco} pares máquina–peça apresentam risco acima de 50% para ${dia.fimCurto}. A lista ordena as prioridades de inspeção para a próxima janela de manutenção. O tanque enche até o pico de ${maxAlto} peças de um mesmo dia no horizonte.`} />
      <${G} label="AUC-PR (validação temporal)" value=${k.ap} estado="estável" nivel=${num(k.ap) * 100} sub=${`Kaggle público: ${k.apKaggle}`} onIr=${() => irPara("desempenho")}
        detail=${`AUC-PR (precisão média) resume precisão e recall, útil para falhas raras. Na validação temporal (3 janelas de 2023) o modelo fica em ${k.ap}, contra ${k.baseline} de uma escolha ao acaso. No Kaggle público a previsão atual marca ${k.apKaggle}.`} />
      <${G} label="Recall @ top-20" value=${k.recall20} estado="cheio" nivel=${num(k.recall20)} sub="falhas capturadas na lista" onIr=${() => irPara("confusao")}
        detail=${`Na validação, as 20 maiores prioridades de cada dia capturam ${k.recall20} das falhas. A matriz mostra acertos e erros no limiar de 0,5; é uma avaliação distinta do corte top-20.`} />
      <${G} label="Última previsão" value="05:00" estado="em dia" nivel=${100} sub=${`${dia.execCurto} · ${k.pares} pares máquina×peça cobertos`} onIr=${() => irPara("execucao")}
        detail=${`Execução às 05:00 de ${dia.execCurto}, avaliando quatro peças em cada uma das ${k.maquinas} máquinas. A previsão considera a janela até 06:00 do dia seguinte.`} />
    </div>` : html`
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
    </div>`}
    <div class="grid gap-5 lg:grid-cols-5">
      <${Cartao} id="prioridades" title="Prioridade de manutenção · hoje" accent="border-l-violet" className="lg:col-span-3 bg-violet-soft/40">
        ${rf && html`<p class="mb-3 flex items-center gap-2 text-xs text-muted-foreground"><${Icone} nome="filter" className="h-3.5 w-3.5" />
          Filtros: ${rf} · ${dia.filtrada.length} de ${dia.lista.length} candidatas</p>`}
        ${dia.top.length === 0 ? html`<p class="py-8 text-center text-sm text-muted-foreground">Nenhuma peça atende aos filtros neste dia.</p>` : html`<div class="overflow-x-auto"><table class="w-full min-w-[560px] text-sm">
          <thead><tr class="text-left text-xs text-muted-foreground">
            <th class="pb-2">#</th><th>Máquina</th><th>Modelo</th><th>Peça</th><th>Idade</th><th class="w-2/5">Prob. de falha</th></tr></thead>
          <tbody>${dia.top.map((e, t) => html`<tr key=${t} class="border-t border-border">
            <td class="py-2 font-bold text-muted-foreground">${t + 1}</td><td class="font-bold">${e.machine}</td>
            <td>${e.model}</td><td>${e.comp}</td><td>${e.age === null || e.age === undefined || Number.isNaN(e.age) ? "–" : `${e.age} a`}</td>
            <td><div class="flex items-center gap-2"><div class="h-2 flex-1 rounded-full bg-secondary">
              <div class=${`h-2 rounded-full ${corBarra(e.prob)}`} style=${{ width: `${e.prob}%` }}></div></div>
              <span class="w-9 text-right font-bold">${e.prob}%</span></div></td></tr>`)}</tbody>
        </table></div>`}
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
    ${window.RaioX && html`<${window.RaioX} />`}
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
      <${Cartao} title="Sinal antes da falha · sensor da peça (48h)" accent="border-l-violet" className="lg:col-span-2" insight="O sensor ligado à peça sai do normal cerca de 2 dias antes da falha: em média 0,27 desvio 48 h antes, 0,53 com 24 h e 0,65 na última hora. É essa rampa que o modelo procura às 05:00 de cada dia.">
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
      <${Cartao} title="Falhas por peça" insight="A peça C é a que mais falha (225 no período), seguida de B (174) e A (165). A peça D falha bem menos (116) e quase só nos modelos A e D.">
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
      <${Cartao} title="Falhas × manutenções por mês" accent="border-l-amber" className="lg:col-span-2" insight="As falhas ficam estáveis, entre 44 e 71 por mês, sem tendência, enquanto as preventivas seguem a grade de 15 dias (109 a 187 por mês). O volume de preventivas varia de um mês para outro sem que as falhas acompanhem.">
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
      <${Cartao} title="Falhas por máquina, por idade (anos)" accent="border-l-brand" insight="Máquinas com 12 anos ou mais têm cerca de 9 a 10 falhas cada, contra 5 a 6 nas mais novas. O efeito vem quase todo da peça A, que falha cerca de 5 vezes mais depois dos 11 anos.">
        <${ResponsiveContainer} width="100%" height=${240}>
          <${BarChart} data=${e.idade}>
            <${XAxis} dataKey="faixa" tick=${T} /><${YAxis} tick=${T} /><${Tooltip} ...${CA} />
            <${Bar} dataKey="taxa" name="Falhas por máquina" fill=${Q.brand} radius=${[4, 4, 0, 0]} />
          <//>
        <//>
      <//>
    </div>
    <div class="grid gap-5 lg:grid-cols-3">
      <${Cartao} title="Alertas de erro: volume × 24h antes de falha" accent="border-l-violet" insight="O E1 é o código mais raro (447) e o mais ligado a falha: 31% vêm seguidos de falha em 24 h, contra 13% a 20% dos demais. Os erros que realmente avisam são os lançados às 06h; nos outros horários a maioria é ruído.">
        <${ResponsiveContainer} width="100%" height=${220}>
          <${BarChart} data=${e.erros}>
            <${XAxis} dataKey="e" tick=${T} /><${YAxis} yAxisId="a" tick=${T} /><${YAxis} yAxisId="b" orientation="right" tick=${T} unit="%" />
            <${Tooltip} ...${CA} /><${Legend} wrapperStyle=${{ fontSize: 12 }} />
            <${Bar} yAxisId="a" dataKey="total" name="Total" fill=${Q.sky} radius=${[4, 4, 0, 0]} />
            <${Bar} yAxisId="b" dataKey="antes" name="Antes de falha (%)" fill=${Q.violet} radius=${[4, 4, 0, 0]} />
          <//>
        <//>
      <//>
      <${Cartao} title="Falhas por modelo de máquina" accent="border-l-amber" insight="Os modelos D e A têm menos máquinas, mas mais falhas por máquina (10,7 e 8,9) do que B e C (6,5 e 5,9). A diferença vem principalmente da peça D, que quase só falha nesses dois modelos.">
        <${ResponsiveContainer} width="100%" height=${220}>
          <${BarChart} data=${e.modelos}>
            <${XAxis} dataKey="m" tick=${T} /><${YAxis} tick=${T} /><${Tooltip} ...${CA} /><${Legend} wrapperStyle=${{ fontSize: 12 }} />
            <${Bar} dataKey="maquinas" name="Máquinas" fill=${Q.brand} radius=${[4, 4, 0, 0]} />
            <${Bar} dataKey="falhas" name="Falhas/máquina" fill=${Q.amber} radius=${[4, 4, 0, 0]} />
          <//>
        <//>
      <//>
      <${Cartao} title="Qualidade da base recebida" accent="border-l-brand-sky" insight="Depois do tratamento, nenhuma tabela tem mais de 3,5% de valores vazios nem duplicatas relevantes. Os vazios da telemetria (1,6%) são as leituras de falha do sensor (0 e −999), marcadas por flag.">
        <table class="w-full text-sm">
          <thead><tr class="text-left text-xs text-muted-foreground"><th class="pb-2">Tabela</th><th>Linhas</th><th>Nulos</th><th>Duplic.</th><th></th></tr></thead>
          <tbody>${e.qualidade.map((q) => html`<tr key=${q.t} class="border-t border-border">
            <td class="py-2 font-bold">${q.t}</td><td>${q.rows}</td><td>${q.miss}%</td><td>${q.dup}%</td>
            <td><span class="rounded-full bg-success/15 px-2 py-0.5 text-xs font-bold text-success">OK</span></td></tr>`)}</tbody>
        </table>
      <//>
    </div>
    <${Galeria} />
  </div>`;
}


function Galeria() {
  const todos = D.graficos || [];
  const grupos = [...new Set(todos.map((g) => g.grupo))].filter((g) => !F.grupos.length || F.grupos.includes(g));
  const [aberto, setAberto] = useState(() => new Set(F.expandir ? todos.map((g) => g.n) : []));
  const alterna = (n) => setAberto((a) => { const b = new Set(a); b.has(n) ? b.delete(n) : b.add(n); return b; });
  if (!todos.length) return null;
  return html`<section aria-label="Análises da Etapa 3" class="grid gap-6">
    <div class="border-t border-border pt-5">
      <h2 class="text-xl font-extrabold">Análises da Etapa 3</h2>
      <p class="mt-1 text-sm text-muted-foreground">${todos.length} gráficos da análise exploratória, feitos só com o período de treino. Clique em um gráfico para ampliá-lo e ler o insight.</p>
    </div>
    ${grupos.map((gr) => html`<div key=${gr}>
      <h3 class="mb-3 text-xs font-bold uppercase tracking-widest text-brand-deep">${gr}</h3>
      <div class="grid gap-5 md:grid-cols-2">
        ${todos.filter((g) => g.grupo === gr).map((g) => {
          const ab = aberto.has(g.n);
          return html`<article key=${g.n} class=${`card-canvas min-w-0 border-l-brand ${ab ? "md:col-span-2" : ""}`}>
            <button class="galeria-btn" aria-expanded=${ab} onClick=${() => alterna(g.n)}>
              <span class="flex min-w-0 items-center gap-3">
                <span class="galeria-num">${g.n}</span>
                <span class="truncate text-left text-base font-extrabold text-foreground">${g.titulo}</span>
              </span>
              <${Icone} nome="chevron-down" className=${`h-4 w-4 flex-none text-muted-foreground transition-transform ${ab ? "rotate-180" : ""}`} />
            </button>
            <button class="galeria-img" aria-label=${`${ab ? "Recolher" : "Ampliar"}: ${g.titulo}`} onClick=${() => alterna(g.n)}>
              <img src=${g.src} alt=${g.titulo} loading="lazy" class=${ab ? "aberta" : ""} />
            </button>
            ${ab && html`<div class="insight-txt flex gap-3"><${Icone} nome="lightbulb" className="mt-0.5 h-4 w-4 flex-none text-amber" /><p>${g.insight}</p></div>`}
          </article>`;
        })}
      </div>
    </div>`)}
  </section>`;
}

function Painel() {
  const base = D.dias[Math.min(F.dia, D.dias.length - 1)];
  const filtrada = filtrar(base.lista);
  const dia = { ...base, filtrada, top: filtrada.slice(0, 10), altoRisco: filtrada.filter((e) => e.prob > 50).length };
  const rf = resumoFiltros();
  return html`<div class="bg-background font-sans">
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <section aria-label="Máquinas com maior risco" class="mb-6 border-l-4 border-amber bg-amber/10 p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="flex items-center gap-2 font-extrabold"><${Icone} nome="triangle-alert" className="h-5 w-5 text-violet" /> Atenção: ${dia.top.length >= 5 ? "cinco máquinas" : "máquinas"} com maior risco</h2>
          <span class="text-xs text-muted-foreground">Até 06:00 de ${dia.fimLongo}${rf ? ` · ${rf}` : ""}</span>
        </div>
        ${dia.top.length === 0
          ? html`<p class="mt-4 text-sm text-muted-foreground">Nenhuma peça atende aos filtros da barra lateral neste dia.</p>`
          : html`<div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          ${dia.top.slice(0, 5).map((e) => html`<button key=${e.machine + e.comp} class=${BTN_ALERTA}
              onClick=${() => { if (window.ABA !== "model") return; requestAnimationFrame(() => irPara("prioridades")); }}>
            <span><strong class="block">${e.machine}</strong><span class="text-xs text-muted-foreground">${e.comp} · ${e.model}</span></span>
            <span class="text-xl font-extrabold text-violet">${e.prob}%</span></button>`)}
        </div>`}
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
