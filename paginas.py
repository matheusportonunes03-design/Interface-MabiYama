"""Abas nativas do Streamlit: "Máquinas" (ficha de cada máquina) e "Dados tratados" (explorador das bases completas).

As bases tratadas ficam em dados/tratados/*.parquet (geradas por `python preparar_dados.py --bases <pasta> --tabelas`).
"""
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import atualizar_bases
import tema

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
def pasta() -> Path:
    """Pasta das bases tratadas desta sessão: a das bases enviadas pelo usuário, se houver; senão a do repositório."""
    p = st.session_state.get("trat_dir")
    return Path(p) if p and Path(p).exists() else TRAT


@st.cache_resource(max_entries=16, show_spinner="Carregando a base…")
def _tabela(p: str, nome: str) -> pd.DataFrame:
    d = pd.read_parquet(Path(p) / f"{nome}.parquet")
    c = TABELAS[nome]["data"]
    if c:
        d[c] = pd.to_datetime(d[c])
    return d


def tabela(nome: str) -> pd.DataFrame:
    return _tabela(str(pasta()), nome)


def disponivel() -> bool:
    return pasta().exists() and any(pasta().glob("*.parquet"))


@st.cache_data(show_spinner=False)
def relatorio_secao(nome: str, p: str) -> str:
    """Trecho do relatório de qualidade do ETL referente à tabela (seção '## <tabela>')."""
    f = Path(p) / "relatorio_qualidade.md"
    if not f.exists():
        return ""
    chave = nome.replace("_corrigido", "").replace("base_integrada_maquina_dia", "integracao")
    partes = f.read_text(encoding="utf-8").split("\n## ")
    for p in partes[1:]:
        if p.split("\n", 1)[0].strip().lower().startswith(chave.split("_")[0]):
            return "### " + p
    return ""


