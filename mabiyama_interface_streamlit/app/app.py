"""MaBiYama · Painel da Frota Industrial (Streamlit).

Reproduz o painel do Lovable em Python, com três telas:
  - Previsão & Modelagem: máquinas com maior risco, prioridade de manutenção, métricas e gráficos do modelo
  - Análise Exploratória: indicadores e gráficos da base histórica
  - Perfil: dados do usuário logado

Os números saem dos arquivos da pasta `dados/` (veja README.md). O botão "Enviar dados do dia" aceita uma
nova previsão no formato da submissão (id, peca_A, peca_B, peca_C, peca_D) e substitui a da pasta.

Rodar:  streamlit run app.py
"""
import hashlib
import hmac
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DADOS = Path(__file__).resolve().parent / "dados"
PECAS = ["peca_A", "peca_B", "peca_C", "peca_D"]
NOME_PECA = {"peca_A": "Peça A", "peca_B": "Peça B", "peca_C": "Peça C", "peca_D": "Peça D"}
SENSOR_DA_PECA = {"peca_A": "sensor C", "peca_B": "sensor D", "peca_C": "sensor B", "peca_D": "sensor A"}  # rótulos
LIMIAR = 0.5

# Métricas do modelo mostradas nos cartões. Atualize quando houver uma submissão melhor.
METRICAS = {
    "ap_kaggle": 0.69146,          # score público do Kaggle da previsão em uso (y01)
    "ap_validacao": None,           # calculado de dados/validacao.csv
}

AZUL, AZUL_CLARO, ROXO, LARANJA, CINZA = "#0B4FCB", "#6FB8F0", "#5B2D90", "#F5A623", "#8A94A6"

st.set_page_config(page_title="MaBiYama · Painel da Frota", page_icon="⚙️", layout="wide")

