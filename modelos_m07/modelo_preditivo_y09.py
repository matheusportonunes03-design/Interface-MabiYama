r"""MaBiYama - modelo preditivo de falha por peça (máquina x dia) - SUBMISSÃO y09 (Kaggle 0,69204), INDEPENDENTE.

Treina tudo do zero a partir dos CSVs de dados tratados; não lê nenhuma submissão anterior. A y09 é a fusão "3 melhores posições"
(média dos 3 maiores 1/(30 + posição) entre as listas; posição 1 = mais provável, por peça) de 6 listas, cada uma a fusão RRF
(k=30, peso 1 salvo indicação) de listas de modelos:

  sub 41  v05(peso 2) + v06 + v07 + v15 + v21 + v28 + v30                         (receita do script das subs 41/43)
  sub 43  v05 + v06 + N1..N5 + v15 + v21 + v28 + v30        (sem o blend v07)     (receita do script das subs 41/43)
  sub 42  v05 + v06 + v07 + v15 + v21 + v28 + v30 + N1..N7  (14 listas)           (receita do script da sub 42)
  sub 44  v05 + v06 + v15 + v21 + v28 + v30                 (sub 37 sem o v07)
  sub 40  v05 + v06 + v07 + v15(peso 2) + v21 + v28 + v30(peso 2)
  p06     v05 + v06 + v07 + v15 + v21 + v28 + v30 + v31 + v32 + v33, listas 'hat' com filtro pf1_hat >= 0,7

  v05 HGB lento por peça | v06 ExtraTrees por peça | v07 blend por rank de 9 modelos antigos
  N1-N3 HGB e N4-N5 ET gini (outros hiperparâmetros) | N6 Random Forest | N7 GradientBoosting do sklearn
  v15 ET "hat" 700 árvores | v21 idem 1500 | v28 + id da máquina | v30 + fornecedor, firmware, operação, clima | v31-v33 extras do p06

Origem das receitas: subs 41, 42 e 43 e os modelos N1..N7 vêm dos scripts dessas subs; as subs 40 e 44 vêm da descrição
(40 = peso 2 em v15 e v30; 44 = sub 37 sem o v07); o p06 vem do script de presets (preset p06).

Regra de ouro: toda variável da linha D usa só dados com timestamp <= D 05:00.

Uso:  python modelos\modelo_preditivo_y09.py [--seeds 3] [--referencia <tabela enviada.csv>] [--conferir <pasta com as subs originais>]
Saídas em saidas\y09_pipeline\: y09.csv, p06.csv, sub37/40/41/42/43/44_reconstruida.csv, lista_*.csv, gate_pf1.csv, manifesto.json.
"""
import argparse
import hashlib
import json
import platform
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from comum_modelo import normalizar, prever_binario
from sklearn.ensemble import (ExtraTreesClassifier, GradientBoostingClassifier, HistGradientBoostingClassifier,
                              RandomForestClassifier)
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score

warnings.filterwarnings("ignore")

PECAS = ["peca_A", "peca_B", "peca_C", "peca_D"]
SENS = ["sensor_a", "sensor_b", "sensor_c", "sensor_d", "vibracao_mm_s"]
SENSOR_DA_PECA = {"peca_A": ("sensor_c", 1), "peca_B": ("sensor_d", 1), "peca_C": ("sensor_b", -1), "peca_D": ("sensor_a", 1)}
ERROS_DA_PECA = {"peca_A": ["erro_E1"], "peca_B": ["erro_E5"], "peca_C": ["erro_E2", "erro_E3"], "peca_D": ["erro_E4"]}
CORTE_H = 5
INICIO_TESTE = pd.Timestamp("2023-09-30")
DIAS_TESTE = 92
FIM_NORMAL = pd.Timestamp("2023-09-30 05:00")      # o "normal" de cada máquina usa só o período de treino
FASE_CAND = 13.958                                  # dias_desde_prev quando D+1 é dia da grade de 15 dias
FASE_CAND1 = 14.9583                                # idem quando o PRÓPRIO dia D é dia de grade (falha às 06:00 de D)
NB, B = 16, 6                                       # blocos de 6 h x 16 = 96 h
JANELAS = [("2022-12-31", "2023-03-30"), ("2023-03-31", "2023-06-29"), ("2023-06-30", "2023-09-29")]
EXP = {"cm", "ex"}                                  # sempre ligados (modo comum removido + variáveis de excedência)
SEEDS = 3
K_RRF = 30
# ---- configuração por preset (--preset pXX); padrão = sub 37 ----
CFG = {"hgb_lr": 0.015, "hgb_iter": 500, "hgb_leaf": 40, "hgb_l2": 5.0, "hgb_mf": 0.5,
       "et_leaf": 1, "et_mf": 0.4, "et_crit": "entropy", "gate": 0.5,
       "hat_extra": [], "pesos": {}, "agg": "rrf", "geo_k": 0, "seeds": None, "k": None}
HX = [("v31", "et_hat_n700", "FS2+EX"), ("v32", "et_hat_n700", "FS2nd+EX+mid"), ("v33", "et_hat_n700", "FS2+EX+mid+prof")]
PRESETS = {
 "p00": {},
 "p01": {"hgb_lr": 0.01, "hgb_iter": 800, "pesos": {"v05": 2}},
 "p02": {"hgb_leaf": 60, "hgb_l2": 8.0, "hgb_mf": 0.3, "pesos": {"v05": 2}},
 "p03": {"et_leaf": 2, "et_mf": 0.3},
 "p04": {"et_crit": "gini", "hat_extra": HX[:1]},
 "p05": {"gate": 0.3},
 "p06": {"gate": 0.7, "hat_extra": HX},
 "p07": {"hat_extra": HX, "pesos": {"v31": 2, "v32": 2, "v33": 2}, "k": 10},
 "p08": {"hgb_lr": 0.01, "hgb_iter": 800, "et_leaf": 2, "et_mf": 0.3, "hat_extra": HX, "pesos": {"v05": 2, "v33": 2},
         "agg": "geo", "seeds": 5},
 "p09": {"hgb_leaf": 60, "hgb_l2": 8.0, "et_crit": "gini", "gate": 0.3, "hat_extra": HX[1:], "pesos": {"v05": 2, "v21": 2}, "agg": "geo"},
}

NEWS = ["adapt_m24", "adapt_m12", "last1", "m2", "max6", "min6", "sd72", "n_valid24", "ewm6", "ewm18", "ewm_gap",
        "vib_m6", "vib_m24", "vib_m72"]
