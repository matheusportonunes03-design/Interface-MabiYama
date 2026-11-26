"""Abas nativas do Streamlit: "Máquinas" (ficha de cada máquina) e "Dados tratados" (explorador das bases completas).

As bases tratadas ficam em dados/tratados/*.parquet (geradas por `python preparar_dados.py --bases <pasta> --tabelas`).
"""
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent
TRAT = RAIZ / "dados" / "tratados"
PECAS = ["peca_A", "peca_B", "peca_C", "peca_D"]
NOME_PECA = {p: "Peça " + p[-1] for p in PECAS}
SENSOR_DA_PECA = {"peca_A": "sensor_c", "peca_B": "sensor_d", "peca_C": "sensor_b", "peca_D": "sensor_a"}
CORES = {"peca_A": "#1f4e9a", "peca_B": "#e8862a", "peca_C": "#2f9e6b", "peca_D": "#8e5bb5"}

TABELAS = {
    "telemetria_corrigido": dict(titulo="Telemetria", data="data_hora", desc="Leituras horárias dos sensores a–d, vibração, temperatura e umidade de cada máquina."),
    "base_integrada_maquina_dia": dict(titulo="Base integrada (máquina × dia)", data="dia_ref",
                                       desc="Uma linha por máquina por dia, com tudo o que se sabe até as 05:00: resumo dos sensores, erros, operação, manutenção e cadastro."),
    "operacao_corrigido": dict(titulo="Operação", data="data", desc="Produção por turno: peças produzidas, meta, defeitos, energia, utilização e hora extra."),
    "manutencao_corrigido": dict(titulo="Manutenção", data="data_hora", desc="Trocas preventivas e corretivas: técnico, duração, fornecedor, lote e custo."),
    "erros_corrigido": dict(titulo="Erros", data="data_hora", desc="Códigos de erro E1–E5 com severidade, firmware e tempo de reconhecimento."),
    "falhas_corrigido": dict(titulo="Falhas", data="data_hora", desc="Falhas de peça registradas às 06:00 (alvo do modelo)."),
    "maquinas_corrigido": dict(titulo="Máquinas", data=None, desc="Cadastro das 92 máquinas: modelo, idade, fabricante, planta, linha e potência."),
}
DESC_COL = {
    "id_maquina": "identificador da máquina (Mnnn)", "data_hora": "data e hora do registro", "dia_ref": "dia D (informação até D 05:00)",
    "sensor_a": "sensor A (ligado à peça D)", "sensor_b": "sensor B em rpm (ligado à peça C)", "sensor_c": "sensor C (ligado à peça A)",
    "sensor_d": "sensor D (ligado à peça B)", "sensor_b_aux": "sensor B em rad/s (= sensor_b × 2π/60)", "vibracao_mm_s": "vibração (mm/s)",
    "temp_ambiente_c": "temperatura ambiente (°C)", "umidade_relativa": "umidade relativa (%)", "qualidade_leitura": "qualidade informada da leitura",
    "peca": "peça (A, B, C ou D)", "tipo": "preventiva ou corretiva", "tecnico": "técnico responsável", "duracao_min": "duração da troca (min)",
    "fornecedor_peca": "fornecedor da peça instalada", "lote_peca": "lote da peça instalada", "custo_troca_reais": "custo da troca (R$)",
    "codigo_erro": "código do erro (E1–E5)", "severidade": "severidade do erro", "versao_firmware": "versão do firmware",
    "tempo_reconhecimento_min": "minutos até o erro ser reconhecido", "modelo": "modelo da máquina", "idade": "idade (anos)",
    "fabricante": "fabricante", "planta": "planta", "linha_producao": "linha de produção", "potencia_kw": "potência (kW)",
    "turno": "turno (manhã, tarde, noite)", "pecas_produzidas": "peças produzidas no turno", "meta_producao": "meta do turno",
    "pecas_defeituosas": "peças com defeito", "consumo_energia_kwh": "energia consumida (kWh)", "utilizacao_pct": "utilização (%)",
    "hora_extra": "houve hora extra", "ind_quebra": "indicador de quebra informado pela operação",
}


# ------------------------------------------------------------------ carga (uma cópia por servidor, sem copiar a cada rerun)
@st.cache_resource(show_spinner="Carregando a base…")
def tabela(nome: str) -> pd.DataFrame:
    d = pd.read_parquet(TRAT / f"{nome}.parquet")
    c = TABELAS[nome]["data"]
    if c:
        d[c] = pd.to_datetime(d[c])
    return d


