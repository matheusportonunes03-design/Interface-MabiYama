r"""Modelos "membros" A-E: HGB / RandomForest / ExtraTrees sobre as variáveis da y09 + filtros casados (patamar do sensor da peça).

Usam a tabela L montada pelo script da y09 (montar_tudo): perfis de 96 h, ciclos e falhas inferidas (pf*_hat). Acrescentam os filtros
casados (log-verossimilhança de "patamar em curso desde s horas atrás com amplitude a", marginalizada no início s; grade de amplitudes
relativas à amplitude típica de falha de cada peça; ruído SIG = 1,25) e treinam:

  A  HGB  filtros + ciclo + sensor, com taxa por (máquina, peça) e decaimento temporal (tau 180 d)
  B  HGB  idem sem a taxa por (máquina, peça)               (melhor nota isolada em validação: AP 0,702)
  C  HGB  idem A + operação, fornecedor, firmware, id da máquina e erros em horário de pico
  D  RF   500 árvores, folha 5, decaimento temporal
  E  ET   700 árvores (entropia, folha 3) sobre as variáveis antigas (FS2) + filtros

Só linhas candidatas (D+1 em dia de grade) com pf1_hat < 0,7 entram no treino e na previsão; as demais recebem 1e-5.
Regra de ouro: toda variável da linha D usa só dados com timestamp <= D 05:00.
"""
import numpy as np
import pandas as pd
from comum_modelo import prever_binario
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier as HGB, RandomForestClassifier

import modelo_preditivo_y09 as A

MU = {"peca_A": 1.32, "peca_B": 1.06, "peca_C": 1.14, "peca_D": 1.52}       # amplitude típica do patamar de falha (z)
REL = (0.5, 0.65, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35, 1.5, 1.7, 2.0, 2.4)
BINS = [(3, 12), (12, 24), (24, 36), (36, 48), (48, 64), (64, 96)]
SIG = 1.25
GATE = 0.7
AGE = ["k", "dprev", "idade_anos", "pf1_hat", "pf_max_hat", "kany_hat", "alive_soft"]
OWN = ["own_m6", "own_m24", "own_m72", "late_early", "ctx_vibracao_mm_s"]


def _lse(x):
    mx = np.max(x, axis=0, keepdims=True)
    return (mx + np.log(np.exp(x - mx).sum(axis=0, keepdims=True))).squeeze(0)


def filtros_casados(L, mu=MU, rel=REL, sig=SIG, prefix="mf"):
    """Variáveis de filtro casado para as linhas candidatas e cand1 de L (precisa das colunas prof0..prof95)."""
    C = L.loc[L["cand"] | L["cand1"]]
    P = C[[f"prof{h}" for h in range(96)]].values.astype(float)
    M = ~np.isnan(P)
    cs = np.concatenate([np.zeros((len(P), 1)), np.cumsum(np.where(M, P, 0.0), 1)], 1)
    cn = np.concatenate([np.zeros((len(P), 1)), np.cumsum(M, 1)], 1)
    mu_r = C["peca"].map(mu).values
    out = {}
    for j, r in enumerate(rel):
        a = mu_r * r
        ll = np.stack([(a * cs[:, s + 1] - cn[:, s + 1] * a * a / 2) / sig ** 2 for s in range(3, 96)])
        out[f"{prefix}_ong{j}"] = _lse(ll) - np.log(ll.shape[0])
        for bi, (lo, hi) in enumerate(BINS):
            if r in (1.0, 1.5):
                out[f"{prefix}_ong{j}_b{bi}"] = _lse(ll[lo - 3:hi - 3]) - np.log(hi - lo)
        if r in (1.0, 1.5, 2.0):
            en = [(a * (cs[:, s + 1] - cs[:, e]) - (cn[:, s + 1] - cn[:, e]) * a * a / 2) / sig ** 2
                  for e in range(2, 40, 3) for s in range(e + 4, 96, 3)]
            out[f"{prefix}_end{j}"] = _lse(np.stack(en)) - np.log(len(en))
    F = pd.DataFrame(out, index=C.index)
    ong = [c for c in F.columns if c.startswith(prefix + "_ong") and "_b" not in c]
    base = F[ong].values
    F[f"{prefix}_best"] = base.argmax(1).astype(float)
    F[f"{prefix}_max"] = base.max(1)
    mx = base.max(1, keepdims=True)
    F[f"{prefix}_post_mean"] = (np.exp(base - mx) * np.array(rel)).sum(1) / np.exp(base - mx).sum(1)
    for c in ong:
        F[c + "_d"] = F[c] - F[f"{prefix}_max"]
    return F


