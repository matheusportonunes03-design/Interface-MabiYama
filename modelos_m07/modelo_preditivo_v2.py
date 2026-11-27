r"""MaBiYama - modelo preditivo de falha por peça (máquina x dia) - v2, escrito do zero (não usa o código anterior).

IDEIA CENTRAL (descoberta na análise dos dados)
  * Falha só acontece em "dias de grade": D+1 cai num múltiplo de 15 dias desde a última troca preventiva (99,4% dos positivos).
    Só essas linhas ("candidatas") entram no modelo; as demais recebem pontuação mínima.
  * Antes de uma falha o sensor da peça sobe em PATAMAR (caixa) de ~1-1,5 desvio por 40-65 h; o patamar acaba na troca.
    Metade dos patamares são falsos alarmes (amplitude ~1,5x maior, ou terminam sem falha). O ruído horário é branco, sd ~ 1.
  * Por isso as variáveis principais são FILTROS CASADOS: log-verossimilhança de "patamar em curso desde s horas atrás com amplitude a"
    (marginalizada no início s; grade de amplitudes relativas à amplitude típica de falha de cada peça) e de "patamar que já terminou".
    O modelo aprende a separar amplitude de falha x amplitude de falso alarme e a idade do patamar.
  * Falhas passadas (ciclos anteriores) trocam a peça e zeram o risco. A tabela de manutenção no período de teste não traz corretivas,
    então elas são INFERIDAS por um detector (rampa antes + queda depois da data de grade), ajustado fora-da-amostra no treino.
  * Regra de ouro respeitada: toda variável da linha D usa só dados com timestamp <= D 05:00 (preventivas só até D-1 06:00;
    a preventiva lançada em D+1 06:00, mesmo existindo no arquivo, NÃO é usada).

PIPELINE: dados -> grade de candidatas -> perfis 96 h -> filtros casados -> detector de falha passada -> idade/ciclos ->
          modelos (HGB x3, RandomForest, ExtraTrees; 3 sementes) -> fusão RRF -> tabela de submissão.

Uso:
  python modelo_preditivo_v2.py --dados <pasta com os csv tratados> --saida <pasta> [--seeds 3] [--validar]
  (--validar roda 3 janelas temporais com o mesmo código, treinando só com dias anteriores a cada janela)
Entradas: telemetria_corrigido.csv, manutencao_corrigido.csv, falhas_corrigido.csv, maquinas_corrigido.csv.
"""
import argparse
import json
import platform
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from comum_modelo import normalizar, prever_binario
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score

warnings.filterwarnings("ignore")