def disponivel() -> bool:
    return TRAT.exists() and any(TRAT.glob("*.parquet"))


@st.cache_data(show_spinner=False)
def relatorio_secao(nome: str) -> str:
    """Trecho do relatório de qualidade do ETL referente à tabela (seção '## <tabela>')."""
    f = TRAT / "relatorio_qualidade.md"
    if not f.exists():
        return ""
    chave = nome.replace("_corrigido", "").replace("base_integrada_maquina_dia", "integracao")
    partes = f.read_text(encoding="utf-8").split("\n## ")
    for p in partes[1:]:
        if p.split("\n", 1)[0].strip().lower().startswith(chave.split("_")[0]):
            return "### " + p
    return ""


@st.cache_data(show_spinner=False)
def dicionario(nome: str) -> pd.DataFrame:
    d = tabela(nome)
    linhas = []
    for c in d.columns:
        s = d[c]
        if pd.api.types.is_numeric_dtype(s):
            faixa = f"{s.min():,.4g} a {s.max():,.4g}" if s.notna().any() else "–"
            tipo = "número"
        elif pd.api.types.is_datetime64_any_dtype(s):
            faixa = f"{s.min():%d/%m/%Y} a {s.max():%d/%m/%Y}" if s.notna().any() else "–"
            tipo = "data"
        else:
            v = s.dropna().astype(str).value_counts()
            faixa = ", ".join(v.index[:4]) + ("…" if len(v) > 4 else "")
            tipo = f"texto ({len(v)} valores)"
        linhas.append({"coluna": c, "descrição": DESC_COL.get(c, "flag do tratamento (1 = valor alterado)" if c.startswith("flag_") else ""),
                       "tipo": tipo, "% vazios": round(100 * s.isna().mean(), 1), "valores / faixa": faixa})
    return pd.DataFrame(linhas)


def _css():
    st.markdown("""<style>
      .st-key-pg { max-width: 80rem; margin: 0 auto; padding: 1.75rem 1.5rem 3rem; width: 100%; gap: 1rem !important; }
      .st-key-pg [data-testid="stVerticalBlock"] { gap: .75rem !important; }
      .st-key-pg [data-testid="stHorizontalBlock"] { gap: 1rem !important; }
      .st-key-pg [data-testid="stElementContainer"]:has(style) { display: none; }
      .pg-tit { font-size: 1.5rem; font-weight: 800; color: var(--foreground); margin: 0; }
      .pg-sub { font-size: .875rem; color: var(--muted-foreground); margin: .25rem 0 0; }
      .cartoes { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: .75rem; }
      .cartao { background: var(--card); border: 1px solid var(--border); border-radius: .75rem; padding: .875rem 1rem; }
      .cartao .r { font-size: .75rem; color: var(--muted-foreground); text-transform: uppercase; letter-spacing: .06em; font-weight: 700; }
      .cartao .v { font-size: 1.25rem; font-weight: 800; color: var(--foreground); margin-top: .125rem; }
      .cartao .v.peq { font-size: 1rem; }
      .st-key-pg [data-testid="stTabs"] button p { font-weight: 700; font-size: .875rem; }
      .st-key-pg [data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: .5rem; }
      .st-key-pg .stDownloadButton button, .st-key-pg .stButton button { background: var(--brand) !important; color: var(--primary-foreground) !important; border: 0 !important; }
      .st-key-pg .stDownloadButton button:hover, .st-key-pg .stButton button:hover { background: var(--brand-deep) !important; }
      .st-key-pg h3 { font-size: 1.1rem !important; font-weight: 800; padding-top: 1rem !important; margin: 0 !important; }
    </style>""", unsafe_allow_html=True)


def _cartoes(itens):
    html = "".join(f'<div class="cartao"><div class="r">{r}</div><div class="v{" peq" if len(str(v)) > 12 else ""}">{v}</div></div>' for r, v in itens)
    st.markdown(f'<div class="cartoes">{html}</div>', unsafe_allow_html=True)


def _sem_dados():
    st.info("As bases tratadas ainda não estão no app. Rode `python preparar_dados.py --bases <pasta das bases tratadas> --tabelas` "
            "para gerar `dados/tratados/` e envie para o repositório.")