@st.cache_data(show_spinner=False)
def dicionario(nome: str, p: str) -> pd.DataFrame:
    d = _tabela(p, nome)
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
      .st-key-pg .stDownloadButton button:hover, .st-key-pg .stButton button:hover { background: var(--brand-solid, var(--brand-deep)) !important; }
      .st-key-dt_origem { background: var(--card); border: 1px solid var(--border); border-radius: .75rem; padding: .5rem .75rem; gap: .5rem !important; flex-wrap: wrap; }
      .st-key-dt_origem > div:first-child { flex: 1 1 18rem; }
      .st-key-dt_origem .origem { font-size: .875rem; color: var(--muted-foreground); display: flex; align-items: center; gap: .5rem; }
      .st-key-dt_origem .origem b { color: var(--foreground); }
      .st-key-dt_origem .pt { width: .55rem; height: .55rem; border-radius: 50%; background: var(--muted-foreground); flex: none; }
      .st-key-dt_origem .pt.on { background: #f59e0b; box-shadow: 0 0 0 3px rgba(245, 158, 11, .2); }
      .st-key-pg h3 { font-size: 1.1rem !important; font-weight: 800; padding-top: 1rem !important; margin: 0 !important; }
    </style>""", unsafe_allow_html=True)


def _cartoes(itens):
    html = "".join(f'<div class="cartao"><div class="r">{r}</div><div class="v{" peq" if len(str(v)) > 12 else ""}">{v}</div></div>' for r, v in itens)
    st.markdown(f'<div class="cartoes">{html}</div>', unsafe_allow_html=True)


def _sem_dados():
    st.info("As bases tratadas ainda não estão no app. Rode `python preparar_dados.py --bases <pasta das bases tratadas> --tabelas` "
            "para gerar `dados/tratados/` e envie para o repositório.")


# ------------------------------------------------------------------ aba "Dados tratados"
@st.cache_resource(max_entries=6, show_spinner=False)
def _recorte(p: str, nome: str, maqs: tuple, periodo: tuple, cols: tuple) -> pd.DataFrame:
    d = _tabela(p, nome)
    cfg = TABELAS[nome]
    m = pd.Series(True, index=d.index)
    if maqs:
        m &= d["id_maquina"].isin(maqs)
    if periodo and len(periodo) == 2 and cfg["data"]:
        c = d[cfg["data"]]
        m &= (c >= pd.Timestamp(periodo[0])) & (c < pd.Timestamp(periodo[1]) + pd.Timedelta(days=1))
    return d.loc[m, list(cols) or list(d.columns)]


@st.cache_resource(max_entries=12, show_spinner="Ordenando…")
def _ordenado(p, nome, maqs, periodo, cols, ordem, desc) -> pd.DataFrame:
    f = _recorte(p, nome, maqs, periodo, cols)
    if ordem:
        f = f.sort_values(ordem, ascending=not desc, kind="stable", na_position="last")
    f = f.reset_index(drop=True)
    f.index = f.index + 1                       # número da linha, a partir de 1
    f.index.name = "linha"
    return f


@st.cache_resource(max_entries=12, show_spinner="Buscando…")
def _buscar(p, nome, maqs, periodo, cols, ordem, desc, q: str, col: str | None) -> np.ndarray:
    """Posições (0..n-1) das linhas em que o valor aparece. Números: igualdade na precisão digitada; datas: mesmo dia; texto: contém."""
    f = _ordenado(p, nome, maqs, periodo, cols, ordem, desc)
    q = q.strip()
    num = None
    try:
        num = float(q.replace(".", "").replace(",", ".")) if "," in q else float(q)
    except ValueError:
        pass
    dec = len(q.replace(",", ".").split(".")[1]) if num is not None and ("," in q or "." in q) else 0
    data = None
    if any(ch in q for ch in "/-") and any(ch.isdigit() for ch in q):
        try:
            data = pd.to_datetime(q, dayfirst=True)
        except (ValueError, OverflowError):
            pass
    mask = np.zeros(len(f), bool)
    for c in ([col] if col else list(f.columns)):
        x = f[c]
        if pd.api.types.is_bool_dtype(x):
            mask |= x.astype(str).str.lower().eq(q.lower()).to_numpy()
        elif pd.api.types.is_numeric_dtype(x):
            if num is not None:
                mask |= (x.round(dec) == round(num, dec)).to_numpy()
        elif pd.api.types.is_datetime64_any_dtype(x):
            if data is not None:
                alvo = x if (data.hour or data.minute) else x.dt.normalize()
                mask |= (alvo == data).to_numpy()
        elif isinstance(x.dtype, pd.CategoricalDtype):
            cats = [k for k in x.cat.categories if q.lower() in str(k).lower()]
            mask |= x.isin(cats).to_numpy()
        else:
            mask |= x.astype(str).str.contains(q, case=False, regex=False, na=False).to_numpy()
    return np.flatnonzero(mask)


def _fmt(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT:
        return "vazio"
    if isinstance(v, pd.Timestamp):
        return f"{v:%d/%m/%Y %H:%M}".replace(" 00:00", "")
    if isinstance(v, (float, np.floating)):
        return f"{v:,.4f}".rstrip("0").rstrip(",.").replace(",", "X").replace(".", ",").replace("X", ".")
    return str(v)


def _ir(linha: int):
    st.session_state.dt_linha = int(linha)


# ------------------------------------------------------------------ envio das bases brutas (roda o ETL e troca as tabelas da sessão)
FORMATO_BRUTAS = """Mande os **6 arquivos CSV brutos**, do jeito que o cliente entrega (separados por vírgula, com cabeçalho).
O nome do arquivo não importa: cada um é reconhecido pelas colunas. Colunas a mais são ignoradas.

| Base | Colunas obrigatórias |
|---|---|
""" + "\n".join(f"| {atualizar_bases.TITULOS[b]} | " + ", ".join(f"`{c}`" for c in cols) + " |" for b, cols in atualizar_bases.COLUNAS.items()) + """

Datas podem vir em ISO (`2023-05-04 06:00:00`), dia/mês/ano ou mês/dia/ano (como o Excel salva): a ordem é detectada pelos dados.
Números com vírgula decimal, nomes com acento ou caixa diferente, sentinelas -999 e linhas duplicadas são tratados pelo ETL,
como descrito no relatório de qualidade. A manutenção também pode vir com uma coluna por peça (`peca_A` … `peca_D` = 0/1)."""


def _ao_terminar(destino, resumo):
    st.session_state.trat_dir = str(destino)
    st.session_state.trat_resumo = resumo
    st.session_state.trat_msg = True
    st.session_state.brutas_v = st.session_state.get("brutas_v", 0) + 1     # fecha o popover e limpa o envio
    for k in [k for k in st.session_state if k.startswith(("dt_", "fm_"))]:
        del st.session_state[k]


def _voltar_bases():
    for k in ("trat_dir", "trat_resumo", "trat_msg"):
        st.session_state.pop(k, None)
    st.session_state.brutas_v = st.session_state.get("brutas_v", 0) + 1
    for k in [k for k in st.session_state if k.startswith(("dt_", "fm_"))]:
        del st.session_state[k]


def _popover_brutas():
    st.markdown("**Atualizar com bases brutas.** O painel roda o mesmo tratamento da Etapa 2 (`ETL/integracao.py`) e troca as "
                "tabelas desta aba e da ficha das máquinas pelas novas. Vale só para a sua sessão: o repositório não muda.")
    with st.expander("Formato dos arquivos"):
        st.markdown(FORMATO_BRUTAS)
    arqs = st.file_uploader("Bases brutas (6 arquivos .csv)", type="csv", accept_multiple_files=True,
                            key=f"brutas_arqs_{st.session_state.get('brutas_v', 0)}")
    if not arqs:
        st.caption("Leva cerca de 1 a 2 minutos depois do envio (a telemetria tem ~1 milhão de linhas).")
        return
    bases, problemas = atualizar_bases.identificar([(a.name, a.getvalue()) for a in arqs])
    lista = " · ".join(("✓ " if b in bases else "✗ ") + atualizar_bases.TITULOS[b] for b in atualizar_bases.COLUNAS)
    st.markdown(f'<div class="lb-info">{lista}</div>', unsafe_allow_html=True)
    for p in problemas:
        st.error(p)
    if problemas or len(bases) < len(atualizar_bases.COLUNAS):
        return
    if st.button("Tratar e atualizar as tabelas", key="brutas_ir", type="primary", width="stretch"):
        barra = st.progress(0.0, text="Começando o tratamento…")

        def aviso(etapa, i, n):
            nome = "Integração (máquina × dia)" if etapa == "integracao" else atualizar_bases.TITULOS[etapa]
            barra.progress(i / (n + 1), text=f"Tratando: {nome} ({i + 1} de {n})")
        try:
            destino, resumo = atualizar_bases.rodar(bases, aviso)
        except Exception as e:
            barra.empty()
            msg = str(e)
            st.error(msg.split("\n\n")[0])
            if "\n\n" in msg:
                with st.expander("Últimas linhas do tratamento"):
                    st.code(msg.split("\n\n", 1)[1], language="text")
            return
        barra.progress(1.0, text="Pronto")
        _ao_terminar(destino, resumo)
        st.rerun()


def _barra_origem():
    r = st.session_state.get("trat_resumo") if pasta() != TRAT else None
    with st.container(key="dt_origem", horizontal=True, vertical_alignment="center"):
        if r:
            st.markdown(f'<div class="origem"><span class="pt on"></span><span><b>Bases enviadas por você</b> em {r["quando"]}, '
                        'tratadas agora pelo ETL da equipe.</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="origem"><span class="pt"></span><span><b>Bases do projeto</b>, tratadas pela equipe na Etapa 2.</span></div>',
                        unsafe_allow_html=True)
        with st.popover("Atualizar com bases brutas", icon=":material/upload_file:", key=f"brutas_pop_{st.session_state.get('brutas_v', 0)}"):
            _popover_brutas()
        if r:
            rel = pasta() / "relatorio_qualidade.md"
            if rel.exists():
                st.download_button("Relatório de qualidade", rel.read_bytes(), file_name="relatorio_qualidade.md", mime="text/markdown",
                                   key="dt_rel", icon=":material/download:")
            st.button("Voltar às bases do projeto", key="dt_voltar", on_click=_voltar_bases, icon=":material/undo:")
    if r and st.session_state.pop("trat_msg", False):
        ref = {n: pq_linhas(TRAT / f"{n}.parquet") for n in r["linhas"]}
        partes = [f"{TABELAS[n]['titulo']}: {v:,}".replace(",", ".") + (f" ({v - ref[n]:+,})".replace(",", ".") if ref.get(n) is not None and v != ref[n] else "")
                  for n, v in r["linhas"].items() if n in TABELAS]
        st.success("Bases tratadas e atualizadas. Linhas por tabela (entre parênteses, a diferença para as bases do projeto): "
                   + " · ".join(partes) + (". Linhas rejeitadas (sem data ou máquina válida) ficaram de fora: "
                                           + ", ".join(r["rejeitados"]) if r["rejeitados"] else "."))


def pq_linhas(caminho: Path):
    try:
        import pyarrow.parquet as pq
        return pq.ParquetFile(caminho).metadata.num_rows
    except Exception:
        return None


def pagina_dados():
    with st.container(key="pg"):
        _css()
        st.markdown('<p class="pg-tit">Bases tratadas</p><p class="pg-sub">As tabelas completas que saíram do tratamento da Etapa 2 e alimentam '
                    'o modelo. Filtre aqui; navegue até uma linha, coluna ou célula pela barra lateral.</p>', unsafe_allow_html=True)
        _barra_origem()
        if not disponivel():
            _sem_dados()
            return
        nomes = [n for n in TABELAS if (pasta() / f"{n}.parquet").exists()]
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
        chave = (str(pasta()), nome, tuple(sel_maq), tuple(periodo or ()) if periodo and len(periodo) == 2 else (), tuple(cols))

        # ---------------- navegação na barra lateral
        if st.session_state.get("dt_rec") != chave:            # recorte mudou: volta ao topo
            st.session_state.dt_rec = chave
            st.session_state.dt_linha = 1
        with st.sidebar:
            tema.secao("Navegar na tabela")
            colunas = list(_recorte(*chave).columns)
            ordem = st.selectbox("Ordenar por", ["ordem original"] + colunas, key=f"dt_ord_{nome}")
            ordem = None if ordem == "ordem original" else ordem
            desc = st.toggle("Ordem decrescente", key=f"dt_desc_{nome}") if ordem else False
            fo = _ordenado(*chave, ordem, desc)
            n = len(fo)
            st.session_state.dt_linha = min(max(1, int(st.session_state.get("dt_linha", 1))), max(1, n))
            st.number_input(f"Ir para a linha (1 a {n:,})".replace(",", "."), min_value=1, max_value=max(1, n), step=1, key="dt_linha")
            col = st.selectbox("Ir para a coluna", ["—"] + colunas, key=f"dt_col_{nome}")
            col = None if col == "—" else col
            linha = st.session_state.dt_linha
            if col and n:
                st.markdown(f'<div class="lb-celula"><div class="r">Célula · linha {linha:,} · {col}</div><div class="v">{_fmt(fo.iloc[linha - 1][col])}</div></div>'
                            .replace(",", "."), unsafe_allow_html=True)
            q = st.text_input("Buscar valor", key=f"dt_q_{nome}", placeholder="ex.: M048, E3, 12,5 ou 03/05/2023")
            onde = st.selectbox("Buscar em", ["todas as colunas"] + colunas, key=f"dt_qcol_{nome}") if q else "todas as colunas"
            achados = np.array([], int)
            if q.strip():
                achados = _buscar(*chave, ordem, desc, q, None if onde == "todas as colunas" else onde)
                if len(achados):
                    w = np.flatnonzero(achados == linha - 1)
                    pos = int(w[0]) + 1 if len(w) else None
                    st.markdown(f'<div class="lb-info"><b>{len(achados):,} linhas</b> contêm “{q}”'.replace(",", ".")
                                + (f" · você está na {pos}ª" if pos else "") + "</div>", unsafe_allow_html=True)
                    b1, b2, b3 = st.columns(3)
                    ant = achados[achados < linha - 1]
                    prox = achados[achados > linha - 1]
                    b1.button("◀", key="dt_q_ant", width="stretch", disabled=not len(ant), help="ocorrência anterior",
                              on_click=_ir, args=(int(ant[-1]) + 1 if len(ant) else 1,))
                    b2.button("1ª", key="dt_q_pri", width="stretch", help="primeira ocorrência", on_click=_ir, args=(int(achados[0]) + 1,))
                    b3.button("▶", key="dt_q_prox", width="stretch", disabled=not len(prox), help="próxima ocorrência",
                              on_click=_ir, args=(int(prox[0]) + 1 if len(prox) else 1,))
                else:
                    st.markdown(f'<div class="lb-info">Nenhuma linha contém “{q}”.</div>', unsafe_allow_html=True)
            c_a, c_b = st.columns(2)
            c_a.button("Topo", key="dt_topo", width="stretch", on_click=_ir, args=(1,))
            c_b.button("Fim", key="dt_fim", width="stretch", on_click=_ir, args=(max(1, n),))

        _cartoes([("Linhas no recorte", f"{n:,}".replace(",", ".")), ("Linhas na base", f"{len(d):,}".replace(",", ".")),
                  ("Colunas", len(fo.columns)), ("Máquinas", fo["id_maquina"].nunique() if "id_maquina" in fo else "–"),
                  ("Período", f"{d[cfg['data']].min():%d/%m/%y} – {d[cfg['data']].max():%d/%m/%y}" if cfg["data"] else "–")])

        t1, t2, t3 = st.tabs(["Tabela", "Dicionário de colunas", "O que foi tratado"])
        with t1:
            LIM, JAN = 100_000, 400
            ordem_cols = None
            if col:
                fixas = [c for c in ("id_maquina", cfg["data"]) if c and c in fo.columns and c != col]
                ordem_cols = fixas + [col] + [c for c in fo.columns if c not in fixas and c != col]
            navegando = linha > 1 or col or len(achados)
            cfg_idx = {"_index": st.column_config.NumberColumn("linha", format="%d", width="small")}
            if not navegando:
                st.dataframe(fo.head(LIM), height=520, width="stretch", column_config=cfg_idx)
                if n > LIM:
                    st.caption(f"Mostrando as primeiras {LIM:,} linhas. Use “Ir para a linha” na barra lateral para chegar a qualquer ponto.".replace(",", "."))
            else:
                ini = max(0, linha - 1 - 4)
                win = fo.iloc[ini: ini + JAN]
                marcados = set((achados[(achados >= ini) & (achados < ini + JAN)] + 1).tolist()) if len(achados) else set()

                def estilo(df):
                    e = pd.DataFrame("", index=df.index, columns=df.columns)
                    for r in marcados:
                        e.loc[r] = "background-color: rgba(56, 189, 248, .18)"
                    if col:
                        e[col] = e[col].where(e[col] != "", "background-color: rgba(59, 130, 246, .08)")
                    e.loc[linha] = "background-color: rgba(245, 158, 11, .22); font-weight: 700"
                    if col:
                        e.loc[linha, col] = "background-color: rgba(245, 158, 11, .75); font-weight: 800; color: #111"
                    return e
                sty = win.style.apply(estilo, axis=None).format(precision=4, na_rep="–", thousands=".", decimal=",")
                st.dataframe(sty, height=520, width="stretch", column_order=ordem_cols, column_config=cfg_idx)
                st.caption(f"Linhas {ini + 1:,} a {ini + len(win):,} de {n:,}. Laranja: linha {linha:,}".replace(",", ".")
                           + (f", célula em “{col}”" if col else "") + (" · azul-claro: ocorrências da busca" if marcados else "") + ".")
                with st.expander(f"Ver a linha {linha:,} inteira (na vertical)".replace(",", ".")):
                    r = fo.iloc[linha - 1]
                    st.dataframe(pd.DataFrame({"coluna": r.index, "valor": [_fmt(v) for v in r.values]}), hide_index=True, width="stretch",
                                 height=min(36 * (len(r) + 1), 560))
            LIM_CSV = 300_000
            if n > LIM_CSV:
                st.caption(f"Para baixar, filtre até {LIM_CSV:,} linhas (por máquina ou período).".replace(",", "."))
            else:
                chave_csv = chave + (ordem, desc)
                if st.session_state.get("dt_csv_chave") != chave_csv:
                    if st.button(f"Preparar CSV do recorte ({n:,} linhas)".replace(",", "."), key="dt_prep"):
                        st.session_state.dt_csv = fo.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
                        st.session_state.dt_csv_chave = chave_csv
                        st.rerun()
                else:
                    st.download_button("Baixar CSV do recorte", st.session_state.dt_csv, file_name=f"{nome}_recorte.csv", mime="text/csv")
        with t2:
            st.dataframe(dicionario(nome, str(pasta())), hide_index=True, width="stretch", height=min(38 * (len(d.columns) + 1), 640))
        with t3:
            txt = relatorio_secao(nome, str(pasta()))
            st.markdown(txt if txt else "_Sem seção específica no relatório de qualidade para esta tabela._")


# ------------------------------------------------------------------ aba "Máquinas"
def _alt(chart):
    """Gráficos Altair legíveis nos dois temas."""
    if not tema.escuro():
        return chart, "streamlit"
    tx, gr = "#c9d2e6", "#3a4766"
    return (chart.configure(background="transparent").configure_view(stroke=None)
            .configure_axis(labelColor=tx, titleColor=tx, gridColor=gr, domainColor=gr, tickColor=gr)
            .configure_legend(labelColor=tx, titleColor=tx)), None


@st.cache_data(show_spinner=False)
def _risco_longo(previsao: pd.DataFrame) -> pd.DataFrame:
    p = previsao.copy()
    p["id_maquina"] = p["id"].str[:4]
    p["dia"] = pd.to_datetime(p["id"].str[5:]) + pd.Timedelta(days=1)          # linha D -> falha às 06:00 de D+1
    return p.melt(id_vars=["id_maquina", "dia"], value_vars=PECAS, var_name="peca", value_name="score")


def _set_maq(m):
    """Escolhe a máquina; se ela estiver fora dos filtros da barra lateral, os filtros são limpos para ela aparecer lá também."""
    if m not in st.session_state.get("_fm_ids", [m]):
        st.session_state.fm_linhas, st.session_state.fm_modelos = [], []
    st.session_state.ficha_maq = m


ORDENS = ["Nº da máquina", "Risco de quebra"]


def _ordem_pg():
    """Ordem escolhida na página vale também na barra lateral; clicar de novo na mesma não desmarca."""
    v = st.session_state.get("fm_ordem_pg")
    if v is not None:
        st.session_state.fm_ordem = v


def _ordem_barra():
    if st.session_state.get("fm_ordem") is None:
        st.session_state.fm_ordem = st.session_state.get("fm_ordem_pg") or "Risco de quebra"


def _sync_pg():
    _set_maq(st.session_state.ficha_maq_pg)


def pagina_maquina(previsao: pd.DataFrame, prob_dia: dict, replay=None):
    """previsao: tabela id/peca_A..D usada no painel; prob_dia: {(maquina, peca, 'dd/mm/aaaa'): prob%} das listas do painel."""
    with st.container(key="pg"):
        _css()
        if not disponivel():
            st.markdown('<p class="pg-tit">Ficha da máquina</p>', unsafe_allow_html=True)
            _sem_dados()
            return
        maq, fal, man, err, tel = (tabela(n) for n in ("maquinas_corrigido", "falhas_corrigido", "manutencao_corrigido", "erros_corrigido",
                                                       "telemetria_corrigido"))
        risco_max = {}
        for (mm_, _, _), pr in prob_dia.items():
            risco_max[mm_] = max(risco_max.get(mm_, 0), pr)
        nfal = fal.groupby("id_maquina").size().to_dict()

        # ---------------- barra lateral: escolher e percorrer as máquinas
        with st.sidebar:
            tema.secao("Ficha da máquina")
            linhas = sorted(maq["linha_producao"].dropna().unique())
            modelos = sorted(maq["modelo"].dropna().unique())
            fl = st.multiselect("Linhas de produção", linhas, key="fm_linhas", placeholder="Todas")
            fmod = st.multiselect("Modelos", modelos, key="fm_modelos", placeholder="Todos",
                                  format_func=lambda t: t.replace("modelo_", "Modelo "))
            mk = pd.Series(True, index=maq.index)
            if fl:
                mk &= maq["linha_producao"].isin(fl)
            if fmod:
                mk &= maq["modelo"].isin(fmod)
            sel = maq[mk]
            ids = list(sel["id_maquina"])
            st.session_state.setdefault("fm_ordem", "Risco de quebra")
            if st.session_state.get("fm_ordem") not in ORDENS:
                st.session_state.fm_ordem = "Risco de quebra"
            ordem = st.segmented_control("Ordenar as máquinas por", ORDENS, key="fm_ordem", on_change=_ordem_barra) or "Risco de quebra"
            chave_ord = (lambda m: m) if ordem == "Nº da máquina" else (lambda m: (-risco_max.get(m, 0), m))
            ids.sort(key=chave_ord)
            if not ids:
                st.markdown('<div class="lb-info">Nenhuma máquina com esses filtros.</div>', unsafe_allow_html=True)
                ids = sorted(maq["id_maquina"])
            if st.session_state.get("ficha_maq") not in ids:
                st.session_state.ficha_maq = ids[0]
            rot = {m: f"{m} · {risco_max.get(m, 0):.0f}% · {nfal.get(m, 0)} falhas" for m in ids}
            m = st.selectbox("Máquina", ids, key="ficha_maq", format_func=rot.get)
            k = ids.index(m)
            b1, b2 = st.columns(2)
            b1.button("◀ Anterior", key="fm_ant", width="stretch", disabled=k == 0, on_click=_set_maq, args=(ids[max(0, k - 1)],))
            b2.button("Próxima ▶", key="fm_prox", width="stretch", disabled=k == len(ids) - 1, on_click=_set_maq, args=(ids[min(len(ids) - 1, k + 1)],))
            tema.secao("Sensores")
            peca = st.selectbox("Sensor da peça", PECAS, format_func=lambda p: f"{NOME_PECA[p]} ({SENSOR_DA_PECA[p]})", key="ficha_peca")
            agr = st.segmented_control("Resolução", ["horária", "média diária"], key="ficha_res", default="horária") or "horária"
            fm, mm, em = fal[fal["id_maquina"] == m], man[man["id_maquina"] == m], err[err["id_maquina"] == m]
            hist = pd.concat([fm.assign(registro="falha"), mm.assign(registro=mm["tipo"]), em.assign(registro="erro")], ignore_index=True)
            hist = hist.sort_values("data_hora")[["data_hora", "registro"] + [c for c in hist.columns if c not in ("data_hora", "registro", "id_maquina")]]
            st.download_button(f"Baixar histórico de {m}", hist.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                               file_name=f"historico_{m}.csv", mime="text/csv", width="stretch")

        info = maq.set_index("id_maquina").loc[m]
        if replay:
            st.markdown('<p class="pg-tit">Frota</p><p class="pg-sub">A planta inteira dia a dia: o risco que o modelo deu às 05:00 contra as falhas que '
                        'aconteceram de verdade na validação de 2023. Para olhar uma máquina, use a ficha logo abaixo.</p>', unsafe_allow_html=True)
            replay()
            st.markdown('<div style="height:.75rem"></div>', unsafe_allow_html=True)
        st.markdown(f'<p class="pg-tit">Ficha da máquina {m}</p><p class="pg-sub">Cadastro, risco previsto no período de teste, histórico de falhas e '
                    'manutenções e o comportamento dos sensores. Troque de máquina aqui ou pela barra lateral.</p>', unsafe_allow_html=True)
        # seletor da página: a frota inteira (sem os filtros da barra lateral), na ordem escolhida aqui
        todas = list(maq["id_maquina"])
        ord_pg = ordem
        st.session_state.fm_ordem_pg = ordem
        todas.sort(key=(lambda x: x) if ord_pg == "Nº da máquina" else (lambda x: (-risco_max.get(x, 0), x)))
        rot_todas = {x: f"{x} · {risco_max.get(x, 0):.0f}% · {nfal.get(x, 0)} falhas" for x in todas}
        kp = todas.index(m)
        st.session_state.ficha_maq_pg = m
        st.session_state["_fm_ids"] = ids
        with st.container(key="fm_escolha", horizontal=True, vertical_alignment="bottom"):
            st.selectbox(f"Máquina · {len(todas)} na frota", todas, key="ficha_maq_pg", format_func=rot_todas.get, on_change=_sync_pg, width=300)
            st.segmented_control("Ordenar por", ORDENS, key="fm_ordem_pg", on_change=_ordem_pg)
            st.button("◀ Anterior", key="fm_ant_pg", disabled=kp == 0, on_click=_set_maq, args=(todas[max(0, kp - 1)],))
            st.button("Próxima ▶", key="fm_prox_pg", disabled=kp == len(todas) - 1, on_click=_set_maq, args=(todas[min(len(todas) - 1, kp + 1)],))
        _cartoes([("Modelo", (lambda t: t[:1].upper() + t[1:])(str(info.get("modelo", "–")).replace("_", " "))), ("Idade", f"{info.get('idade', np.nan):.0f} anos" if pd.notna(info.get("idade")) else "–"),
                  ("Fabricante", info.get("fabricante", "–")), ("Planta", info.get("planta", "–")), ("Linha", info.get("linha_producao", "–")),
                  ("Potência", f"{info.get('potencia_kw'):.0f} kW" if pd.notna(info.get("potencia_kw")) else "–"),
                  ("Maior risco no teste", f"{risco_max.get(m, 0):.0f}%")])

        # --- risco previsto no teste
        st.markdown("### Risco previsto no período de teste")
        risco = _risco_longo(previsao)
        r = risco[risco["id_maquina"] == m].copy()
        r["Peça"] = r["peca"].map(NOME_PECA)
        r["prob"] = [prob_dia.get((m, p, f"{d:%d/%m/%Y}"), np.nan) for p, d in zip(r["peca"], r["dia"])]
        r = r[r["prob"].notna()]
        if r.empty:
            st.caption("Nenhuma data de grade desta máquina no período de teste.")
        else:
            r["Probabilidade"] = r["prob"].round(0)
            enc = dict(x=alt.X("dia:T", title="falha prevista para (06:00 de)", scale=alt.Scale(padding=26),
                               axis=alt.Axis(format="%d/%m", grid=True, labelOverlap="greedy", labelPadding=6, tickCount={"interval": "week", "step": 2},
                                             gridDash=[2, 4], gridOpacity=.55)),
                       y=alt.Y("Peça:N", title=None, sort=list(NOME_PECA.values()), axis=alt.Axis(labelPadding=10, ticks=False, domain=False)),
                       tooltip=[alt.Tooltip("dia:T", format="%d/%m/%Y", title="dia"), "Peça", alt.Tooltip("Probabilidade:Q", format=".0f", title="prob. (%)")])
            pontos = alt.Chart(r).mark_circle(opacity=.85, stroke="white", strokeWidth=1).encode(
                size=alt.Size("prob:Q", scale=alt.Scale(domain=[0, 100], range=[30, 1100]), legend=None),
                color=alt.Color("Peça:N", scale=alt.Scale(domain=list(NOME_PECA.values()), range=list(CORES.values())), legend=None), **enc)
            rotulos = alt.Chart(r[r["prob"] >= 20]).mark_text(dy=-22, fontSize=11, fontWeight="bold",
                                                               color="#e6ebf5" if tema.escuro() else "#334").encode(
                text=alt.Text("Probabilidade:Q", format=".0f"), **{k: v for k, v in enc.items() if k != "tooltip"})
            ch, th = _alt((pontos + rotulos).properties(height=230, padding={"left": 14, "top": 6, "right": 6, "bottom": 4}))
            st.altair_chart(ch, width="stretch", theme=th)
            st.caption("Cada círculo é um dia de grade da peça (múltiplo de 15 dias desde a última preventiva); o tamanho e o número mostram a probabilidade de falha (%). Nos outros dias o risco é praticamente zero.")

        # --- histórico
        st.markdown("### Histórico")
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
        st.markdown(f"### Sensores · {NOME_PECA[peca]} ({SENSOR_DA_PECA[peca]})")
        tm = tel[tel["id_maquina"] == m]
        ini, fim = tm["data_hora"].min().date(), tm["data_hora"].max().date()
        ult = fm.loc[fm["peca"] == peca, "data_hora"].max()
        if pd.notna(ult):
            pad = (max(ini, (ult - pd.Timedelta(days=21)).date()), min(fim, (ult + pd.Timedelta(days=7)).date()))
        else:
            pad = (max(ini, fim - pd.Timedelta(days=45)), fim)
        s1, _ = st.columns([1.3, 2])
        per = s1.date_input("Período", pad, min_value=ini, max_value=fim, format="DD/MM/YYYY", key=f"ficha_per_{m}_{peca}",
                            help="Por padrão, as 4 semanas em volta da última falha desta peça. Peça e resolução ficam na barra lateral.")
        if len(per) == 2:
            a, b = pd.Timestamp(per[0]), pd.Timestamp(per[1]) + pd.Timedelta(days=1)
            sen = SENSOR_DA_PECA[peca]
            x = tm[(tm["data_hora"] >= a) & (tm["data_hora"] < b)][["data_hora", sen]].dropna()
            if agr == "média diária":
                x = x.set_index("data_hora").resample("D").mean().reset_index()
            base = alt.Chart(x).mark_line(color=CORES[peca] if not tema.escuro() else {"peca_A": "#6ea8ff", "peca_B": "#f2a65a", "peca_C": "#5fd19b", "peca_D": "#c39bf0"}[peca],
                                          strokeWidth=1.2).encode(
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
            ch, th = _alt((base + regras).properties(height=280))
            st.altair_chart(ch, width="stretch", theme=th)
            st.caption("Antes de uma falha o sensor da peça costuma subir em patamar por 40–65 h; a troca derruba o sinal. "
                       "No período de teste (a partir de 30/09/2023) as falhas não são conhecidas.")