PECAS = ["peca_A", "peca_B", "peca_C", "peca_D"]
SENSOR = {"peca_A": ("sensor_c", 1), "peca_B": ("sensor_d", 1), "peca_C": ("sensor_b", -1), "peca_D": ("sensor_a", 1)}
FIM_NORMAL = pd.Timestamp("2023-09-30 05:00")   # o "normal" de cada máquina usa só o período de treino (ver --corte em validação)
INICIO_TESTE, DIAS_TESTE = pd.Timestamp("2023-09-30"), 92
ULTIMO_ROTULO = pd.Timestamp("2023-09-29")       # D+1 06:00 <= 30/09 06:00: último lançamento conhecido
INCERTOS = [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")]   # lote suspeito de 02/01 03:00
H = 96                                           # horas de perfil
SIG = 1.25                                       # desvio efetivo do filtro casado (calibrado em validação)
REL = (0.5, 0.65, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35, 1.5, 1.7, 2.0, 2.4)   # amplitudes relativas à típica de falha
BINS = [(3, 12), (12, 24), (24, 36), (36, 48), (48, 64), (64, 96)]
JANELAS = [("2022-12-31", "2023-03-30"), ("2023-03-31", "2023-06-29"), ("2023-06-30", "2023-09-29")]
GATE = 0.7
MU_ESCALA = 1.0                                  # variantes: escala da amplitude típica de falha
DROP_COLS = []                                   # variantes: variáveis retiradas do modelo
MU_PADRAO = {"peca_A": 1.32, "peca_B": 1.06, "peca_C": 1.14, "peca_D": 1.52}


# ---------------------------------------------------------------- dados
def carregar(d):
    d = Path(d)
    tel = pd.read_csv(d / "telemetria_corrigido.csv", parse_dates=["data_hora"],
                      usecols=["id_maquina", "data_hora", "sensor_a", "sensor_b", "sensor_c", "sensor_d", "vibracao_mm_s"])
    man = pd.read_csv(d / "manutencao_corrigido.csv", parse_dates=["data_hora"], usecols=["data_hora", "id_maquina", "peca", "tipo"])
    fal = pd.read_csv(d / "falhas_corrigido.csv", parse_dates=["data_hora"])
    maq = pd.read_csv(d / "maquinas_corrigido.csv")
    return tel, man, fal, maq


def z_telemetria(tel, fim_normal):
    """z robusto por máquina (mediana/MAD só do período normal) com o modo comum da frota (mesma hora) removido."""
    idx = pd.date_range(tel["data_hora"].min(), tel["data_hora"].max(), freq="h")
    maquinas = sorted(tel["id_maquina"].unique())
    Z = {}
    for s in ["sensor_a", "sensor_b", "sensor_c", "sensor_d", "vibracao_mm_s"]:
        w = tel.pivot_table(index="data_hora", columns="id_maquina", values=s, aggfunc="mean").reindex(index=idx, columns=maquinas)
        tr = w.loc[:fim_normal]
        med = tr.median()
        mad = (tr - med).abs().median() * 1.4826
        z = ((w - med) / (mad + 1e-9)).clip(-8, 8)
        Z[s] = z.sub(z.median(axis=1), axis=0)
    return Z


def grade(man, fal, maq, maquinas, dias):
    """Uma linha por (máquina, peça, dia D) com ciclo desde a última preventiva (<= D-1), candidata (D+1 na grade) e 'cand1' (D na grade)."""
    pv = man[man["tipo"].eq("preventiva") & man["id_maquina"].isin(maquinas)].assign(dia=lambda x: x["data_hora"].dt.normalize())
    if pv.empty:
        raise ValueError("A previsão m07 requer um histórico de manutenção preventiva das máquinas com telemetria.")
    falhas = fal[fal["flag_falha_suspeita"] == 0]
    fs = set(zip(falhas["id_maquina"], falhas["peca"], falhas["data_hora"].dt.normalize()))
    info = maq.set_index("id_maquina")
    linhas = []
    for (m, p), g in pv.groupby(["id_maquina", "peca"]):
        datas = np.sort(g["dia"].values)
        D = dias.values
        i = np.searchsorted(datas, D, side="left") - 1           # última preventiva com dia <= D-1
        ok = i >= 0
        P = np.where(ok, datas[np.clip(i, 0, None)], np.datetime64("NaT"))
        linhas.append(pd.DataFrame({"id_maquina": m, "peca": p, "dia_ref": D, "P": P}))
    L = pd.concat(linhas, ignore_index=True)
    L = L[L["P"].notna()].copy()
    d1 = (L["dia_ref"] + pd.Timedelta(days=1) - L["P"]).dt.days
    d0 = (L["dia_ref"] - L["P"]).dt.days
    L["k"] = d1 // 15
    L["cand"] = (d1 % 15 == 0) & (d1 >= 15)
    L["cand1"] = (d0 % 15 == 0) & (d0 >= 15)
    L["dprev"] = d1
    L["y"] = [int((m, p, d + pd.Timedelta(days=1)) in fs) for m, p, d in zip(L["id_maquina"], L["peca"], L["dia_ref"])]
    L["y1"] = [int((m, p, d) in fs) for m, p, d in zip(L["id_maquina"], L["peca"], L["dia_ref"])]
    L["idade"] = L["id_maquina"].map(info["idade"]).astype(float)
    L["modelo"] = L["id_maquina"].map(info["modelo"].astype("category").cat.codes)
    L["linha"] = L["id_maquina"].map(info["linha_producao"].astype("category").cat.codes)
    L["mid"] = L["id_maquina"].str[1:].astype(int)
    return L.reset_index(drop=True)


# ---------------------------------------------------------------- perfis e filtros casados
def perfis(Z, L, deslocamento_h=0):
    """Perfil horário de H horas terminando em (D 05:00 + deslocamento) do sensor da peça (com sinal), mais a vibração."""
    idx = Z["sensor_a"].index
    cols = {k: i for i, k in enumerate(Z["sensor_a"].columns)}
    pos = idx.get_indexer(pd.DatetimeIndex(L["dia_ref"]) + pd.Timedelta(hours=5 + deslocamento_h))
    col = L["id_maquina"].map(cols).values
    P = np.full((len(L), H), np.nan, dtype=np.float32)
    V = np.full((len(L), H), np.nan, dtype=np.float32)
    for p, (s, sg) in SENSOR.items():
        sel = (L["peca"] == p).values
        a, v = Z[s].values * sg, Z["vibracao_mm_s"].values
        for h in range(H):
            q = pos[sel] - h
            ok = (q >= 0) & (pos[sel] >= 0) & (q < len(a))
            P[sel, h] = np.where(ok, a[np.clip(q, 0, len(a) - 1), col[sel]], np.nan)
            V[sel, h] = np.where(ok, v[np.clip(q, 0, len(a) - 1), col[sel]], np.nan)
    return P, V


def _lse(x):
    mx = x.max(axis=0, keepdims=True)
    return (mx + np.log(np.exp(x - mx).sum(axis=0, keepdims=True)))[0]


def _somas(P):
    M = ~np.isnan(P)
    cs = np.concatenate([np.zeros((len(P), 1)), np.cumsum(np.where(M, P, 0.0), 1)], 1)
    cn = np.concatenate([np.zeros((len(P), 1)), np.cumsum(M, 1)], 1)
    return cs, cn


def caixa_livre(P):
    """Melhor patamar em curso de amplitude livre: LLR, início (h atrás) e amplitude média."""
    cs, cn = _somas(P.astype(float))
    best, bs, ba = np.full(len(P), -1e9), np.zeros(len(P)), np.zeros(len(P))
    for s in range(5, H):
        S, N = cs[:, s + 1], np.maximum(cn[:, s + 1], 1)
        sc = np.where(cn[:, s + 1] >= 4, S ** 2 / N / 2, -1e9)
        u = sc > best
        best[u], bs[u], ba[u] = sc[u], s, (S / N)[u]
    return best, bs, ba


def estimar_mu(P, pecas, y):
    """Amplitude típica do patamar de falha por peça (só linhas positivas de treino com patamar em curso nítido)."""
    llr, bs, ba = caixa_livre(P)
    mu = {}
    for p in PECAS:
        s = (pecas == p) & (y == 1) & (llr > 12) & (bs >= 8) & (bs <= 60)
        mu[p] = float(np.mean(ba[s])) if s.sum() >= 20 else MU_PADRAO[p]
    return mu


def filtros_casados(P, pecas, mu, prefix="mf"):
    cs, cn = _somas(P.astype(float))
    mu_r = pecas.map(mu).values
    out = {}
    for j, r in enumerate(REL):
        a = mu_r * r
        ll = np.stack([(a * cs[:, s + 1] - cn[:, s + 1] * a * a / 2) / SIG ** 2 for s in range(3, H)])      # patamar em curso desde s
        out[f"{prefix}_ong{j}"] = _lse(ll) - np.log(ll.shape[0])
        if r in (1.0, 1.5):
            for bi, (lo, hi) in enumerate(BINS):
                out[f"{prefix}_ong{j}_b{bi}"] = _lse(ll[lo - 3:hi - 3]) - np.log(hi - lo)
        if r in (1.0, 1.5, 2.0):                                                                              # patamar já terminado
            en = [(a * (cs[:, s + 1] - cs[:, e]) - (cn[:, s + 1] - cn[:, e]) * a * a / 2) / SIG ** 2
                  for e in range(2, 40, 3) for s in range(e + 4, H, 3)]
            out[f"{prefix}_end{j}"] = _lse(np.stack(en)) - np.log(len(en))
    F = pd.DataFrame(out, index=np.arange(len(P)))
    ong = [c for c in F.columns if "_ong" in c and "_b" not in c]
    base = F[ong].values
    mx = base.max(1, keepdims=True)
    F[f"{prefix}_max"] = mx[:, 0]
    F[f"{prefix}_best"] = base.argmax(1).astype(float)
    F[f"{prefix}_amp"] = (np.exp(base - mx) * np.array(REL)).sum(1) / np.exp(base - mx).sum(1)
    for c in ong:
        F[c + "_d"] = F[c] - F[f"{prefix}_max"]
    return F


def estatisticas(P, V):
    def mm(A, k):
        with np.errstate(all="ignore"):
            return np.nanmean(A[:, :k], axis=1)
    F = pd.DataFrame({"m6": mm(P, 6), "m24": mm(P, 24), "m72": mm(P, 72), "v24": mm(V, 24)})
    with np.errstate(all="ignore"):
        F["late_early"] = np.nanmean(P[:, :6], axis=1) - np.nanmean(P[:, 36:48], axis=1)
    return F


# ---------------------------------------------------------------- detector de falha em data de grade passada
def detector(L, Z, mu, rotulados, seeds=2):
    """Prob. de falha às 06:00 de cada data de grade (linhas cand1), usando a rampa até G 05:00 e a QUEDA nas 48 h seguintes.
    Fora-da-amostra em 5 blocos de tempo nas linhas rotuladas; modelo completo nas demais. Devolve Series indexada por L."""
    c1 = L[L["cand1"]].copy()
    if c1.empty or not c1["rotulado1"].any():
        return pd.Series(0.0, index=c1.index)
    P, V = perfis(Z, c1)
    F = filtros_casados(P, c1["peca"].reset_index(drop=True), mu, "dt")
    F.index = c1.index
    S = estatisticas(P, V)
    S.index = c1.index
    A = pd.DataFrame(index=c1.index)
    for nome, (a, b) in {"aft12": (2, 13), "aft24": (2, 25), "aft48": (25, 49)}.items():   # horas depois de G 05:00
        PP = np.full((len(c1), b - a), np.nan)
        PA, _ = perfis(Z, c1, deslocamento_h=b - 1)       # janela terminando em G 05:00 + (b-1) h
        PP = PA[:, :b - a]
        with np.errstate(all="ignore"):
            A[nome] = np.nanmean(PP, axis=1)
    with np.errstate(all="ignore"):
        A["bef12"] = np.nanmean(P[:, :12], axis=1)
        A["bef36"] = np.nanmean(P[:, :36], axis=1)
    A["drop12"] = A["bef12"] - A["aft24"]
    A["drop36"] = A["bef36"] - A["aft24"]
    X = pd.concat([F, S, A], axis=1)
    X["peca_i"] = c1["peca"].map({p: i for i, p in enumerate(PECAS)}).values
    y = c1["y1"].values
    rot = c1["rotulado1"].values
    out = pd.Series(np.nan, index=c1.index)

    def fit_pred(idx_tr, idx_va):
        res = np.zeros(len(idx_va))
        for p in range(4):
            t = idx_tr[X["peca_i"].values[idx_tr] == p]
            v = np.where(X["peca_i"].values[idx_va] == p)[0]
            if len(v) == 0:
                continue
            h = np.mean([prever_binario(HistGradientBoostingClassifier(
                max_iter=200, learning_rate=0.04, max_depth=3, min_samples_leaf=30, l2_regularization=3.0, random_state=s),
                X.iloc[t], y[t], X.iloc[idx_va[v]]) for s in range(seeds)], axis=0)
            e = prever_binario(ExtraTreesClassifier(300, min_samples_leaf=2, max_features=0.4,
                class_weight="balanced_subsample", n_jobs=-1, random_state=0),
                X.iloc[t].fillna(-9), y[t], X.iloc[idx_va[v]].fillna(-9))
            res[v] = (h + e) / 2
        return res

    ir = np.where(rot)[0]
    iu = np.where(~rot)[0]
    ordem = c1["dia_ref"].values[ir].argsort()
    blocos = np.array_split(ir[ordem], 5)
    s_oof = np.zeros(len(ir))
    pos_ir = {v: i for i, v in enumerate(ir)}
    for b in blocos:
        tr = np.setdiff1d(ir, b)
        s_oof[[pos_ir[v] for v in b]] = fit_pred(tr, b)
    ap = average_precision_score(y[ir], s_oof)
    print(f"   detector de falha passada: AP fora-da-amostra = {ap:.3f}", flush=True)
    iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(s_oof, y[ir])
    out.iloc[ir] = iso.predict(s_oof)
    if len(iu):
        out.iloc[iu] = iso.predict(fit_pred(ir, iu))
    return out


def ciclos(L, pf):
    """pf_j = prob. de falha na j-ésima data de grade anterior (D+1-15j); só vale para j < k (depois da última preventiva)."""
    chave = pd.MultiIndex.from_arrays([L.loc[pf.index, "id_maquina"], L.loc[pf.index, "peca"], L.loc[pf.index, "dia_ref"]])
    S = pd.Series(pf.values, index=chave)
    S = S[~S.index.duplicated()]
    ph = {}
    for j in range(1, 7):
        i = pd.MultiIndex.from_arrays([L["id_maquina"], L["peca"], L["dia_ref"] + pd.Timedelta(days=1 - 15 * j)])
        ph[j] = S.reindex(i).values
        L[f"pf{j}"] = np.where(j < L["k"].values, ph[j], np.nan)
    k = L["k"].values
    soft = np.ones(len(L))
    kh = k.astype(float).copy()
    for j in range(6, 0, -1):
        kh = np.where((np.nan_to_num(L[f"pf{j}"].values) > 0.5) & (j < kh), j, kh)
    for j in range(1, 6):
        soft = soft * (1 - np.nan_to_num(L[f"pf{j}"].values))
    L["alive"] = soft
    L["k_eff"] = kh
    L["pf_max"] = np.nanmax(np.stack([np.nan_to_num(L[f"pf{j}"].values) for j in range(1, 6)]), axis=0)
    return L


# ---------------------------------------------------------------- modelos
def _modelo(nome, seed):
    if nome == "hgb_a":
        return HistGradientBoostingClassifier(max_iter=250, learning_rate=0.03, max_depth=2, min_samples_leaf=40, l2_regularization=5.0, max_features=0.7, random_state=seed)
    if nome == "hgb_b":
        return HistGradientBoostingClassifier(max_iter=250, learning_rate=0.03, max_depth=2, min_samples_leaf=60, l2_regularization=10.0, max_features=0.5, random_state=seed)
    if nome == "hgb_c":
        return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.02, max_depth=3, min_samples_leaf=50, l2_regularization=8.0, max_features=0.7, random_state=seed)
    if nome == "rf":
        return RandomForestClassifier(n_estimators=500, min_samples_leaf=5, max_features=0.4, class_weight="balanced_subsample", n_jobs=-1, random_state=seed)
    if nome == "et":
        return ExtraTreesClassifier(n_estimators=700, min_samples_leaf=3, max_features=0.5, criterion="entropy", class_weight="balanced_subsample", n_jobs=-1, random_state=seed)
    raise ValueError(nome)