# ------------------------------------------------------------------ aba "Dados tratados"
def pagina_dados():
    with st.container(key="pg"):
        _css()
        st.markdown('<p class="pg-tit">Bases tratadas</p><p class="pg-sub">As tabelas completas que saíram do tratamento da Etapa 2 e alimentam '
                    'o modelo. Filtre, consulte o dicionário de colunas e o que foi corrigido, e baixe o recorte.</p>', unsafe_allow_html=True)
        if not disponivel():
            _sem_dados()
            return
        nomes = [n for n in TABELAS if (TRAT / f"{n}.parquet").exists()]
        nome = st.segmented_control("Tabela", nomes, format_func=lambda n: TABELAS[n]["titulo"], default=nomes[0], key="dt_tab",
                                    label_visibility="collapsed") or nomes[0]
        d = tabela(nome)
        cfg = TABELAS[nome]
        st.caption(cfg["desc"])

        c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
        maqs = sorted(d["id_maquina"].dropna().unique()) if "id_maquina" in d else []
        sel_maq = c1.multiselect("Máquinas", maqs, key=f"dt_maq_{nome}", placeholder="Todas") if maqs else []
        periodo = None
        if cfg["data"]:
            ini, fim = d[cfg["data"]].min().date(), d[cfg["data"]].max().date()
            periodo = c2.date_input("Período", (ini, fim), min_value=ini, max_value=fim, format="DD/MM/YYYY", key=f"dt_per_{nome}")
        cols = c3.multiselect("Colunas", list(d.columns), key=f"dt_cols_{nome}", placeholder="Todas as colunas")

        m = pd.Series(True, index=d.index)
        if sel_maq:
            m &= d["id_maquina"].isin(sel_maq)
        if periodo and len(periodo) == 2:
            c = d[cfg["data"]]
            m &= (c >= pd.Timestamp(periodo[0])) & (c < pd.Timestamp(periodo[1]) + pd.Timedelta(days=1))
        f = d.loc[m, cols or list(d.columns)]

        _cartoes([("Linhas no recorte", f"{len(f):,}".replace(",", ".")), ("Linhas na base", f"{len(d):,}".replace(",", ".")),
                  ("Colunas", len(f.columns)), ("Máquinas", f["id_maquina"].nunique() if "id_maquina" in f else "–"),
                  ("Período", f"{d[cfg['data']].min():%d/%m/%y} – {d[cfg['data']].max():%d/%m/%y}" if cfg["data"] else "–")])

        t1, t2, t3 = st.tabs(["Tabela", "Dicionário de colunas", "O que foi tratado"])
        with t1:
            LIM = 100_000
            st.dataframe(f.head(LIM), height=520, hide_index=True, width="stretch")
            if len(f) > LIM:
                st.caption(f"Mostrando as primeiras {LIM:,} linhas. Use os filtros para ver um recorte menor.".replace(",", "."))
            LIM_CSV = 300_000
            if len(f) > LIM_CSV:
                st.caption(f"Para baixar, filtre até {LIM_CSV:,} linhas (por máquina ou período).".replace(",", "."))
            else:
                chave = (nome, tuple(sel_maq), tuple(periodo or ()), tuple(cols))
                if st.session_state.get("dt_csv_chave") != chave:
                    if st.button(f"Preparar CSV do recorte ({len(f):,} linhas)".replace(",", "."), key="dt_prep"):
                        st.session_state.dt_csv = f.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
                        st.session_state.dt_csv_chave = chave
                        st.rerun()
                else:
                    st.download_button("Baixar CSV do recorte", st.session_state.dt_csv, file_name=f"{nome}_recorte.csv", mime="text/csv")
        with t2:
            st.dataframe(dicionario(nome), hide_index=True, width="stretch", height=min(38 * (len(d.columns) + 1), 640))
        with t3:
            txt = relatorio_secao(nome)
            st.markdown(txt if txt else "_Sem seção específica no relatório de qualidade para esta tabela._")


# ------------------------------------------------------------------ aba "Máquinas"
@st.cache_data(show_spinner=False)
def _risco_longo(previsao: pd.DataFrame) -> pd.DataFrame:
    p = previsao.copy()
    p["id_maquina"] = p["id"].str[:4]
    p["dia"] = pd.to_datetime(p["id"].str[5:]) + pd.Timedelta(days=1)          # linha D -> falha às 06:00 de D+1
    return p.melt(id_vars=["id_maquina", "dia"], value_vars=PECAS, var_name="peca", value_name="score")


