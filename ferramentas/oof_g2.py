"""OOF da fusão g2 (3 melhores posições, k=10; y09 + v2 + membros A-E) nas 3 janelas de validação."""
import pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/etapa4/modelos")
import modelo_preditivo_v2 as B
RES = Path("/home/claude/etapa4/resultados")
Y09 = ["sub41", "sub43", "sub42", "sub44", "sub40", "p06"]; V2 = ["v2_1.25", "v2_1.0", "v2_1.6"]; MEM = ["mem_" + n for n in "ABCDE"]
G2 = Y09 + V2 + MEM
def fusao(X, keep=3, k=10):
    pe = X.index.get_level_values(1)
    Rk = X.groupby(pe).rank(ascending=False).values
    v = 1 / (k + Rk)
    return np.sort(v, 1)[:, ::-1][:, :keep].mean(1)
out = []
for a, z in B.JANELAS:
    r = pickle.load(open(RES / "oof" / f"y09mem_{a}.pkl", "rb")); yy = r.pop("_y")
    for sg in (1.25, 1.0, 1.6): r[f"v2_{sg}"] = pickle.load(open(RES / "oof" / f"v2_{sg}_{a}.pkl", "rb")).reindex(yy.index).fillna(1e-5)
    X = pd.DataFrame(r)[G2]
    C = pickle.load(open(RES / "cache" / f"janela_{a}.pkl", "rb"))[0]
    va0 = C[(C.dia_ref >= pd.Timestamp(a)) & (C.dia_ref <= pd.Timestamp(z)) & ~C.dia_ref.isin(B.INCERTOS)]
    cand = pd.MultiIndex.from_arrays([va0.id_maquina, va0.peca, va0.dia_ref])
    t = yy.rename("y").to_frame()
    t["score"] = fusao(X)
    t["cand"] = t.index.isin(cand)
    t["janela"] = a
    info = va0.set_index(["id_maquina", "peca", "dia_ref"])[["k", "mf_max", "pf1"]]
    t = t.join(info)
    out.append(t.reset_index())
T = pd.concat(out, ignore_index=True)
T.to_pickle("oof_g2.pkl")
from sklearn.metrics import average_precision_score as aps
for a, g in T.groupby("janela"):
    print(a, np.mean([aps(h.y, h.score) for _, h in g.groupby("peca")]), g.cand.sum(), g.y.sum(), g[g.cand].y.sum())