MODELOS = [("hgb_a", 3), ("hgb_b", 3), ("hgb_c", 3), ("rf", 1), ("et", 1)]     # (modelo, nº de sementes quando --seeds 3)


def treinar_e_prever(tr, va, cols, seeds):
    """Um modelo por peça nas candidatas; devolve dict nome -> posto percentual (0..1) por linha de va (candidatas)."""
    sai = {}
    for nome, ns in MODELOS:
        s = pd.Series(np.nan, index=va.index)
        n = max(1, round(ns * seeds / 3))
        fill = nome in ("rf", "et")
        for p in PECAS:
            t, v = tr[tr["peca"] == p], va[va["peca"] == p]
            if len(v) == 0:
                continue
            Xt, Xv = (t[cols].fillna(-9), v[cols].fillna(-9)) if fill else (t[cols], v[cols])
            s.loc[v.index] = np.mean([prever_binario(_modelo(nome, sd), Xt, t["y"], Xv) for sd in range(n)], axis=0)
        sai[nome] = s
    return sai


def fundir(listas, va, k=30):
    z = sum(1.0 / (k + s.groupby(va["peca"]).rank(ascending=False, method="average")) for s in listas.values())
    return z


# ---------------------------------------------------------------- pipeline completo
def construir(dados, treino_ate, fim_normal=FIM_NORMAL, *, periodo=None, rotulos=None):
    """Monta todas as variáveis. Rótulos só valem para D < treino_ate (e <= 29/09); o restante é tratado como não rotulado."""
    tel, man, fal, maq = carregar(dados)
    Z = z_telemetria(tel, fim_normal)
    maquinas = sorted(tel["id_maquina"].unique())
    dias = periodo if periodo is not None else pd.date_range("2022-10-03", "2024-01-01")
    L = grade(man, fal, maq, maquinas, dias)
    L["rotulado"] = (L["dia_ref"] < treino_ate) & (L["dia_ref"] <= ULTIMO_ROTULO) & ~L["dia_ref"].isin(INCERTOS)
    L["rotulado1"] = (L["dia_ref"] < treino_ate) & (L["dia_ref"] <= ULTIMO_ROTULO) & ~L["dia_ref"].isin(INCERTOS + [d + pd.Timedelta(days=1) for d in INCERTOS])
    if rotulos is not None:
        chave = L[["id_maquina", "dia_ref", "peca"]]
        y = rotulos.reindex(pd.MultiIndex.from_frame(chave)).to_numpy()
        ontem = chave.assign(dia_ref=chave["dia_ref"] - pd.Timedelta(days=1))
        y1 = rotulos.reindex(pd.MultiIndex.from_frame(ontem)).to_numpy()
        L["rotulado"] = pd.notna(y)
        L["rotulado1"] = pd.notna(y1) & (L["dia_ref"] + pd.Timedelta(days=2) < treino_ate)
        L["y"] = pd.Series(y).fillna(0).astype(int).to_numpy()
        L["y1"] = pd.Series(y1).fillna(0).astype(int).to_numpy()
    L.loc[~L["rotulado"], "y"] = 0
    C = L[L["cand"]].copy()
    P, V = perfis(Z, C)
    mu = estimar_mu(P, C["peca"].values, C["y"].values * C["rotulado"].values)
    mu = {k: v * MU_ESCALA for k, v in mu.items()}
    print("amplitude típica de falha por peça:", {k: round(v, 2) for k, v in mu.items()}, flush=True)
    F = filtros_casados(P, C["peca"].reset_index(drop=True), mu)
    F.index = C.index
    S = estatisticas(P, V)
    S.index = C.index
    C = pd.concat([C, F, S], axis=1)
    pf = detector(L, Z, mu, L["rotulado1"])
    L = ciclos(L, pf)
    cic = ["pf1", "pf2", "pf3", "pf4", "pf5", "alive", "k_eff", "pf_max"]
    C = C.drop(columns=[c for c in C.columns if c in cic]).join(L.loc[C.index, cic])
    cols = list(F.columns) + ["k", "dprev", "idade", "modelo", "linha", "m6", "m24", "m72", "v24", "late_early"] + cic
    cols = [c for c in cols if c not in DROP_COLS]
    return C, cols, mu