HATF = ["pf1_hat", "pf2_hat", "pf3_hat", "kany_hat", "alive_soft", "pf_max_hat"]
DROPF = [f"{a}_{j}" for j in (1, 2, 3) for a in ("drop", "drop36", "bef12", "bef36")]
EX = ["fornecedor_peca_atual_c", "versao_firmware_c", "op_utilizacao_pct_media", "op_consumo_energia_kwh", "op_hora_extra",
      "op_taxa_defeito", "op_pct_meta", "op_qtd_operadores_media", "op_tempo_setup_min", "op_n_turnos",
      "temp_ambiente_c_media", "umidade_relativa_media"]


# ------------------------------------------------------------------ telemetria horária
def _wide(tel_path):
    t = pd.read_csv(tel_path, parse_dates=["data_hora"], usecols=["id_maquina", "data_hora"] + SENS)
    idx = pd.date_range(t["data_hora"].min(), t["data_hora"].max(), freq="h")
    maquinas = sorted(t["id_maquina"].unique())
    return {s: t.pivot_table(index="data_hora", columns="id_maquina", values=s, aggfunc="mean")
            .reindex(index=idx, columns=maquinas) for s in SENS}


def _z(w):
    tr = w.loc[:FIM_NORMAL]
    med = tr.median()
    mad = (tr - med).abs().median() * 1.4826
    z = ((w - med) / (mad + 1e-9)).clip(-8, 8)
    if "cm" in EXP:                                   # modo comum da frota na mesma hora (só presente/passado)
        z = z.sub(z.median(axis=1), axis=0)
    return z