def especificacoes(L, conj, xs):
    base = xs + AGE + OWN
    pico = [c for c in L.columns if c.startswith("pico_")] + ["n_erros", "n_own_codes"]
    todos = base + A.EX + ["mid"] + pico
    return {"A": dict(kind="hgb", cols=base, te=True, tau=180), "B": dict(kind="hgb", cols=base, te=False, tau=180),
            "C": dict(kind="hgb", cols=todos, te=True, tau=180), "D": dict(kind="rf", cols=base, te=True, tau=180),
            "E": dict(kind="et", cols=conj["FS2"] + xs, te=True, tau=None)}


def ajustar_prever(spec, tr, va, a0, seeds=3):
    """Treina por peça nas candidatas de tr e prevê as de va. a0 = primeiro dia da previsão (referência do decaimento temporal)."""
    t = tr[tr["cand"] & (tr["pf1_hat"].fillna(0) < GATE)].copy()
    v = va[va["cand"] & (va["pf1_hat"].fillna(0) < GATE)].copy()
    cc = list(spec["cols"])
    if spec["te"]:
        t["te_mp"], v["te_mp"] = A.taxa_maquina_peca(t, v)
        cc = cc + ["te_mp"]
    w = None if spec["tau"] is None else np.exp(-((a0 - t["dia_ref"]).dt.days.values) / spec["tau"])
    s = pd.Series(np.nan, index=v.index)
    for p in A.PECAS:
        tp, vp = t[t["peca"] == p], v[v["peca"] == p]
        wp = None if w is None else w[(t["peca"] == p).values]
        k = spec["kind"]
        if k == "hgb":
            pr = np.mean([prever_binario(HGB(max_iter=250, learning_rate=0.03, max_depth=2, min_samples_leaf=60,
                              l2_regularization=10.0, max_features=0.5, random_state=sd),
                              tp[cc], tp["y"], vp[cc], sample_weight=wp) for sd in range(seeds)], 0)
        elif k == "rf":
            pr = prever_binario(RandomForestClassifier(500, min_samples_leaf=5, max_features=0.4,
                class_weight="balanced_subsample", n_jobs=-1, random_state=0),
                tp[cc].fillna(-9), tp["y"], vp[cc].fillna(-9), sample_weight=wp)
        else:
            pr = prever_binario(ExtraTreesClassifier(700, min_samples_leaf=3, max_features=0.5, criterion="entropy",
                class_weight="balanced_subsample", n_jobs=-1, random_state=0),
                tp[cc].fillna(-9), tp["y"], vp[cc].fillna(-9))
        s.loc[vp.index] = pr
    out = pd.Series(1e-5, index=va.index)
    out.loc[v.index] = s.values
    return out


def tabela(score, teste, ids):
    """Pontuação por linha de teste -> tabela id, peca_A..peca_D na ordem de 'ids'."""
    t = teste[["id_maquina", "dia_ref", "peca"]].copy()
    t["p"] = score.reindex(teste.index).fillna(1e-5).values
    e = t.pivot_table(index=["id_maquina", "dia_ref"], columns="peca", values="p").reset_index()
    e["id"] = e["id_maquina"] + "_" + e["dia_ref"].dt.strftime("%Y-%m-%d")
    return e[["id"] + A.PECAS].set_index("id").loc[ids].reset_index()


def membros(L, conj, ids, nomes=("A", "B", "C", "D", "E"), seeds=3):
    """Treina os membros em todas as linhas rotuladas e devolve {nome: tabela de teste}."""
    F = filtros_casados(L)
    L = L.join(F)
    rot = L[L["y_known"] & ~L["incerto"]]
    teste = L[L["dia_ref"].between(A.INICIO_TESTE, A.INICIO_TESTE + pd.Timedelta(days=A.DIAS_TESTE - 1))].copy()
    spec = especificacoes(L, conj, list(F.columns))
    out = {}
    for n in nomes:
        print(f"   membro {n} ({spec[n]['kind']})", flush=True)
        out[n] = tabela(ajustar_prever(spec[n], rot, teste, A.INICIO_TESTE, seeds), teste, ids)
    return out