def prever(C, cols, previsao, seeds, gate=GATE):
    """Treina nas candidatas rotuladas (fora do filtro) e devolve a pontuação por linha de 'previsao' (candidatas)."""
    tr = C[C["rotulado"] & (C["pf1"].fillna(0) < gate)]
    va = previsao[previsao["pf1"].fillna(0) < gate].copy()
    listas = treinar_e_prever(tr, va, cols, seeds)
    z = fundir(listas, va)
    z = normalizar(z)
    out = pd.Series(1e-4, index=previsao.index)         # candidatas com falha anterior inferida: rebaixadas
    out.loc[z.index] = 1e-3 + 0.999 * z
    return out, listas


def ap_por_peca(L, score):
    return float(np.mean([average_precision_score(L.loc[L["peca"] == p, "y"], score[L["peca"] == p]) for p in PECAS]))


def validar(dados, seeds):
    res = []
    for a, z in JANELAS:
        C, cols, _ = construir(dados, pd.Timestamp(a))
        va = C[(C["dia_ref"] >= pd.Timestamp(a)) & (C["dia_ref"] <= pd.Timestamp(z)) & ~C["dia_ref"].isin(INCERTOS)]
        sc, listas = prever(C, cols, va, seeds)
        tudo = construir_linhas_janela(dados, a, z)
        k = pd.MultiIndex.from_arrays([tudo["id_maquina"], tudo["peca"], tudo["dia_ref"]])

        def alinhar(v):   # AP sobre TODAS as linhas da janela: não candidatas = pontuação mínima; positivos fora da grade contam como erro
            m = pd.Series(v.values, index=pd.MultiIndex.from_arrays([va.loc[v.index, "id_maquina"], va.loc[v.index, "peca"], va.loc[v.index, "dia_ref"]]))
            return pd.Series(m.reindex(k).fillna(1e-5).values, index=tudo.index)
        res.append(ap_por_peca(tudo, alinhar(sc)))
        print(f"janela {a}..{z}: AP (média das 4 peças) = {res[-1]:.4f}", flush=True)
        for n, v in listas.items():
            print(f"      {n:6s} AP = {ap_por_peca(tudo, alinhar(v)):.4f}", flush=True)
    print(f"AP médio das 3 janelas = {np.mean(res):.4f}")
    return res