# ------------------------------------------------------------------ estilo
st.markdown(f"""
<style>
  .block-container {{padding-top: 1.2rem; max-width: 1200px;}}
  .hero {{background: linear-gradient(110deg, #0039A6 0%, {AZUL} 45%, {AZUL_CLARO} 100%);
          border-radius: 18px; padding: 28px 32px 22px; color: white; margin-bottom: 18px;}}
  .hero .sup {{letter-spacing: .25em; font-size: .78rem; font-weight: 700; opacity: .85;}}
  .hero h1 {{color: white; font-style: italic; font-weight: 800; margin: 4px 0 0; font-size: 2.1rem;}}
  .alerta {{background: #F7F0E6; border-left: 5px solid {LARANJA}; border-radius: 12px; padding: 18px 20px 10px;
            margin-bottom: 18px;}}
  .alerta h3 {{margin: 0; font-size: 1.15rem;}}
  .alerta .sub {{color: #6B7280; font-size: .85rem; margin: 2px 0 12px;}}
  .card-risco {{background: white; border-radius: 12px; padding: 12px 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08);
                display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;}}
  .card-risco .m {{font-weight: 700; font-size: 1.05rem;}}
  .card-risco .d {{color: #6B7280; font-size: .82rem;}}
  .card-risco .p {{color: {ROXO}; font-weight: 800; font-size: 1.6rem;}}
  .kpi {{background: white; border: 1px solid #E5E7EB; border-radius: 14px; padding: 14px 18px; height: 100%;}}
  .kpi .t {{color: #6B7280; font-size: .85rem;}}
  .kpi .v {{font-size: 1.9rem; font-weight: 800; color: #111827; line-height: 1.2;}}
  .kpi .s {{color: #9CA3AF; font-size: .78rem;}}
  div[data-testid="stTabs"] button p {{font-size: 1rem; font-weight: 600;}}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ login
def _hash(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def autenticar(email: str, senha: str) -> bool:
    """Compara com os hashes SHA-256 em .streamlit/secrets.toml (seção [usuarios]). Nenhuma senha fica no código."""
    usuarios = st.secrets.get("usuarios", {}) if hasattr(st, "secrets") else {}
    alvo = usuarios.get(email.strip().lower(), {})
    return bool(alvo) and hmac.compare_digest(_hash(senha), alvo.get("senha_sha256", ""))


def tela_login():
    col = st.columns([1, 1.2, 1])[1]
    with col:
        st.markdown(f"<div class='hero'><div class='sup'>MANUTENÇÃO PREDITIVA</div><h1>MaBiYama</h1>"
                    f"<div style='opacity:.9'>Acesse sua frota</div></div>", unsafe_allow_html=True)
        with st.form("login"):
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            ok = st.form_submit_button("Entrar", width="stretch", type="primary")
        if ok:
            if autenticar(email, senha):
                usuarios = st.secrets["usuarios"]
                st.session_state.usuario = {"email": email.strip().lower(),
                                            "nome": usuarios[email.strip().lower()].get("nome", email.split("@")[0])}
                st.rerun()
            else:
                st.error("Email ou senha incorretos.")
        st.caption("MaBiYama · Poli Júnior")


# ------------------------------------------------------------------ carregamento de dados
@st.cache_data
def ler_previsao(conteudo: bytes | None = None) -> pd.DataFrame:
    """Formato da submissão -> uma linha por (máquina, dia, peça)."""
    if conteudo is not None:
        import io
        sub = pd.read_csv(io.BytesIO(conteudo))
    else:
        sub = pd.read_csv(DADOS / "previsao.csv")
    falta = {"id", *PECAS} - set(sub.columns)
    if falta:
        raise ValueError(f"colunas ausentes: {sorted(falta)}")
    sub[["id_maquina", "dia"]] = sub["id"].str.split("_", n=1, expand=True)
    sub["dia"] = pd.to_datetime(sub["dia"])
    longo = sub.melt(id_vars=["id_maquina", "dia"], value_vars=PECAS, var_name="peca", value_name="score")
    # o score da submissão é um ranking por peça, não uma probabilidade: converte em prob. calibrada
    # usando a curva da validação temporal (percentil dentro das linhas candidatas -> taxa de falha observada)
    longo["prob"] = calibrar(longo)
    return longo


@st.cache_data
def curva_calibracao() -> tuple[np.ndarray, np.ndarray]:
    v = pd.read_csv(DADOS / "validacao.csv")
    v["pct"] = v.groupby("peca")["prob"].rank(pct=True)
    v = v.sort_values("pct")
    return v["pct"].values, v["prob"].values


def calibrar(longo: pd.DataFrame) -> np.ndarray:
    x, y = curva_calibracao()
    piso = longo.groupby("peca")["score"].transform("min")
    cand = longo["score"] > piso + 1e-12
    # percentil calculado contra as candidatas de todo o período da previsão
    pct_total = longo.loc[cand].groupby("peca")["score"].rank(pct=True)
    p = np.zeros(len(longo))
    p[cand.values] = np.interp(pct_total.values, x, y)
    return p


@st.cache_data
def ler_csv(nome):
    return pd.read_csv(DADOS / nome)


def ler_maquinas():
    return ler_csv("maquinas_resumo.csv")


# ------------------------------------------------------------------ componentes visuais
def kpi(titulo, valor, sub=""):
    st.markdown(f"<div class='kpi'><div class='t'>{titulo}</div><div class='v'>{valor}</div>"
                f"<div class='s'>{sub}</div></div>", unsafe_allow_html=True)


def fig_base(fig, altura=320, legenda=True):
    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white",
                      paper_bgcolor="white", showlegend=legenda,
                      legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"))
    fig.update_xaxes(showgrid=False, linecolor="#E5E7EB")
    fig.update_yaxes(gridcolor="#F1F3F7", zeroline=False)
    return fig


def fmt_pct(x):
    return f"{x * 100:.0f}%"


def fmt_int(x):
    return f"{x:,.0f}".replace(",", ".")


# ------------------------------------------------------------------ telas
def cabecalho():
    st.markdown("<div class='hero'><div class='sup'>MANUTENÇÃO PREDITIVA · MABIYAMA</div>"
                "<h1>Painel da Frota Industrial</h1></div>", unsafe_allow_html=True)
    with st.expander("⬆️  Enviar dados do dia"):
        arq = st.file_uploader("Previsão no formato da submissão (id, peca_A, peca_B, peca_C, peca_D)", type="csv")
        if arq is not None:
            try:
                ler_previsao(arq.getvalue())
                st.session_state.previsao_bytes = arq.getvalue()
                st.success(f"Previsão carregada: {arq.name}")
            except Exception as e:  # formato inválido
                st.error(f"Não consegui ler o arquivo: {e}")


def alerta_top5(dia_df, maq):
    top = dia_df.nlargest(5, "prob").merge(maq[["id_maquina", "modelo"]], on="id_maquina", how="left")
    st.markdown(f"<div class='alerta'><h3>⚠️ Atenção: cinco máquinas com maior risco</h3>"
                f"<div class='sub'>Falha até 06:00 de {(dia_df['dia'].iloc[0] + pd.Timedelta(days=1)):%d/%m/%Y}"
                f"</div>", unsafe_allow_html=True)
    cols = st.columns(2)
    for i, r in enumerate(top.itertuples()):
        with cols[i % 2]:
            st.markdown(f"<div class='card-risco'><div><div class='m'>{r.id_maquina}</div>"
                        f"<div class='d'>{NOME_PECA[r.peca]} · {r.modelo}</div></div>"
                        f"<div class='p'>{fmt_pct(r.prob)}</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def tela_previsao():
    maq = ler_maquinas()
    prev = ler_previsao(st.session_state.get("previsao_bytes"))
    dias = sorted(prev["dia"].unique())
    c1, c2 = st.columns([1, 3])
    dia = c1.selectbox("Dia da previsão (dados até 05:00)", dias, index=0,
                       format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"))
    d = prev[prev["dia"] == dia].copy()

    alerta_top5(d, maq)

    v = pd.read_csv(DADOS / "validacao.csv")
    from sklearn.metrics import average_precision_score, precision_recall_curve
    ap_val = np.mean([average_precision_score(g["y"], g["prob"]) for _, g in v.groupby("peca")])
    k = st.columns(4)
    with k[0]:
        kpi("Peças em alto risco", int((d["prob"] > LIMIAR).sum()), f"prob. > {LIMIAR:.0%} até 06:00 de amanhã")
    with k[1]:
        kpi("AP (validação temporal)", f"{ap_val:.2f}".replace(".", ","),
            f"Kaggle público: {METRICAS['ap_kaggle']:.3f}".replace(".", ","))
    with k[2]:
        rec = recall_top_k(v, 5)
        kpi("Recall do alerta (top-5/dia)", fmt_pct(rec), "falhas que estariam nos 5 cartões do dia")
    with k[3]:
        kpi("Última previsão", "05:00", f"{pd.Timestamp(dia):%d/%m} · {d['id_maquina'].nunique() * 4} pares máquina×peça")

    st.subheader("Prioridade de manutenção · dia selecionado")
    tab = (d.nlargest(10, "prob").merge(maq[["id_maquina", "modelo", "idade"]], on="id_maquina", how="left")
           .assign(peca=lambda x: x["peca"].map(NOME_PECA)))
    tab.insert(0, "#", range(1, len(tab) + 1))
    st.dataframe(
        tab[["#", "id_maquina", "modelo", "peca", "idade", "prob"]].rename(
            columns={"id_maquina": "Máquina", "modelo": "Modelo", "peca": "Peça", "idade": "Idade (anos)",
                     "prob": "Prob. de falha"}),
        hide_index=True, width="stretch",
        column_config={"Prob. de falha": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
                       "Idade (anos)": st.column_config.NumberColumn(format="%d")})

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Importância das variáveis**")
        imp = pd.read_csv(DADOS / "importancia.csv").head(10).iloc[::-1]
        imp["nome"] = imp["variavel"].map(NOMES_VARIAVEIS).fillna(imp["variavel"])
        st.plotly_chart(fig_base(go.Figure(go.Bar(x=imp["importancia"], y=imp["nome"], orientation="h",
                                                   marker_color=AZUL)), legenda=False), width="stretch")
    with g2:
        st.markdown("**Precisão × recall (validação temporal)**")
        fig = go.Figure()
        for p, g in v.groupby("peca"):
            pr, rc, _ = precision_recall_curve(g["y"], g["prob"])
            fig.add_trace(go.Scatter(x=rc, y=pr, mode="lines", name=NOME_PECA[p]))
        fig.update_xaxes(title="Recall", range=[0, 1]); fig.update_yaxes(title="Precisão", range=[0, 1.02])
        st.plotly_chart(fig_base(fig), width="stretch")

    g3, g4 = st.columns(2)
    with g3:
        st.markdown("**Calibração das probabilidades**")
        v["faixa"] = pd.cut(v["prob"], [-0.01, .02, .05, .1, .2, .4, .6, .8, 1.0])
        cal = v.groupby("faixa", observed=True).agg(prev=("prob", "mean"), real=("y", "mean"), n=("y", "size"))
        fig = go.Figure([go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(dash="dash", color=CINZA),
                                    name="Perfeita"),
                         go.Scatter(x=cal["prev"], y=cal["real"], mode="lines+markers", name="Modelo",
                                    marker=dict(size=8, color=ROXO), line=dict(color=ROXO))])
        fig.update_xaxes(title="Prob. prevista", range=[0, 1]); fig.update_yaxes(title="Taxa real", range=[0, 1])
        st.plotly_chart(fig_base(fig), width="stretch")
    with g4:
        st.markdown(f"**Matriz de confusão (limiar {LIMIAR:.1f})**".replace(".", ","))
        pr_ = v["prob"] > LIMIAR
        m = np.array([[((~pr_) & (v.y == 0)).sum(), (pr_ & (v.y == 0)).sum()],
                      [((~pr_) & (v.y == 1)).sum(), (pr_ & (v.y == 1)).sum()]])
        fig = go.Figure(go.Heatmap(z=m, x=["Prev. ok", "Prev. falha"], y=["Real ok", "Real falha"],
                                   text=[[fmt_int(a) for a in r] for r in m], texttemplate="%{text}",
                                   textfont=dict(size=18), colorscale=[[0, "#EEF4FF"], [1, AZUL]], showscale=False))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_base(fig, legenda=False), width="stretch")
        st.caption("Linhas candidatas (D+1 em dia de grade) das 3 janelas de validação temporal.")

    st.markdown("**Resumo da previsão**")
    r = st.columns(3)
    r[0].metric("Execução", f"{pd.Timestamp(dia):%d/%m} · 05:00")
    r[1].metric("Cobertura", f"{d['id_maquina'].nunique()} máquinas · {len(d)} pares")
    r[2].metric("Fim da janela", f"{pd.Timestamp(dia) + pd.Timedelta(days=1):%d/%m} · 06:00")


def recall_top_k(v, k):
    """Fração das falhas que estariam entre as k linhas de maior prob. no próprio dia."""
    if "dia_ref" not in v:
        return np.nan
    v = v.copy()
    v["rk"] = v.groupby("dia_ref")["prob"].rank(ascending=False, method="first")
    return v.loc[v["y"] == 1, "rk"].le(k).mean()


NOMES_VARIAVEIS = {
    "k1": "1º ciclo após preventiva", "ewm6": "sensor · média exp. 6h", "ewm18": "sensor · média exp. 18h",
    "tmpl36": "rampa de 36h", "tmpl60": "rampa de 60h", "own_m24": "sensor · média 24h", "own_m12": "sensor · média 12h",
    "above_0.5_24": "horas acima do normal (24h)", "above_1_12": "horas muito acima (12h)",
    "own_vs_oth": "sensor vs outras peças", "own_frac24": "fração 24h em alerta", "run_0.3": "duração da rampa",
}


def tela_exploratoria():
    ind = ler_csv("indicadores.csv").iloc[0]
    k = st.columns(4)
    with k[0]:
        kpi("Máquinas", int(ind["maquinas"]), f"{int(ind['n_modelos'])} modelos · {int(ind['idade_min'])}–{int(ind['idade_max'])} anos")
    with k[1]:
        kpi("Falhas", fmt_int(ind["falhas"]), f"{pd.Timestamp(ind['inicio']):%m/%Y} a {pd.Timestamp(ind['fim']):%m/%Y}")
    with k[2]:
        kpi("Trocas preventivas", fmt_int(ind["preventivas"]), "grade de 15 dias")
    with k[3]:
        kpi("Leituras de sensores", f"{ind['leituras'] / 1e6:.1f} mi".replace(".", ","), "4 sensores + vibração · horária")

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Sinal antes da falha · sensor da peça (48h)**")
        s = ler_csv("sinal_pre_falha.csv")
        fig = go.Figure()
        for p, g in s.groupby("peca"):
            fig.add_trace(go.Scatter(x=g["h"], y=g["z"], mode="lines", name=f"{NOME_PECA[p]} ({SENSOR_DA_PECA[p]})"))
        fig.add_vrect(x0=-24, x1=0, fillcolor=LARANJA, opacity=0.08, line_width=0, annotation_text="janela 24h")
        fig.add_hline(y=0, line_dash="dot", line_color=CINZA, annotation_text="operação normal")
        fig.update_xaxes(title="horas até a falha"); fig.update_yaxes(title="desvio do normal (z)")
        st.plotly_chart(fig_base(fig), width="stretch")
    with g2:
        st.markdown("**Falhas por peça**")
        c = ler_csv("falhas_por_peca.csv")
        st.plotly_chart(fig_base(go.Figure(go.Bar(x=c["peca"].map(NOME_PECA), y=c["falhas"], marker_color=AZUL,
                                                   text=c["falhas"])), legenda=False), width="stretch")

    g3, g4 = st.columns(2)
    with g3:
        st.markdown("**Falhas × trocas preventivas por mês**")
        m = ler_csv("mensal.csv")
        x = pd.to_datetime(m["mes"]).dt.strftime("%b/%y")
        fig = go.Figure([go.Bar(x=x, y=m["preventivas"], name="Preventivas", marker_color=AZUL_CLARO),
                         go.Scatter(x=x, y=m["falhas"], name="Falhas", yaxis="y2", mode="lines+markers",
                                    line=dict(color=ROXO, width=3))])
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, title="falhas"),
                          yaxis=dict(title="preventivas"))
        st.plotly_chart(fig_base(fig), width="stretch")
    with g4:
        st.markdown("**Falhas por máquina, por faixa de idade**")
        r = ler_csv("falhas_por_idade.csv")
        st.plotly_chart(fig_base(go.Figure(go.Bar(x=r["faixa"], y=r["falhas_por_maquina"], marker_color=AZUL,
                                                   text=r["falhas_por_maquina"].round(1))), legenda=False),
                        width="stretch")

    g5, g6 = st.columns(2)
    with g5:
        st.markdown("**Erros: volume × % nas 24h antes de uma falha**")
        r = ler_csv("erros_pre_falha.csv")
        fig = go.Figure([go.Bar(x=r["codigo"], y=r["total"], name="Total", marker_color=AZUL_CLARO),
                         go.Scatter(x=r["codigo"], y=r["pct_antes_falha"] * 100, name="Antes de falha (%)", yaxis="y2",
                                    mode="lines+markers", line=dict(color=ROXO, width=3))])
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, ticksuffix="%"))
        st.plotly_chart(fig_base(fig), width="stretch")
    with g6:
        st.markdown("**Falhas por modelo de máquina**")
        r = ler_csv("falhas_por_modelo.csv")
        fig = go.Figure([go.Bar(x=r["modelo"], y=r["maquinas"], name="Máquinas", marker_color=AZUL_CLARO),
                         go.Scatter(x=r["modelo"], y=r["falhas_por_maquina"], name="Falhas/máquina", yaxis="y2",
                                    mode="lines+markers", line=dict(color=ROXO, width=3))])
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False))
        st.plotly_chart(fig_base(fig), width="stretch")

    st.markdown("**Qualidade das bases tratadas**")
    q = ler_csv("qualidade.csv")
    q["Status"] = np.where(q["duplic_pct"] < 1, "OK", "Revisar")
    q["linhas"] = q["linhas"].map(fmt_int)
    q["nulos_pct"] = q["nulos_pct"].map(lambda v: f"{v:.1f}%")
    q["duplic_pct"] = q["duplic_pct"].map(lambda v: f"{v:.1f}%")
    st.dataframe(q.rename(columns={"tabela": "Tabela", "linhas": "Linhas", "nulos_pct": "Nulos", "duplic_pct": "Duplic."}),
                 hide_index=True, width="stretch")


def tela_perfil():
    u = st.session_state.usuario
    st.subheader("Dados pessoais")
    c1, c2 = st.columns([1, 3])
    with c1:
        foto = st.file_uploader("Alterar foto", type=["jpg", "jpeg", "png", "webp"], help="até 5 MB")
        if foto is not None and foto.size <= 5 * 1024 * 1024:
            st.session_state.foto = foto.getvalue()
        if "foto" in st.session_state:
            st.image(st.session_state.foto, width=140)
        else:
            st.markdown("<div style='font-size:4rem;text-align:center'>👤</div>", unsafe_allow_html=True)
    with c2:
        nome = st.text_input("Nome", value=u["nome"])
        st.text_input("Email", value=u["email"], disabled=True)
        if st.button("Salvar", type="primary"):
            st.session_state.usuario["nome"] = nome
            st.success("Dados atualizados nesta sessão.")
    st.divider()
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()


# ------------------------------------------------------------------ main
def main():
    if "usuario" not in st.session_state:
        tela_login()
        return
    cabecalho()
    t1, t2, t3 = st.tabs(["Previsão & Modelagem", "Análise Exploratória", "👤 Perfil"])
    with t1:
        tela_previsao()
    with t2:
        tela_exploratoria()
    with t3:
        tela_perfil()
    st.caption("MaBiYama · Poli Júnior")


main()