def pagina_maquina(previsao: pd.DataFrame, prob_dia: dict):
    """previsao: tabela id/peca_A..D usada no painel; prob_dia: {(maquina, peca, 'dd/mm/aaaa'): prob%} das listas do painel."""
    with st.container(key="pg"):
        _css()
        st.markdown('<p class="pg-tit">Ficha da máquina</p><p class="pg-sub">Cadastro, risco previsto no período de teste, histórico de falhas e '
                    'manutenções e o comportamento dos sensores.</p>', unsafe_allow_html=True)
        if not disponivel():
            _sem_dados()
            return
        maq, fal, man, err, tel = (tabela(n) for n in ("maquinas_corrigido", "falhas_corrigido", "manutencao_corrigido", "erros_corrigido",
                                                       "telemetria_corrigido"))
        ids = sorted(maq["id_maquina"])
        risco = _risco_longo(previsao)
        topo = risco.groupby("id_maquina")["score"].max().sort_values(ascending=False)
        padrao = st.session_state.get("ficha_maq") or (topo.index[0] if len(topo) else ids[0])
        c1, c2 = st.columns([1, 3])
        m = c1.selectbox("Máquina", ids, index=ids.index(padrao) if padrao in ids else 0, key="ficha_maq")
        info = maq.set_index("id_maquina").loc[m]
        c2.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
        _cartoes([("Modelo", (lambda t: t[:1].upper() + t[1:])(str(info.get("modelo", "–")).replace("_", " "))), ("Idade", f"{info.get('idade', np.nan):.0f} anos" if pd.notna(info.get("idade")) else "–"),
                  ("Fabricante", info.get("fabricante", "–")), ("Planta", info.get("planta", "–")), ("Linha", info.get("linha_producao", "–")),
                  ("Potência", f"{info.get('potencia_kw'):.0f} kW" if pd.notna(info.get("potencia_kw")) else "–")])

        # --- risco previsto no teste
        st.markdown("### Risco previsto no período de teste")
        r = risco[risco["id_maquina"] == m].copy()
        r["Peça"] = r["peca"].map(NOME_PECA)
        r["prob"] = [prob_dia.get((m, p, f"{d:%d/%m/%Y}"), np.nan) for p, d in zip(r["peca"], r["dia"])]
        r = r[r["prob"].notna()]
        if r.empty:
            st.caption("Nenhuma data de grade desta máquina no período de teste.")
        else:
            r["Probabilidade"] = r["prob"].round(0)
            enc = dict(x=alt.X("dia:T", title="falha prevista para (06:00 de)", axis=alt.Axis(format="%d/%m", grid=True)),
                       y=alt.Y("Peça:N", title=None, sort=list(NOME_PECA.values())),
                       tooltip=[alt.Tooltip("dia:T", format="%d/%m/%Y", title="dia"), "Peça", alt.Tooltip("Probabilidade:Q", format=".0f", title="prob. (%)")])
            pontos = alt.Chart(r).mark_circle(opacity=.85, stroke="white", strokeWidth=1).encode(
                size=alt.Size("prob:Q", scale=alt.Scale(domain=[0, 100], range=[30, 1100]), legend=None),
                color=alt.Color("Peça:N", scale=alt.Scale(domain=list(NOME_PECA.values()), range=list(CORES.values())), legend=None), **enc)
            rotulos = alt.Chart(r[r["prob"] >= 20]).mark_text(dy=-22, fontSize=11, fontWeight="bold", color="#334").encode(
                text=alt.Text("Probabilidade:Q", format=".0f"), **{k: v for k, v in enc.items() if k != "tooltip"})
            st.altair_chart((pontos + rotulos).properties(height=230, padding={"left": 14, "top": 6, "right": 6, "bottom": 4}), width="stretch")
            st.caption("Cada círculo é um dia de grade da peça (múltiplo de 15 dias desde a última preventiva); o tamanho e o número mostram a probabilidade de falha (%). Nos outros dias o risco é praticamente zero.")

        # --- histórico
        st.markdown("### Histórico")
        fm, mm, em = fal[fal["id_maquina"] == m], man[man["id_maquina"] == m], err[err["id_maquina"] == m]
        h1, h2, h3 = st.columns(3)
        with h1:
            st.markdown("**Falhas por peça**")
            t = fm.groupby("peca").size().reindex(PECAS, fill_value=0).rename(index=NOME_PECA).rename("falhas").reset_index()
            st.dataframe(t, hide_index=True, width="stretch")
        with h2:
            st.markdown("**Última preventiva por peça**")
            pv = mm[mm["tipo"] == "preventiva"].groupby("peca")["data_hora"].max().reindex(PECAS)
            t = pd.DataFrame({"peça": [NOME_PECA[p] for p in PECAS], "última": [f"{d:%d/%m/%Y}" if pd.notna(d) else "–" for d in pv],
                              "próxima data de grade": [f"{(d + pd.Timedelta(days=15)):%d/%m/%Y}" if pd.notna(d) else "–" for d in pv]})
            st.dataframe(t, hide_index=True, width="stretch")
        with h3:
            st.markdown("**Erros por código**")
            t = em.groupby("codigo_erro").size().rename("ocorrências").reset_index() if len(em) else pd.DataFrame({"codigo_erro": [], "ocorrências": []})
            st.dataframe(t, hide_index=True, width="stretch")

        # --- sensores
        st.markdown("### Sensores")
        tm = tel[tel["id_maquina"] == m]
        ini, fim = tm["data_hora"].min().date(), tm["data_hora"].max().date()
        s1, s2, s3 = st.columns([1, 1.4, 1])
        peca = s1.selectbox("Sensor da peça", PECAS, format_func=lambda p: f"{NOME_PECA[p]} ({SENSOR_DA_PECA[p]})", key="ficha_peca")
        ult = fm.loc[fm["peca"] == peca, "data_hora"].max()
        if pd.notna(ult):
            pad = (max(ini, (ult - pd.Timedelta(days=21)).date()), min(fim, (ult + pd.Timedelta(days=7)).date()))
        else:
            pad = (max(ini, fim - pd.Timedelta(days=45)), fim)
        per = s2.date_input("Período", pad, min_value=ini, max_value=fim, format="DD/MM/YYYY", key=f"ficha_per_{m}_{peca}",
                            help="Por padrão, as 4 semanas em volta da última falha desta peça.")
        agr = s3.selectbox("Resolução", ["horária", "média diária"], key="ficha_res")
        if len(per) == 2:
            a, b = pd.Timestamp(per[0]), pd.Timestamp(per[1]) + pd.Timedelta(days=1)
            sen = SENSOR_DA_PECA[peca]
            x = tm[(tm["data_hora"] >= a) & (tm["data_hora"] < b)][["data_hora", sen]].dropna()
            if agr == "média diária":
                x = x.set_index("data_hora").resample("D").mean().reset_index()
            base = alt.Chart(x).mark_line(color=CORES[peca], strokeWidth=1.2).encode(
                x=alt.X("data_hora:T", title=None, axis=alt.Axis(format="%d/%m")), y=alt.Y(f"{sen}:Q", title=sen, scale=alt.Scale(zero=False)),
                tooltip=[alt.Tooltip("data_hora:T", format="%d/%m/%Y %H:%M", title="hora"), alt.Tooltip(f"{sen}:Q", format=".2f")])
            ev = pd.concat([fm[fm["peca"] == peca].assign(evento="falha")[["data_hora", "evento"]],
                            mm[mm["peca"] == peca].assign(evento=lambda z: z["tipo"])[["data_hora", "evento"]]])
            ev = ev[(ev["data_hora"] >= a) & (ev["data_hora"] < b)]
            ev = ev.assign(ordem=ev["evento"].map({"preventiva": 0, "corretiva": 1, "falha": 2})).sort_values("ordem")   # falha desenhada por cima
            regras = alt.Chart(ev).mark_rule(strokeDash=[4, 3], strokeWidth=1.5).encode(
                x="data_hora:T", color=alt.Color("evento:N", title="evento", scale=alt.Scale(domain=["falha", "preventiva", "corretiva"],
                                                                                          range=["#d62728", "#9aa3ad", "#e8862a"])),
                tooltip=[alt.Tooltip("data_hora:T", format="%d/%m/%Y %H:%M", title="data"), "evento"])
            st.altair_chart((base + regras).properties(height=280), width="stretch")
            st.caption("Antes de uma falha o sensor da peça costuma subir em patamar por 40–65 h; a troca derruba o sinal. "
                       "No período de teste (a partir de 30/09/2023) as falhas não são conhecidas.")