_CACHE = {}


def construir_linhas_janela(dados, a, z):
    """Todas as linhas (máquina, peça, dia) da janela com o rótulo verdadeiro (para o AP incluir os positivos fora da grade)."""
    if "base" not in _CACHE:
        tel, man, fal, maq = carregar(dados)
        maquinas = sorted(tel["id_maquina"].unique())
        fs = fal[fal["flag_falha_suspeita"] == 0]
        fs = set(zip(fs["id_maquina"], fs["peca"], fs["data_hora"].dt.normalize()))
        dias = pd.date_range("2022-10-03", "2023-09-29")
        T = pd.MultiIndex.from_product([maquinas, PECAS, dias], names=["id_maquina", "peca", "dia_ref"]).to_frame(index=False)
        T["y"] = [int((m, p, d + pd.Timedelta(days=1)) in fs) for m, p, d in zip(T["id_maquina"], T["peca"], T["dia_ref"])]
        _CACHE["base"] = T[~T["dia_ref"].isin(INCERTOS)]
    T = _CACHE["base"]
    return T[(T["dia_ref"] >= pd.Timestamp(a)) & (T["dia_ref"] <= pd.Timestamp(z))].reset_index(drop=True)


def gerar_submissao(dados, saida, seeds, *, periodo=None, rotulos=None):
    C, cols, mu = construir(dados, INICIO_TESTE, FIM_NORMAL, periodo=periodo, rotulos=rotulos)
    teste = C[C["dia_ref"].between(INICIO_TESTE, INICIO_TESTE + pd.Timedelta(days=DIAS_TESTE - 1))].copy()
    print("candidatas no treino:", int(C["rotulado"].sum()), "| positivos:", int(C.loc[C["rotulado"], "y"].sum()),
          "| candidatas no teste:", len(teste), flush=True)
    sc, listas = prever(C, cols, teste, seeds)
    tel, *_ = carregar(dados)
    maquinas = sorted(tel["id_maquina"].unique())
    dias = pd.date_range(INICIO_TESTE, periods=DIAS_TESTE)
    T = pd.MultiIndex.from_product([maquinas, dias], names=["id_maquina", "dia_ref"]).to_frame(index=False)
    for p in PECAS:
        m = pd.Series(sc.values, index=pd.MultiIndex.from_arrays([teste["id_maquina"], teste["peca"], teste["dia_ref"]]))
        T[p] = m.reindex(pd.MultiIndex.from_arrays([T["id_maquina"], [p] * len(T), T["dia_ref"]])).fillna(1e-5).values
    T["id"] = T["id_maquina"] + "_" + T["dia_ref"].dt.strftime("%Y-%m-%d")
    sub = T[["id"] + PECAS].round(6)
    assert sub[PECAS].notna().all().all() and sub[PECAS].min().min() >= 0 and sub[PECAS].max().max() <= 1
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    sub.to_csv(saida / "submissao.csv", index=False)
    (saida / "manifesto.json").write_text(json.dumps({"python": platform.python_version(), "pandas": pd.__version__,
                                                       "numpy": np.__version__, "seeds": seeds, "mu": mu}, indent=2))
    print("salvo", saida / "submissao.csv", sub.shape)
    return sub


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", required=True)
    ap.add_argument("--saida", default="saidas_v2")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--validar", action="store_true")
    a = ap.parse_args()
    if a.validar:
        validar(a.dados, a.seeds)
    else:
        gerar_submissao(a.dados, a.saida, a.seeds)