def _rolling(z):
    """Janelas terminando em cada hora (a linha do dia D lê a hora D 05:00)."""
    out = {}
    m = z.notna().astype(float)
    y = z.fillna(0.0)
    x = pd.DataFrame(np.repeat(np.arange(len(z))[:, None], z.shape[1], 1), index=z.index, columns=z.columns).astype(float)
    for k in (3, 6, 12, 24, 48, 72):
        out[f"m{k}"] = z.rolling(k, min_periods=max(2, k // 3)).mean()
    out["max24"] = z.rolling(24, min_periods=8).max()
    out["min24"] = z.rolling(24, min_periods=8).min()
    out["sd24"] = z.rolling(24, min_periods=8).std()
    for k in (48, 72):
        S1, Sx, Sxx = m.rolling(k).sum(), (m * x).rolling(k).sum(), (m * x * x).rolling(k).sum()
        Sy, Sxy = y.rolling(k).sum(), (y * x).rolling(k).sum()
        den = S1 * Sxx - Sx ** 2
        sl = (S1 * Sxy - Sx * Sy) / den.where(den > 1e-6)
        out[f"slope{k}"] = sl.where(S1 >= k / 3) * 24
    out["gap"] = out["m12"] - out["m72"]
    if "ex" in EXP:
        out["max48"] = z.rolling(48, min_periods=16).max()
        out["max72"] = z.rolling(72, min_periods=24).max()
        out["frac24"] = (z > 1.5).astype(float).where(z.notna()).rolling(24, min_periods=8).mean()
        out["frac48"] = (z > 1.0).astype(float).where(z.notna()).rolling(48, min_periods=16).mean()
    return out


def feats_telemetria(tel_path, dias):
    W = _wide(tel_path)
    Z = {s: _z(w) for s, w in W.items()}
    idx = Z["sensor_a"].index
    ts = pd.DatetimeIndex([d + pd.Timedelta(hours=CORTE_H) for d in dias])
    pos = idx.get_indexer(ts)
    maqs = list(Z["sensor_a"].columns)

    def amostra(frame):
        a = frame.values[pos[pos >= 0]]
        full = np.full((len(dias), len(maqs)), np.nan)
        full[pos >= 0] = a
        return full.reshape(-1)           # ordem (dia, máquina)

    base = pd.DataFrame({"dia_ref": np.repeat(dias.values, len(maqs)), "id_maquina": np.tile(maqs, len(dias))})
    for s in SENS:
        base[f"ctx_{s}"] = amostra(Z[s].rolling(24, min_periods=8).mean())
    R = {}
    for p, (s, sg) in SENSOR_DA_PECA.items():
        zz = Z[s] * sg
        R[p] = _rolling(zz)
        for nome, fr in R[p].items():
            base[f"{p}|own_{nome}"] = amostra(fr)
        blocos = np.full((len(dias), len(maqs), NB), np.nan)
        a = zz.values
        for j in range(NB):
            amostras = pos[None, :] - (B * j + np.arange(B))[:, None]
            leituras = a[np.maximum(amostras, 0), :]
            leituras[amostras < 0] = np.nan
            v = np.nanmean(leituras, axis=0)
            v[pos < 0] = np.nan
            blocos[:, :, j] = v
        for j in range(NB):
            base[f"{p}|blk{j}"] = blocos[:, :, j].reshape(-1)
    if "ex" in EXP:                                    # sensor da peça contra os sensores das outras peças
        for p in PECAS:
            oth = sum(R[q]["m24"] for q in PECAS if q != p) / (len(PECAS) - 1)
            base[f"{p}|own_oth24"] = amostra(oth)
            base[f"{p}|own_vs_oth"] = amostra(R[p]["m24"] - oth)
    base["dia_ref"] = pd.to_datetime(base["dia_ref"])
    return base


# ------------------------------------------------------------------ erros, falhas, base
def feats_erros(err_path, maquinas, dias=None):
    e = pd.read_csv(err_path, parse_dates=["data_hora"])
    e["dia"] = e["data_hora"].dt.normalize()
    ep = e[e["flag_horario_pico"] == 1].groupby(["id_maquina", "dia", "codigo_erro"]).size().unstack(fill_value=0)
    if dias is None:
        dias = pd.date_range("2022-09-25", "2024-01-02")
    full = pd.MultiIndex.from_product([maquinas, dias], names=["id_maquina", "dia"])
    return ep.reindex(full, fill_value=0)


def alvo_falhas(falhas_path):
    f = pd.read_csv(falhas_path, parse_dates=["data_hora"])
    f = f[f["flag_falha_suspeita"] == 0]
    return set(zip(f["id_maquina"], f["peca"], f["data_hora"].dt.normalize()))


def montar(base_path, tel_path, err_path, falhas_path, periodo=None):
    base = pd.read_csv(base_path, encoding="utf-8-sig", parse_dates=["dia_ref"])
    maquinas = sorted(base["id_maquina"].unique())
    dias = periodo if periodo is not None else pd.date_range("2022-10-03", "2024-01-01")
    tel = feats_telemetria(tel_path, dias)
    cols = ["id_maquina", "dia_ref", "modelo", "linha_producao", "idade_anos", "n_erros"] + \
           [f"n_erro_E{i}" for i in range(1, 6)] + [f"dias_desde_prev_peca_{p}" for p in "ABCD"]
    d = tel.merge(base[cols], on=["id_maquina", "dia_ref"], how="left")
    d["modelo"] = d["modelo"].astype("category").cat.codes
    d["linha_producao"] = d["linha_producao"].astype("category").cat.codes
    ep = feats_erros(err_path, maquinas, pd.date_range(dias.min() - pd.Timedelta(days=3), dias.max()))
    fs = alvo_falhas(falhas_path)
    partes = []
    for i, p in enumerate(PECAS):
        x = d[["id_maquina", "dia_ref", "modelo", "linha_producao", "idade_anos", "n_erros"]].copy()
        for c in [c for c in d.columns if c.startswith(p + "|")]:
            x[c.split("|")[1]] = d[c]
        for s in SENS:
            x[f"ctx_{s}"] = d[f"ctx_{s}"]
        x["ramp_diff"] = x["blk0"] - x["blk4"]
        x["ramp_diff2"] = x["blk0"] - x["blk8"]
        x["dprev"] = d[f"dias_desde_prev_{p}"]
        x["k"] = np.round((x["dprev"] + 1 / 24) / 15)
        x["k1"] = (x["k"] == 1).astype(int)
        x["cand"] = ((x["dprev"] % 15) - FASE_CAND).abs() < 0.01
        for lag in (1, 2, 3):
            sub = ep.reindex(pd.MultiIndex.from_arrays([x["id_maquina"], x["dia_ref"] - pd.Timedelta(days=lag)]))
            x[f"pico_own_l{lag}"] = sub.reindex(columns=ERROS_DA_PECA[p]).sum(axis=1).values
            x[f"pico_all_l{lag}"] = sub.sum(axis=1).values
        x["n_own_codes"] = d[[c.replace("erro_", "n_erro_") for c in ERROS_DA_PECA[p]]].sum(axis=1)
        x["y"] = [int((m, p, dd + pd.Timedelta(days=1)) in fs) for m, dd in zip(x["id_maquina"], x["dia_ref"])]
        x["peca"], x["peca_i"] = p, i
        for j in range(len(PECAS)):                    # dummies só para a regressão logística agrupada
            x[f"pi{j}"] = int(i == j)
        partes.append(x)
    L = pd.concat(partes, ignore_index=True)
    L["y_known"] = L["dia_ref"] <= pd.Timestamp("2023-09-29")        # D+1 06:00 <= 30/09 06:00: último lançamento conhecido
    L["incerto"] = L["dia_ref"].isin([pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")])  # lote suspeito de 02/01 03:00
    return L


def colunas(L):
    own = [c for c in L.columns if c.startswith("own_")]
    ctx = [c for c in L.columns if c.startswith("ctx_")]
    blk = [f"blk{j}" for j in range(NB)] + ["ramp_diff", "ramp_diff2"]
    pico = [c for c in L.columns if c.startswith("pico_")]
    stat = ["idade_anos", "modelo", "linha_producao", "n_own_codes", "n_erros", "k", "k1"]
    return own + ctx + blk + pico + stat




# ------------------------------------------------------------------ variáveis novas (só linhas candidatas)
def _normalizados(tel_path):
    return {s: _z(w) for s, w in _wide(tel_path).items()}


def feats_perfil(Z, L):
    """Perfil horário das últimas 96 h do sensor da peça (prof0 = hora D 05:00), baseline adaptativo de 30 dias, vibração,
    médias exponenciais e janelas curtas. Só para linhas candidatas (D+1 na grade) e 'cand1' (D na grade)."""
    C = L.loc[L["cand"] | L["cand1"], ["id_maquina", "dia_ref", "peca"]]
    idx = Z["sensor_a"].index
    mc = {k: i for i, k in enumerate(Z["sensor_a"].columns)}
    pos = idx.get_indexer(pd.DatetimeIndex(C["dia_ref"]) + pd.Timedelta(hours=CORTE_H))
    col = C["id_maquina"].map(mc).values
    ok = pos >= 0

    def samp(fr):
        out = np.full(len(C), np.nan)
        out[ok] = fr.values[pos[ok], col[ok]]
        return out

    prof = np.full((len(C), 96), np.nan, dtype=np.float32)
    partes = []
    for p, (s, sg) in SENSOR_DA_PECA.items():
        sel = (C["peca"] == p).values
        zz = Z[s] * sg
        a = zz.values
        ps, cs, okk = pos[sel], col[sel], ok[sel]
        P = np.full((sel.sum(), 96), np.nan, dtype=np.float32)
        for h in range(96):
            q = ps - h
            P[:, h] = np.where((q >= 0) & okk, a[np.clip(q, 0, None), cs], np.nan)
        prof[sel] = P
        base = zz.shift(72).rolling(720, min_periods=240).median()
        m24 = zz.rolling(24, min_periods=8).mean()
        f = pd.DataFrame(index=C.index[sel])
        f["adapt_m24"] = samp(m24 - base)[sel]
        f["adapt_m12"] = samp(zz.rolling(12, min_periods=4).mean() - base)[sel]
        f["last1"] = samp(zz)[sel]
        f["m2"] = samp(zz.rolling(2, min_periods=1).mean())[sel]
        f["max6"] = samp(zz.rolling(6, min_periods=2).max())[sel]
        f["min6"] = samp(zz.rolling(6, min_periods=2).min())[sel]
        f["sd72"] = samp(zz.rolling(72, min_periods=24).std())[sel]
        f["n_valid24"] = samp(zz.notna().astype(float).rolling(24).sum())[sel]
        f["ewm6"] = samp(zz.ewm(halflife=6, min_periods=4).mean())[sel]
        f["ewm18"] = samp(zz.ewm(halflife=18, min_periods=8).mean())[sel]
        f["ewm_gap"] = f["ewm6"] - f["ewm18"]
        zv = Z["vibracao_mm_s"]
        f["vib_m6"] = samp(zv.rolling(6, min_periods=2).mean())[sel]
        f["vib_m24"] = samp(zv.rolling(24, min_periods=8).mean())[sel]
        f["vib_m72"] = samp(zv.rolling(72, min_periods=24).mean())[sel]
        partes.append(f)
    F = pd.concat(partes).loc[C.index]
    for h in range(96):
        F[f"prof{h}"] = prof[:, h]
    return F


def derivar_forma(F):
    """Forma da rampa a partir do perfil de 96 h: segmentos, subida, duração acima de limiar e casamento com rampas-modelo."""
    P = F[[f"prof{h}" for h in range(96)]].values.astype(float)
    out = {}

    def media(a, b):
        with np.errstate(all="ignore"):
            return np.nanmean(P[:, a:b], axis=1)

    for a, b in [(0, 6), (6, 12), (12, 24), (24, 36), (36, 48), (48, 60), (60, 72), (72, 96)]:
        out[f"seg_{a}_{b}"] = media(a, b)
    out["late_early"] = out["seg_0_6"] - out["seg_36_48"]
    out["early_amp"] = np.nanmax(np.stack([out["seg_36_48"], out["seg_48_60"], out["seg_60_72"]]), axis=0)
    out["rise_12_36"] = media(0, 12) - media(24, 36)
    out["rise_6_24"] = media(0, 6) - media(12, 24)
    S = np.stack([np.nanmean(P[:, h:h + 6], axis=1) for h in range(0, 91)], axis=1)
    for thr in (0.3, 0.6):
        run, alive = np.zeros(len(P)), np.ones(len(P), bool)
        for h in range(S.shape[1]):
            alive &= (S[:, h] > thr) | np.isnan(S[:, h])
            run += alive
        out[f"run_{thr}"] = run
    out["above_0.5_24"] = np.nanmean(P[:, :24] > 0.5, axis=1)
    out["above_0.5_48"] = np.nanmean(P[:, :48] > 0.5, axis=1)
    out["above_1_12"] = np.nanmean(P[:, :12] > 1, axis=1)
    Pf = np.where(np.isnan(P), 0, P)
    t36, t60 = np.clip(1 - np.arange(96) / 36, 0, None), np.clip(1 - np.arange(96) / 60, 0, None)
    out["tmpl36"] = Pf @ t36 / (np.linalg.norm(t36) + 1e-9)
    out["tmpl60"] = Pf @ t60 / (np.linalg.norm(t60) + 1e-9)
    out["excess_early"] = out["tmpl60"] - out["tmpl36"]
    return pd.DataFrame(out, index=F.index)


def feats_ciclos(Z, L, nj=6):
    """Rampa ANTES e queda DEPOIS de cada data de grade passada (G_j = D+1-15j dias, 06:00): sinal de troca por falha."""
    C = L.loc[L["cand"], ["id_maquina", "dia_ref", "peca"]]
    idx = Z["sensor_a"].index
    mc = {k: i for i, k in enumerate(Z["sensor_a"].columns)}
    pos = idx.get_indexer(pd.DatetimeIndex(C["dia_ref"]) + pd.Timedelta(hours=CORTE_H))
    col = C["id_maquina"].map(mc).values
    out = {}
    for p, (s, sg) in SENSOR_DA_PECA.items():
        sel = (C["peca"] == p).values
        a = (Z[s] * sg).values
        ps, cs = pos[sel], col[sel]
        cs_ = np.nan_to_num(np.cumsum(np.nan_to_num(a), axis=0))
        cn = np.cumsum(~np.isnan(a), axis=0)

        def wmean(c, lo, hi):                          # média sobre as posições (lo, hi] por linha, via somas cumulativas
            lo = np.clip(lo, -1, None)
            okk = (hi >= 0) & (lo >= -1) & (hi < len(a))
            h, l = np.clip(hi, 0, len(a) - 1), np.clip(lo, 0, len(a) - 1)
            s1 = cs_[h, c] - np.where(lo >= 0, cs_[l, c], 0)
            n1 = cn[h, c] - np.where(lo >= 0, cn[l, c], 0)
            return np.where(okk & (n1 >= 4), s1 / np.maximum(n1, 1), np.nan)

        for j in range(1, nj + 1):
            g = ps - 335 - 360 * (j - 1)
            for nome, (lo, hi) in {"bef36": (-36, -1), "bef12": (-12, -1), "aft24": (1, 24), "aft48": (25, 48)}.items():
                out.setdefault(f"{nome}_{j}", np.full(len(C), np.nan))[sel] = wmean(cs, g + lo, g + hi)
    F = pd.DataFrame(out, index=C.index)
    for j in range(1, nj + 1):
        F[f"drop_{j}"] = F[f"bef12_{j}"] - F[f"aft24_{j}"]
        F[f"drop36_{j}"] = F[f"bef36_{j}"] - F[f"aft24_{j}"]
    return F


# ------------------------------------------------------------------ modelos
def _modelo(nome, seed=0):
    if nome == "hgb_d3":
        return HistGradientBoostingClassifier(max_iter=200, learning_rate=0.04, max_depth=3, min_samples_leaf=30,
                                              l2_regularization=3.0, random_state=seed)
    if nome == "hgb_d2":
        return HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=2, min_samples_leaf=25,
                                              l2_regularization=1.0, random_state=seed)
    if nome == "hgb_d1":
        return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_depth=1, min_samples_leaf=30,
                                              l2_regularization=2.0, random_state=seed)
    if nome == "hgb_slow":
        return HistGradientBoostingClassifier(max_iter=CFG["hgb_iter"], learning_rate=CFG["hgb_lr"], max_depth=3,
                                              min_samples_leaf=CFG["hgb_leaf"], l2_regularization=CFG["hgb_l2"],
                                              max_features=CFG["hgb_mf"], random_state=seed)
    if nome == "et":                                   # ET do modelo base
        return ExtraTreesClassifier(n_estimators=500, min_samples_leaf=5, max_features=0.5, n_jobs=-1, random_state=seed)
    if nome.startswith("et_hat"):                      # ET entropia, folha 1, mf 0,4, peso balanceado (n árvores no nome)
        n = int(nome.split("_n")[1])
        return ExtraTreesClassifier(n_estimators=n, min_samples_leaf=CFG["et_leaf"], max_features=CFG["et_mf"],
                                    criterion=CFG["et_crit"], class_weight="balanced_subsample", n_jobs=-1, random_state=seed)
    if nome == "et_det":                               # ET do detector de falha anterior
        return ExtraTreesClassifier(n_estimators=400, min_samples_leaf=2, max_features=0.4, criterion="entropy",
                                    class_weight="balanced_subsample", n_jobs=-1, random_state=seed)
    if nome == "hgb_n1":                                # ---- modelos "novos" (sub 42/43); N1-N5 copiados do script das subs 41/43
        return HistGradientBoostingClassifier(max_iter=500, learning_rate=0.02, max_depth=3, min_samples_leaf=40,
                                              l2_regularization=5.0, max_features=0.3, random_state=seed)
    if nome == "hgb_n2":
        return HistGradientBoostingClassifier(max_iter=400, learning_rate=0.03, max_depth=2, min_samples_leaf=25,
                                              l2_regularization=3.0, max_features=0.5, random_state=seed)
    if nome == "hgb_n3":
        return HistGradientBoostingClassifier(max_iter=600, learning_rate=0.01, max_depth=4, min_samples_leaf=60,
                                              l2_regularization=10.0, max_features=0.4, random_state=seed)
    if nome == "et_n4":
        return ExtraTreesClassifier(n_estimators=700, min_samples_leaf=3, max_features=0.3, criterion="gini", n_jobs=-1, random_state=seed)
    if nome == "et_n5":
        return ExtraTreesClassifier(n_estimators=700, min_samples_leaf=8, max_features=0.7, criterion="gini", n_jobs=-1, random_state=seed)
    if nome == "rf_n6":
        return RandomForestClassifier(n_estimators=300, min_samples_leaf=8, max_features=0.3, max_samples=0.7, n_jobs=-1, random_state=seed)
    if nome == "gbc_n7":
        return GradientBoostingClassifier(n_estimators=300, learning_rate=0.03, max_depth=2, subsample=0.7, min_samples_leaf=20,
                                          max_features=0.5, random_state=seed)
    raise ValueError(nome)


def _usa_fill(nome):
    return nome == "et" or nome.startswith(("et_", "rf_", "gbc_"))


def _logit(x):
    x = np.clip(x, 1e-6, 1 - 1e-6)
    return np.log(x / (1 - x))


def taxa_maquina_peca(tr, va, a=20):
    """Taxa suavizada de falha por (máquina, peça). No treino usa blocos temporais fora-do-bloco (sem olhar o próprio rótulo)."""
    if tr.empty:
        return np.empty(0), np.zeros(len(va))
    prior = tr["y"].mean()
    g = tr.groupby(["id_maquina", "peca"])["y"]
    s, n = g.sum(), g.count()
    key = lambda d: pd.MultiIndex.from_arrays([d["id_maquina"], d["peca"]])
    va_te = (s.reindex(key(va), fill_value=0).values + a * prior) / (n.reindex(key(va), fill_value=0).values + a)
    blk = np.arange(len(tr)) * 5 // len(tr) if len(tr) < 5 else pd.qcut(tr["dia_ref"].rank(method="first"), 5, labels=False)
    te = np.zeros(len(tr))
    for b in range(5):
        o, i = tr[blk != b], np.asarray(blk == b)
        go = o.groupby(["id_maquina", "peca"])["y"]
        so, no = go.sum(), go.count()
        k = key(tr[i])
        te[i] = (so.reindex(k, fill_value=0).values + a * prior) / (no.reindex(k, fill_value=0).values + a)
    return te, va_te


def treinar(tr, va, tipo, mdl, F, seeds):
    """Treina em tr[cand] e prevê va[cand]. tipo='peca': um modelo por peça; 'pool': um modelo para as 4 peças.
    Devolve o logit da probabilidade (média de 'seeds' sementes) indexado pelas linhas candidatas de va."""
    tr, va = tr[tr["cand"]].copy(), va[va["cand"]].copy()
    tr["te_mp"], va["te_mp"] = taxa_maquina_peca(tr, va)
    FF = F + ["te_mp"]
    fill = (lambda d: d.fillna(-9)) if _usa_fill(mdl) else (lambda d: d)

    def ajusta(Xt, yt, Xv):
        return np.mean([prever_binario(_modelo(mdl, sd), Xt, yt, Xv) for sd in range(seeds)], axis=0)

    out = pd.Series(np.nan, index=va.index)
    if tipo == "peca":
        for p in PECAS:
            t, v = tr[tr["peca"] == p], va[va["peca"] == p]
            out.loc[v.index] = ajusta(fill(t[FF]), t["y"], fill(v[FF]))
    else:
        G = FF + ["peca_i"]
        out[:] = ajusta(fill(tr[G]), tr["y"], fill(va[G]))
    return _logit(out)


# ------------------------------------------------------------------ montagem completa das variáveis
def detector_falha_anterior(L, FS):
    """Probabilidade calibrada (isotônica, fora-da-amostra em 5 blocos de tempo) de falha às 06:00 de cada data de grade
    (linhas 'cand1'). Detecta, só pela rampa de telemetria até D 05:00, as peças trocadas por corretiva no ciclo anterior."""
    c1 = L[L["cand1"]].copy()
    c1["y"] = c1["y1"]
    rotulada = c1["y_known"] & ~c1["incerto"]
    lb, un = c1[rotulada], c1[~rotulada]
    if lb.empty:
        return pd.Series(0.0, index=c1.index)

    def ajusta(tr, va):
        o = pd.DataFrame(index=va.index, columns=["h", "e"], dtype=float)
        for p in PECAS:
            t, v = tr[tr["peca"] == p], va[va["peca"] == p]
            o.loc[v.index, "h"] = np.mean([prever_binario(_modelo("hgb_slow", s), t[FS], t["y"], v[FS]) for s in range(2)], axis=0)
            o.loc[v.index, "e"] = prever_binario(_modelo("et_det", 0), t[FS].fillna(-9), t["y"], v[FS].fillna(-9))
        return o

    blk = np.arange(len(lb)) * 5 // len(lb) if len(lb) < 5 else pd.qcut(lb["dia_ref"].rank(method="first"), 5, labels=False)
    oof = pd.concat([ajusta(lb[blk != b], lb[blk == b]) for b in range(5)])
    full = ajusta(lb, un)
    s_oof, s_full = (oof["h"] + oof["e"]) / 2, (full["h"] + full["e"]) / 2
    iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(s_oof.values, lb.loc[s_oof.index, "y"].values)
    print("   detector de falha anterior: AP fora-da-amostra =",
          round(average_precision_score(lb.loc[s_oof.index, "y"], s_oof), 3))
    return pd.concat([pd.Series(iso.predict(s_oof.values), index=s_oof.index),
                      pd.Series(iso.predict(s_full.values), index=s_full.index)])


def ciclos_inferidos(L, p1):
    """pf{j}_hat = prob. de falha na j-ésima data de grade anterior; kany_hat = ciclos desde a última troca (preventiva OU falha)."""
    chave = pd.MultiIndex.from_arrays([L.loc[p1.index, "id_maquina"], L.loc[p1.index, "peca"], L.loc[p1.index, "dia_ref"]])
    P = pd.Series(p1.values, index=chave)
    ph = {}
    for j in range(1, 7):
        i = pd.MultiIndex.from_arrays([L["id_maquina"], L["peca"], L["dia_ref"] + pd.Timedelta(days=1 - 15 * j)])
        ph[j] = P.reindex(i).values
        L[f"pf{j}_hat"] = ph[j]
    k = L["k"].values
    kh, soft = k.copy(), np.ones(len(L))
    for j in range(6, 0, -1):
        kh = np.where((np.nan_to_num(ph[j]) > 0.5) & (j < kh), j, kh)
    for j in range(1, 6):
        soft = np.where(j < k, soft * (1 - np.nan_to_num(ph[j])), soft)
    L["kany_hat"], L["alive_soft"] = kh, soft
    L["pf_max_hat"] = np.nanmax(np.stack([np.where(j < k, np.nan_to_num(ph[j]), 0) for j in range(1, 6)]), axis=0)
    return L


def montar_tudo(base_path, tel_path, err_path, falhas_path, bm_path, *, periodo=None, rotulos=None):
    L = montar(base_path, tel_path, err_path, falhas_path, periodo)
    L["cand1"] = ((L["dprev"] % 15) - FASE_CAND1).abs() < 0.01
    fs = alvo_falhas(falhas_path)
    L["y1"] = [int((m, p, d) in fs) for m, p, d in zip(L["id_maquina"], L["peca"], L["dia_ref"])]   # falha às 06:00 do próprio dia D
    if rotulos is not None:
        L["y"] = rotulos.reindex(pd.MultiIndex.from_frame(L[["id_maquina", "dia_ref", "peca"]])).to_numpy()
        L["y_known"] = L["y"].notna()
        L["incerto"] = False  # rótulos incertos foram retirados da referência
        L["y"] = L["y"].fillna(0).astype(int)
    Z = _normalizados(tel_path)
    L = L.join(feats_perfil(Z, L))
    L = L.join(derivar_forma(L.loc[L["cand"] | L["cand1"]]))
    L = L.join(feats_ciclos(Z, L))
    F0 = colunas(L)
    forma = list(derivar_forma(L.loc[L["cand"] | L["cand1"]].head(5)).columns)
    FS = [c for c in F0 if not c.startswith("blk")] + NEWS + forma + [f"blk{j}" for j in (0, 1, 2, 3, 4, 6, 8)]
    L = ciclos_inferidos(L, detector_falha_anterior(L, FS))
    b = pd.read_csv(bm_path, encoding="utf-8-sig", parse_dates=["dia_ref"])
    for c in ["versao_firmware", "fornecedor_peca_atual"]:
        b[c + "_c"] = b[c].astype("category").cat.codes
    L["idx_"] = L.index
    L = L.merge(b[["id_maquina", "dia_ref", "peca"] + EX], on=["id_maquina", "dia_ref", "peca"], how="left").set_index("idx_")
    L.index.name = None
    L["mid"] = L["id_maquina"].str[1:].astype(int)
    conj = {"FS": FS, "FB": F0 + NEWS + forma}
    conj["FS2"] = FS + HATF + DROPF
    conj["FS2+mid"] = conj["FS2"] + ["mid"]
    conj["FS2+EX+mid"] = conj["FS2"] + EX + ["mid"]
    conj["FS2+EX"] = conj["FS2"] + EX
    conj["FS2nd+EX+mid"] = FS + HATF + EX + ["mid"]                      # sem as variáveis drop/bef
    conj["FS2+EX+mid+prof"] = conj["FS2+EX+mid"] + [f"prof{h}" for h in range(0, 48, 2)]
    return L, conj


# ------------------------------------------------------------------ componentes e fusão
# (nome, tipo, modelo, conjunto de variáveis)  -- família "antiga": sem filtro, sem variáveis de ciclo
ANTIGOS = [("hgb_d3_pp", "peca", "hgb_d3", "FS"), ("hgb_d2_pp", "peca", "hgb_d2", "FS"), ("hgb_slow_pp", "peca", "hgb_slow", "FS"),
           ("hgb_d3_pool", "pool", "hgb_d3", "FS"), ("hgb_slow_pool", "pool", "hgb_slow", "FS"), ("hgb_d1_pool", "pool", "hgb_d1", "FS"),
           ("et_pp", "peca", "et", "FS"), ("et_pool", "pool", "et", "FS"), ("hgb_d3_pool_blkall", "pool", "hgb_d3", "FB")]
# família "hat": com variáveis de ciclo e filtro das linhas com falha anterior inferida
HAT = [("v15", "et_hat_n700", "FS2"), ("v21", "et_hat_n1500", "FS2"), ("v28", "et_hat_n700", "FS2+mid"), ("v30", "et_hat_n700", "FS2+EX+mid")]


def _vetor(va, escore, base=1e-5):
    v = pd.Series(base, index=va.index)
    v.loc[escore.index] = escore.values
    return v


NOVOS = [("N1", "hgb_n1", "FS", 4), ("N2", "hgb_n2", "FS", 4), ("N3", "hgb_n3", "FS", 4), ("N4", "et_n4", "FS", 3),
         ("N5", "et_n5", "FS", 3), ("N6", "rf_n6", "FS", 1), ("N7", "gbc_n7", "FS", 1)]   # (nome, modelo, variáveis, sementes quando --seeds 3)
_sig = lambda s: pd.Series(np.clip(1 / (1 + np.exp(-s.values)), 1e-5, 1), index=s.index)


def vetores_antigos(tr, va, conj, seeds):
    """v05 (HGB lento por peça), v06 (ET por peça) e v07 (blend por rank dos 9 modelos antigos). Sem filtro."""
    P = {n: treinar(tr, va, tipo, mdl, conj[fs], seeds) for n, tipo, mdl, fs in ANTIGOS}
    pe = va.loc[P["et_pp"].index, "peca"]
    V = {"v05": _vetor(va, _sig(P["hgb_slow_pp"])), "v06": _vetor(va, _sig(P["et_pp"]))}
    z = sum(P[n].groupby(pe).rank(pct=True) for n, *_ in ANTIGOS) / len(ANTIGOS)
    V["v07"] = _vetor(va, (1e-3 + 0.999 * z).clip(upper=1))
    return {k: v.round(6) for k, v in V.items()}


def vetores_novos(tr, va, conj, seeds):
    """N1-N3 (HGB), N4-N5 (ET gini), N6 (Random Forest) e N7 (GradientBoosting), todos por peça e sem filtro."""
    V = {}
    for nome, mdl, fs, ns in NOVOS:
        V[nome] = _vetor(va, _sig(treinar(tr, va, "peca", mdl, conj[fs], max(1, round(ns * seeds / 3)))))
    return {k: v.round(6) for k, v in V.items()}


def vetores_hat(tr, va, conj, seeds, lista):
    """Listas 'hat' (ET com variáveis de ciclo); linhas com pf1_hat >= CFG['gate'] ficam fora do treino e rebaixadas na previsão."""
    gate = lambda d: d["pf1_hat"].fillna(0) < CFG["gate"]
    trg = tr.copy()
    trg["cand"] = trg["cand"] & gate(trg)
    vag = va.copy()
    vag["cand"] = vag["cand"] & gate(vag)
    V = {}
    for nome, mdl, fs in lista:
        lg = treinar(trg, vag, "peca", mdl, conj[fs], seeds)
        p_ = vag.loc[lg.index, "peca"]
        pct = lg.groupby(p_).rank(pct=True).groupby(p_).rank(pct=True)
        v = _vetor(va, (1e-3 + 0.999 * pct).clip(upper=1))
        v.loc[va.index[va["cand"] & ~vag["cand"]]] = 1e-4
        V[nome] = v
    return {k: v.round(6) for k, v in V.items()}


def construir_vetores(tr, va, conj, seeds):
    """As 7 listas da sub 37 (+ extras do preset ativo). Usado pela validação."""
    return {**vetores_antigos(tr, va, conj, seeds), **vetores_hat(tr, va, conj, seeds, HAT + CFG["hat_extra"])}


def fundir(V, va, k=K_RRF, pesos=None):
    """Fusão RRF: soma de peso/(k + posição) por peça (posição 1 = mais provável; empates = posição média).
    'pesos' = dict nome->peso (só as listas citadas entram); sem 'pesos', entram todas as listas de V."""
    pw = pesos if pesos is not None else {n: CFG["pesos"].get(n, 1.0) for n in V}
    rk = {n: V[n].groupby(va["peca"]).rank(ascending=False, method="average") for n in pw}
    if CFG["agg"] == "geo":
        z = -sum(w * np.log(CFG["geo_k"] + rk[n]) for n, w in pw.items()) / sum(pw.values())
    else:
        z = sum(w / (k + rk[n]) for n, w in pw.items())
    z = normalizar(z)
    return (1e-5 + 0.99999 * z).round(6)


def validar(L, conj, seeds=1):
    """AP por peça em 3 janelas temporais: fusão e cada lista isolada (treino só com dias anteriores à janela)."""
    rot = L[L["y_known"] & ~L["incerto"]]
    aps = {}
    for a, z in JANELAS:
        tr = rot[rot["dia_ref"] < pd.Timestamp(a)]
        va = rot[(rot["dia_ref"] >= pd.Timestamp(a)) & (rot["dia_ref"] <= pd.Timestamp(z))]
        V = construir_vetores(tr, va, conj, seeds)
        V["FUSAO"] = fundir({n: v for n, v in V.items()}, va)
        for n, v in V.items():
            aps.setdefault(n, []).append(np.mean([average_precision_score(va.loc[va["peca"] == p, "y"], v[va["peca"] == p]) for p in PECAS]))
        print(f"janela {a}..{z}: fusão AP = {aps['FUSAO'][-1]:.4f}", flush=True)
    for n, v in aps.items():
        print(f"   {n:8s} AP médio = {np.mean(v):.4f}  por janela = {np.round(v, 3).tolist()}")


def salvar_lista(v, teste, caminho, sample):
    """Grava uma lista de previsão (uma pontuação por linha de teste) no formato id, peca_A..peca_D."""
    t = teste[["id_maquina", "dia_ref", "peca"]].copy()
    t["p"] = v
    e = t.pivot_table(index=["id_maquina", "dia_ref"], columns="peca", values="p").reset_index()
    e["id"] = e["id_maquina"] + "_" + e["dia_ref"].dt.strftime("%Y-%m-%d")
    e = e[["id"] + PECAS].round(6)
    if Path(sample).exists():
        e = pd.read_csv(sample)[["id"]].merge(e, on="id", how="left")
    e = e[["id"] + PECAS]
    assert e[PECAS].notna().all().all()
    e.to_csv(caminho, index=False)
    return e


def melhores_n(listas, n=3, k=30):
    """Fusão 'melhores n posições': por (id, peça), média dos n maiores 1/(k+posição) entre as listas (posição 1 = mais provável)."""
    ids = listas[0]["id"].values
    out = pd.DataFrame({"id": ids})
    for p in PECAS:
        R = np.stack([d.set_index("id").loc[ids, p].rank(ascending=False, method="average").values for d in listas])
        z = np.sort(1.0 / (k + R), axis=0)[::-1][:n].mean(axis=0)
        ativos = np.any([d.set_index("id").loc[ids, p].to_numpy() > 1e-5 for d in listas], axis=0)
        out[p] = np.where(ativos, 1e-5 + 0.99999 * normalizar(z), 1e-5).round(6)
    return out


def receitas(nomes_novos):
    """Receita de cada lista fundida (nome da lista -> peso). 41 e 43 vêm do script das subs 41/43; 37, 40, 44 e 42 da descrição."""
    s37 = {n: 1.0 for n in ("v05", "v06", "v07", "v15", "v21", "v28", "v30")}
    return {"sub37": dict(s37),
            "sub40": {**s37, "v15": 2.0, "v30": 2.0},
            "sub41": {**s37, "v05": 2.0},
            "sub44": {n: w for n, w in s37.items() if n != "v07"},
            "sub43": {**{n: 1.0 for n in ("v05", "v06", "v15", "v21", "v28", "v30", "N1", "N2", "N3", "N4", "N5")}},
            "sub42": {**s37, **{n: 1.0 for n in nomes_novos}}}


def pipeline(rot, teste, conj, seeds, k, sample, pasta, keep=3):
    """Treina tudo do zero e devolve (listas reconstruídas, p06, y09). Nenhuma sub anterior é lida."""
    pasta.mkdir(parents=True, exist_ok=True)
    print("== rodada 1: listas antigas (v05, v06, v07), 'hat' (v15, v21, v28, v30) e novas (N1..N7)", flush=True)
    V_ant = vetores_antigos(rot, teste, conj, seeds)
    V_hat = vetores_hat(rot, teste, conj, seeds, HAT)
    V_nov = vetores_novos(rot, teste, conj, seeds)
    todas = {**V_ant, **V_hat, **V_nov}
    for nome, v in todas.items():
        salvar_lista(v, teste, pasta / f"lista_{nome}.csv", sample)
    R = receitas(list(V_nov))
    rec = {nome: salvar_lista(fundir(todas, teste, k, w), teste, pasta / f"{nome}_reconstruida.csv", sample) for nome, w in R.items()}
    print("== rodada 2: preset p06 (filtro 0,7 + listas v31, v32, v33)", flush=True)
    CFG.update(PRESETS["p06"])
    V_hat6 = vetores_hat(rot, teste, conj, seeds, HAT + CFG["hat_extra"])
    V6 = {**V_ant, **V_hat6}
    for nome in ("v31", "v32", "v33"):
        salvar_lista(V6[nome], teste, pasta / f"lista_p06_{nome}.csv", sample)
    p06 = salvar_lista(fundir(V6, teste, k, {n: 1.0 for n in V6}), teste, pasta / "p06.csv", sample)
    print("== fusão final: 3 melhores posições de [sub41, sub43, sub42, sub44, sub40, p06]", flush=True)
    y09 = melhores_n([rec["sub41"], rec["sub43"], rec["sub42"], rec["sub44"], rec["sub40"], p06], keep, k)
    assert y09[PECAS].notna().all().all() and ((y09[PECAS] >= 0) & (y09[PECAS] <= 1)).all().all()
    y09.to_csv(pasta / "y09.csv", index=False)
    rec["p06"], rec["y09"] = p06, y09
    return rec, p06, y09


def _sha(caminho, n=1 << 20):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for b in iter(lambda: f.read(n), b""):
            h.update(b)
    return h.hexdigest()


def comparar(df, ref, rotulo, limite=0.98):
    """Top 5% em comum e correlação de postos (Spearman) por peça entre a tabela gerada e a tabela de referência (por id)."""
    ref = ref.set_index("id")
    df = df.set_index("id").loc[ref.index]
    k5 = int(round(0.05 * len(ref)))
    ov = [len(set(df[p].nlargest(k5).index) & set(ref[p].nlargest(k5).index)) / k5 for p in PECAS]
    rho = [df[p].rank().corr(ref[p].rank()) for p in PECAS]
    ok = all(x >= limite for x in ov)
    print(f"   {rotulo}: top 5% em comum por peça = {[round(x, 3) for x in ov]} | Spearman = {[round(x, 4) for x in rho]} "
          f"-> {'PASSA' if ok else 'NÃO PASSA'} (limite {limite} no top 5%)")
    return ok


def main():
    global SEEDS, K_RRF
    RAIZ = Path(__file__).resolve().parent.parent
    TRATADOS = RAIZ / "dados" / "tratados"
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", default=str(TRATADOS))
    ap.add_argument("--base", default=None)
    ap.add_argument("--telemetria", default=None)
    ap.add_argument("--erros", default=None)
    ap.add_argument("--falhas", default=None)
    ap.add_argument("--base_modelagem", default=str(TRATADOS / "base_modelagem.csv"))
    ap.add_argument("--sample", default=str(TRATADOS / "sample_submission.csv"))
    ap.add_argument("--pasta", default=str(RAIZ / "saidas" / "y09_pipeline"))
    ap.add_argument("--referencia", default=None, help="CSV da tabela de submissão de referência (a enviada) para conferir a reprodução")
    ap.add_argument("--conferir", default=None, help="pasta com os sub_37/40..44 e p06 originais, só para medir a reconstrução")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--k", type=int, default=30)
    ap.add_argument("--keep", type=int, default=3)
    a = ap.parse_args()
    SEEDS, K_RRF = max(1, a.seeds), a.k
    pasta, D = Path(a.pasta), Path(a.dados)
    import numpy, sklearn
    print(f"versões: python {platform.python_version()} | pandas {pd.__version__} | numpy {numpy.__version__} | "
          f"scikit-learn {sklearn.__version__} | seeds {SEEDS} | k {K_RRF}", flush=True)
    L, conj = montar_tudo(a.base or D / "base_integrada_maquina_dia.csv", a.telemetria or D / "telemetria_corrigido.csv",
                          a.erros or D / "erros_corrigido.csv", a.falhas or D / "falhas_corrigido.csv", a.base_modelagem)
    rot = L[L["y_known"] & ~L["incerto"]]
    teste = L[L["dia_ref"].between(INICIO_TESTE, INICIO_TESTE + pd.Timedelta(days=DIAS_TESTE - 1))].copy()
    print("linhas treino:", len(rot), "| positivos:", int(rot["y"].sum()), "| teste:", len(teste),
          "| candidatos no teste:", int(teste["cand"].sum()), flush=True)
    pasta.mkdir(parents=True, exist_ok=True)
    gt = teste.loc[teste["cand"] & (teste["pf1_hat"].fillna(0) >= 0.5), ["id_maquina", "dia_ref", "peca", "pf1_hat"]].copy()
    gt["id"] = gt["id_maquina"] + "_" + gt["dia_ref"].dt.strftime("%Y-%m-%d")
    gt[["id", "peca", "pf1_hat"]].to_csv(pasta / "gate_pf1.csv", index=False)         # para aplicar_gate.py
    rec, p06, y09 = pipeline(rot, teste, conj, SEEDS, K_RRF, a.sample, pasta, a.keep)
    if a.conferir:
        for nome, pref in [("sub37", "sub_37"), ("sub40", "sub_40"), ("sub41", "sub_41"), ("sub42", "sub_42"),
                           ("sub43", "sub_43"), ("sub44", "sub_44"), ("p06", "p06")]:
            g = sorted(Path(a.conferir).glob(f"{pref}*.csv"))
            if not g:
                continue
            ref = pd.read_csv(g[0]).set_index("id")
            k5 = int(round(0.05 * len(ref)))
            ov = [len(set(rec[nome].set_index("id").loc[ref.index, p].nlargest(k5).index) & set(ref[p].nlargest(k5).index)) / k5 for p in PECAS]
            print(f"   conferência {nome} vs {g[0].name}: top 5% em comum por peça = {[round(x, 3) for x in ov]}")
    if a.referencia:
        ref = pd.read_csv(a.referencia)
        comparar(y09, ref, "y09 gerada vs tabela de referência")
    entradas = {"base": a.base or D / "base_integrada_maquina_dia.csv", "telemetria": a.telemetria or D / "telemetria_corrigido.csv",
                "erros": a.erros or D / "erros_corrigido.csv", "falhas": a.falhas or D / "falhas_corrigido.csv",
                "base_modelagem": a.base_modelagem}
    man = {"python": platform.python_version(), "pandas": pd.__version__, "numpy": numpy.__version__, "scikit-learn": sklearn.__version__,
           "seeds": SEEDS, "k": K_RRF, "keep": a.keep,
           "entradas_sha256": {n: _sha(p) for n, p in entradas.items() if Path(p).exists()},
           "saidas_sha256": {f: _sha(pasta / f) for f in ("y09.csv", "p06.csv")}}
    (pasta / "manifesto.json").write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
    print("salvo", pasta / "y09.csv", y09.shape, "| manifesto.json também gravado")


if __name__ == "__main__":
    main()
