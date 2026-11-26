"""Gera dados/extras.json para o painel: replay da frota, simulador de política e raio-X da falha.
Tudo vem da validação temporal (3 janelas de 2023), onde as falhas reais são conhecidas.
Uso: python gerar_extras.py  (precisa de oof_g2.pkl, gerado por oof_g2.py, e dos CSV tratados)."""
import json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/etapa4/modelos"); sys.path.insert(0, "/home/claude/app")
import modelo_preditivo_v2 as B
import painel_dados as PD
DADOS = Path("/home/claude/tratadas"); RES = Path("/home/claude/etapa4/resultados")
APP = Path("/home/claude/app/dados")
PEC = B.PECAS

T = pd.read_pickle("oof_g2.pkl")
val = pd.read_csv(APP / "validacao.csv")
x, y = PD.curva_calibracao(val)
c = T[T.cand].copy()
c["pct"] = c.groupby("peca").score.rank(pct=True)
c["prob"] = np.interp(c.pct, x, y)
T = T.merge(c[["id_maquina", "peca", "dia_ref", "prob"]], how="left")

maq = pd.read_csv(DADOS / "maquinas_corrigido.csv")
maq = maq.sort_values(["linha_producao", "id_maquina"]).reset_index(drop=True)
mi = {m: i for i, m in enumerate(maq.id_maquina)}
pi = {p: i for i, p in enumerate(PEC)}
dias = sorted(T.dia_ref.unique())
porDia = []
for d in dias:
    g = T[T.dia_ref == d]
    cand = g[g.cand].sort_values("prob", ascending=False)
    fora = g[~g.cand & (g.y == 1)]
    porDia.append({
        "c": [[mi[m], pi[p], round(float(pr) * 100, 1), int(yy)] for m, p, pr, yy in zip(cand.id_maquina, cand.peca, cand.prob, cand.y)],
        "f": [[mi[m], pi[p]] for m, p in zip(fora.id_maquina, fora.peca)],
    })
replay = {
    "maquinas": [{"id": r.id_maquina, "linha": r.linha_producao, "modelo": r.modelo.replace("modelo_", ""),
                  "idade": None if pd.isna(r.idade) else int(r.idade), "cap": float(r.capacidade_nominal_h)} for r in maq.itertuples()],
    "pecas": ["A", "B", "C", "D"],
    "dias": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in dias],
    "janelas": [a for a, _ in B.JANELAS],
    "porDia": porDia,
}

# ---------------- custos observados (para o simulador)
man = pd.read_csv(DADOS / "manutencao_corrigido.csv")
custos = {p[-1]: round(float(g.custo_troca_reais.median()), 0) for p, g in man.groupby("peca")}
dur = man.groupby("tipo").duracao_min.median().to_dict()
simul = {"custoPeca": custos, "duracaoMin": {k: float(v) for k, v in dur.items()}}

# ---------------- raio-X: série horária do sensor da peça + detector (filtro casado) hora a hora
tel, *_ = B.carregar(DADOS)
Z = B.z_telemetria(tel, B.FIM_NORMAL)
base_k = c.assign(kk=c.k.clip(upper=10)).groupby("kk").y.mean()

def detector(m, p, d, mu):
    s, sg = B.SENSOR[p]
    serie = Z[s][m] * sg
    corte = pd.Timestamp(d) + pd.Timedelta(hours=5)
    horas = np.arange(-120, 26)
    zz = serie.reindex([corte + pd.Timedelta(hours=int(h)) for h in horas]).values
    alvo = horas[horas <= 0]
    P = np.full((len(alvo), B.H), np.nan)
    for i, h in enumerate(alvo):
        t = corte + pd.Timedelta(hours=int(h))
        P[i] = serie.reindex([t - pd.Timedelta(hours=j) for j in range(B.H)]).values
    F = B.filtros_casados(P, pd.Series([p] * len(P)), mu)
    llr, bs, ba = B.caixa_livre(P[-1:])
    return horas, zz, F["mf_max"].values, int(bs[0]), s

def escolher(cond, ordem, asc=False):
    g = c[cond].sort_values(ordem, ascending=asc)
    return g.iloc[0]

exemplos = [
    ("pega", "Falha antecipada", "O sensor sai do normal e forma um patamar horas antes do corte das 05:00. O filtro casado reconhece o formato e a probabilidade dispara.",
     escolher((c.y == 1) & (c.prob > .85) & c.mf_max.between(15, 40), "mf_max")),
    ("sutil", "Patamar sutil", "O desvio é pequeno e ruidoso: um limiar simples no sensor não veria nada, mas o filtro casado soma a evidência hora a hora.",
     escolher((c.y == 1) & (c.prob > .5) & c.mf_max.between(3, 8), "prob")),
    ("perdida", "Falha sem aviso", "Até 05:00 o sensor está no normal. A falha acontece depois do corte, então nenhum modelo honesto poderia antecipá-la: é o limite do problema (~1 em 4 falhas).",
     escolher((c.y == 1) & (c.prob < .06) & (c.mf_max < -1), "mf_max", True)),
    ("alarme", "Alarme falso", "Há um patamar forte, mas a peça não falha na janela. Esses casos explicam parte dos erros do topo da lista.",
     escolher((c.y == 0) & (c.prob > .8), "prob")),
]
raiox = []
for chave, titulo, texto, r in exemplos:
    a = r.janela if "janela" in r else None
    a = T.loc[(T.id_maquina == r.id_maquina) & (T.peca == r.peca) & (T.dia_ref == r.dia_ref), "janela"].iloc[0]
    mu = pickle.load(open(RES / "cache" / f"janela_{a}.pkl", "rb"))[2]
    horas, zz, det, bs, sensor = detector(r.id_maquina, r.peca, r.dia_ref, mu)
    k = int(min(r.k, 10)); p0 = float(base_k.get(k, c.y.mean()))
    lo = np.log(p0 / (1 - p0))
    post = 1 / (1 + np.exp(-(np.clip(det, -30, 30) + lo)))
    dref = pd.Timestamp(r.dia_ref)
    raiox.append({
        "chave": chave, "titulo": titulo, "texto": texto, "maquina": r.id_maquina, "peca": r.peca[-1], "sensor": sensor.replace("_", " "),
        "dia": dref.strftime("%d/%m/%Y"), "diaFalha": (dref + pd.Timedelta(days=1)).strftime("%d/%m/%Y"), "falhou": int(r.y),
        "prob": round(float(r.prob) * 100, 1), "k": int(r.k), "p0": round(p0 * 100, 1), "inicio": -bs,
        "h": horas.tolist(), "z": [None if np.isnan(v) else round(float(v), 2) for v in zz],
        "det": [round(float(v), 2) for v in det], "post": [round(float(v) * 100, 1) for v in post],
    })
    print(chave, r.id_maquina, r.peca, r.dia_ref.date(), round(r.prob, 3), round(r.mf_max, 1), "k", r.k, "inicio", -bs)

json.dump({"replay": replay, "simul": simul, "raiox": raiox}, open(APP / "extras.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("ok", (APP / "extras.json").stat().st_size)
