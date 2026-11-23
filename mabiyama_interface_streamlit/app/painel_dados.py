"""Monta, a partir da pasta dados/, o JSON que o front-end (frontend/painel.js) desenha."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_curve

PECAS = ["peca_A", "peca_B", "peca_C", "peca_D"]
LIMIAR = 0.5
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

NOMES_VARIAVEIS = {
    "k1": "1º ciclo após preventiva", "k": "ciclos desde preventiva", "ewm6": "sensor · média exp. 6h",
    "ewm18": "sensor · média exp. 18h", "tmpl36": "rampa de 36h", "tmpl60": "rampa de 60h",
    "own_m24": "sensor · média 24h", "own_m12": "sensor · média 12h", "above_0.5_24": "horas acima do normal 24h",
    "above_1_12": "horas muito acima 12h", "own_vs_oth": "sensor vs outras peças", "own_frac24": "fração 24h em alerta",
    "run_0.3": "duração da rampa", "te_mp": "histórico máquina×peça",
}


def br(x, casas=0):
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def nome_peca(p):
    return "Peça " + p[-1]


def ler(pasta, nome):
    return pd.read_csv(Path(pasta) / nome)


# ------------------------------------------------------------------ previsão
def curva_calibracao(val):
    v = val.copy()
    v["pct"] = v.groupby("peca")["prob"].rank(pct=True)
    v = v.sort_values("pct")
    return v["pct"].values, v["prob"].values


def previsao_longa(sub: pd.DataFrame, val: pd.DataFrame) -> pd.DataFrame:
    """Submissão (id, peca_A..D) -> uma linha por máquina, dia e peça, com prob. calibrada.
    O escore da submissão é um ranking: o percentil entre as linhas candidatas vira a taxa de falha
    observada nesse percentil na validação temporal."""
    falta = {"id", *PECAS} - set(sub.columns)
    if falta:
        raise ValueError(f"colunas ausentes: {sorted(falta)}")
    sub = sub.copy()
    sub[["id_maquina", "dia"]] = sub["id"].str.split("_", n=1, expand=True)
    sub["dia"] = pd.to_datetime(sub["dia"])
    lg = sub.melt(id_vars=["id_maquina", "dia"], value_vars=PECAS, var_name="peca", value_name="score")
    x, y = curva_calibracao(val)
    piso = lg.groupby("peca")["score"].transform("min")
    cand = lg["score"] > piso + 1e-12
    lg["prob"] = 0.0
    pct = lg.loc[cand].groupby("peca")["score"].rank(pct=True)
    lg.loc[cand, "prob"] = np.interp(pct.values, x, y)
    return lg


def lista_dia(g, maq):
    """Candidatas de um dia (prob. > 0), da maior para a menor probabilidade, com modelo e idade da máquina."""
    g = g[g["prob"] > 0].sort_values("prob", ascending=False)
    return pd.DataFrame({
        "machine": g["id_maquina"].values,
        "comp": [nome_peca(p) for p in g["peca"]],
        "model": [maq.loc[m, "modelo"] if m in maq.index else "–" for m in g["id_maquina"]],
        "age": [None if m not in maq.index or pd.isna(maq.loc[m, "idade"]) else int(maq.loc[m, "idade"]) for m in g["id_maquina"]],
        "prob": [int(round(p * 100)) for p in g["prob"]],
    })


def dados_modelagem(pasta, sub=None):
    val = ler(pasta, "validacao.csv")
    maq = ler(pasta, "maquinas_resumo.csv").set_index("id_maquina")
    sub = ler(pasta, "previsao.csv") if sub is None else sub
    lg = previsao_longa(sub, val)

    dias = []
    for dia, g in lg.groupby("dia"):
        dias.append({
            "dia": f"{dia:%Y-%m-%d}",
            "execCurto": f"{dia:%d/%m}",
            "fimCurto": f"{dia + pd.Timedelta(days=1):%d/%m}",
            "fimLongo": f"{dia + pd.Timedelta(days=1):%d/%m/%Y}",
            "lista": lista_dia(g, maq).to_dict("records"),
        })

    # métricas da validação temporal
    ap = np.mean([average_precision_score(g["y"], g["prob"]) for _, g in val.groupby("peca")])
    v = val.copy()
    v["rk"] = v.groupby("dia_ref")["prob"].rank(ascending=False, method="first")
    recall20 = v.loc[v["y"] == 1, "rk"].le(20).mean()

    pr_p, pr_r, _ = precision_recall_curve(val["y"], val["prob"])
    base = val["y"].mean()
    pr = []
    for r in np.linspace(0, 1, 21):
        p = pr_p[pr_r >= r].max() if (pr_r >= r).any() else 0
        pr.append({"recall": round(float(r), 2), "precision": round(float(p), 3), "baseline": round(float(base), 3)})

    v["faixa"] = pd.cut(v["prob"], np.linspace(0, 1, 11), include_lowest=True)
    cal = v.groupby("faixa", observed=True).agg(bin=("prob", "mean"), real=("y", "mean"), n=("y", "size"))
    cal = cal[cal["n"] >= 5]
    cal = [{"bin": round(float(a), 3), "real": round(float(b), 3)} for a, b in zip(cal["bin"], cal["real"])]

    pv = val["prob"] > LIMIAR
    cm = {"tn": br(((~pv) & (val.y == 0)).sum()), "fp": br((pv & (val.y == 0)).sum()),
          "fn": br(((~pv) & (val.y == 1)).sum()), "tp": br((pv & (val.y == 1)).sum())}

    imp = ler(pasta, "importancia.csv").head(8)
    imp = [{"f": NOMES_VARIAVEIS.get(a, a), "v": round(float(b), 4)} for a, b in zip(imp["variavel"], imp["importancia"])]

    n_maq = int(lg["id_maquina"].nunique())
    return {
        "dias": dias, "diaInicial": 0,
        "kpi": {"ap": br(ap, 2), "apKaggle": "0,708", "recall20": f"{recall20 * 100:.0f}%", "baseline": br(base, 2),
                "maquinas": n_maq, "pares": n_maq * 4},
        "imp": imp, "pr": pr, "cal": cal, "cm": cm,
    }


# ------------------------------------------------------------------ análise exploratória
def dados_exploratoria(pasta):
    ind = ler(pasta, "indicadores.csv").iloc[0]
    ini, fim = pd.Timestamp(ind["inicio"]), pd.Timestamp(ind["fim"])

    s = ler(pasta, "sinal_pre_falha.csv").groupby("h")["z"].mean()
    sinal = [{"h": int(h), "antes": round(float(z), 2), "normal": 0} for h, z in s.items()]

    pp = ler(pasta, "falhas_por_peca.csv")
    mens = ler(pasta, "mensal.csv")
    mens["m"] = [f"{MESES[int(m[5:7]) - 1]}/{m[2:4]}" for m in mens["mes"]]
    idade = ler(pasta, "falhas_por_idade.csv")
    err = ler(pasta, "erros_pre_falha.csv")
    mod = ler(pasta, "falhas_por_modelo.csv")
    q = ler(pasta, "qualidade.csv")

    return {
        "kpi": {
            "maquinas": str(int(ind["maquinas"])),
            "maquinasSub": f"{int(ind['n_modelos'])} modelos · {int(ind['idade_min'])}–{int(ind['idade_max'])} anos",
            "falhas": br(ind["falhas"]),
            "falhasSub": f"{MESES[ini.month - 1]}/{ini:%Y} a {MESES[fim.month - 1]}/{fim:%Y}",
            "manut": br(ind["preventivas"]),
            "leituras": br(ind["leituras"] / 1e6, 1) + " mi",
        },
        "sinal": sinal,
        "porPeca": [{"c": nome_peca(a), "n": int(b)} for a, b in zip(pp["peca"], pp["falhas"])],
        "mensal": [{"m": a, "falhas": int(b), "manut": int(c)} for a, b, c in zip(mens["m"], mens["falhas"], mens["preventivas"])],
        "idade": [{"faixa": a, "taxa": round(float(b), 1)} for a, b in zip(idade["faixa"], idade["falhas_por_maquina"])],
        "erros": [{"e": a, "total": int(b), "antes": round(float(c) * 100, 1)}
                  for a, b, c in zip(err["codigo"], err["total"], err["pct_antes_falha"])],
        "modelos": [{"m": a, "maquinas": int(b), "falhas": round(float(c), 1)}
                    for a, b, c in zip(mod["modelo"], mod["maquinas"], mod["falhas_por_maquina"])],
        "qualidade": [{"t": a, "rows": br(b), "miss": br(c, 1), "dup": br(d, 1)}
                      for a, b, c, d in zip(q["tabela"], q["linhas"], q["nulos_pct"], q["duplic_pct"])],
    }


def graficos_eda(pasta):
    """Galeria da análise exploratória (Etapa 3): imagens em WebP embutidas como data URI + texto do insight."""
    import base64, json
    base = Path(pasta) / "eda"
    cat = json.loads((base / "graficos.json").read_text(encoding="utf-8"))
    for g in cat:
        g["src"] = "data:image/webp;base64," + base64.b64encode((base / g["arquivo"]).read_bytes()).decode()
    return sorted(cat, key=lambda g: g["n"])


def montar(pasta, sub=None):
    d = dados_modelagem(pasta, sub)
    d["eda"] = dados_exploratoria(pasta)
    return d
