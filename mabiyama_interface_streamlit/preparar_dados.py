"""Gera a pasta dados/ do painel a partir das bases TRATADAS da equipe.

O painel não lê as bases diretamente: este script resume tudo em arquivos agregados (contagens, médias,
gráficos prontos). Assim o repositório não carrega nenhuma base da competição, só números já resumidos.

Uso:
    python preparar_dados.py --bases <pasta com as bases tratadas> [--saida dados]

Bases usadas (todas *_corrigido.csv do ETL da equipe):
    maquinas_corrigido.csv, falhas_corrigido.csv, manutencao_corrigido.csv, erros_corrigido.csv,
    telemetria_corrigido.csv

Arquivos que NÃO saem daqui (vêm do modelo, ver README): previsao.csv, validacao.csv, importancia.csv.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PECAS = ["peca_A", "peca_B", "peca_C", "peca_D"]
SENSOR_DA_PECA = {"peca_A": "sensor_c", "peca_B": "sensor_d", "peca_C": "sensor_b", "peca_D": "sensor_a"}
SENS = ["sensor_a", "sensor_b", "sensor_c", "sensor_d", "vibracao_mm_s"]


def ler(pasta, nome, datas=()):
    return pd.read_csv(Path(pasta) / nome, encoding="utf-8-sig", parse_dates=list(datas))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bases", required=True)
    ap.add_argument("--saida", default=str(Path(__file__).resolve().parent / "dados"))
    a = ap.parse_args()
    out = Path(a.saida)
    out.mkdir(parents=True, exist_ok=True)

    maq = ler(a.bases, "maquinas_corrigido.csv")
    fal = ler(a.bases, "falhas_corrigido.csv", ["data_hora"])
    man = ler(a.bases, "manutencao_corrigido.csv", ["data_hora"])
    err = ler(a.bases, "erros_corrigido.csv", ["data_hora"])
    tel = ler(a.bases, "telemetria_corrigido.csv", ["data_hora"])

    fal_ok = fal[fal["flag_falha_suspeita"] == 0].copy()          # o lote suspeito de 02/01 03:00 fica de fora
    prev = man[man["tipo"] == "preventiva"]
    maq["modelo"] = "Modelo " + maq["modelo"].str[-1].str.upper()

    # cadastro mínimo usado na tabela de prioridade (sem número de série, fabricante etc.)
    maq[["id_maquina", "modelo", "idade"]].to_csv(out / "maquinas_resumo.csv", index=False)

    # indicadores da aba Análise Exploratória
    ind = {
        "maquinas": len(maq), "n_modelos": maq["modelo"].nunique(),
        "idade_min": maq["idade"].min(), "idade_max": maq["idade"].max(),
        "falhas": len(fal_ok), "falhas_suspeitas": int(fal["flag_falha_suspeita"].sum()),
        "preventivas": len(prev), "corretivas": int((man["tipo"] == "corretiva").sum()),
        "leituras": len(tel), "inicio": fal_ok["data_hora"].min().date(), "fim": fal_ok["data_hora"].max().date(),
    }
    pd.DataFrame([ind]).to_csv(out / "indicadores.csv", index=False)

    fal_ok["peca"].value_counts().reindex(PECAS, fill_value=0).rename_axis("peca").rename("falhas") \
        .reset_index().to_csv(out / "falhas_por_peca.csv", index=False)

    mes_f = fal_ok.groupby(fal_ok["data_hora"].dt.to_period("M")).size().rename("falhas")
    mes_p = prev.groupby(prev["data_hora"].dt.to_period("M")).size().rename("preventivas")
    mes = pd.concat([mes_f, mes_p], axis=1).fillna(0).astype(int)
    mes = mes[(mes.index >= mes_f.index.min()) & (mes.index <= mes_f.index.max())]
    mes.index = mes.index.astype(str)
    mes.rename_axis("mes").reset_index().to_csv(out / "mensal.csv", index=False)

    por_maq = fal_ok.groupby("id_maquina").size().reindex(maq["id_maquina"], fill_value=0)
    t = maq.assign(falhas=por_maq.values).dropna(subset=["idade"])
    t["faixa"] = pd.cut(t["idade"], [-1, 3, 7, 11, 15, 21], labels=["0–3", "4–7", "8–11", "12–15", "16–20"])
    t.groupby("faixa", observed=True).agg(maquinas=("falhas", "size"), falhas_por_maquina=("falhas", "mean")) \
        .round(2).reset_index().to_csv(out / "falhas_por_idade.csv", index=False)

    m = maq.assign(falhas=por_maq.values).groupby("modelo").agg(maquinas=("falhas", "size"), falhas=("falhas", "sum"))
    m["falhas_por_maquina"] = (m["falhas"] / m["maquinas"]).round(2)
    m.reset_index().to_csv(out / "falhas_por_modelo.csv", index=False)

    # erros: volume total e % lançados nas 24h antes de uma falha da mesma máquina
    f24 = fal_ok[["id_maquina", "data_hora"]].rename(columns={"data_hora": "t_falha"})
    e = err.reset_index().merge(f24, on="id_maquina", how="left")
    e["antes"] = (e["t_falha"] > e["data_hora"]) & (e["t_falha"] - e["data_hora"] <= pd.Timedelta(hours=24))
    e = e.groupby(["index", "codigo_erro"], as_index=False)["antes"].any()
    r = e.groupby("codigo_erro").agg(total=("antes", "size"), pct_antes_falha=("antes", "mean")).round(4)
    r.index = r.index.str.replace("erro_", "")
    r.rename_axis("codigo").reset_index().to_csv(out / "erros_pre_falha.csv", index=False)

    # sinal do sensor da peça nas 48h antes da falha, em desvios do normal da própria máquina
    w = tel.set_index(["id_maquina", "data_hora"]).sort_index()
    curvas = []
    for r in fal_ok.itertuples():
        if r.id_maquina not in w.index.get_level_values(0):
            continue
        x = w.loc[r.id_maquina, SENSOR_DA_PECA[r.peca]]
        seg = x[(x.index >= r.data_hora - pd.Timedelta(hours=48)) & (x.index < r.data_hora)].dropna()
        base = x[(x.index >= r.data_hora - pd.Timedelta(days=20)) & (x.index < r.data_hora - pd.Timedelta(days=5))].dropna()
        if len(seg) < 24 or len(base) < 48 or base.std() == 0:
            continue
        h = ((seg.index - r.data_hora) / pd.Timedelta(hours=1)).astype(int)
        curvas.append(pd.DataFrame({"peca": r.peca, "h": h, "z": (seg.values - base.median()) / base.std()}))
    pd.concat(curvas).groupby(["peca", "h"])["z"].mean().round(4).reset_index().to_csv(out / "sinal_pre_falha.csv", index=False)

    # qualidade das bases tratadas
    def q(nome, df, chave, cols=None):
        cols = cols or [c for c in df.columns if not c.startswith("flag_")]
        return {"tabela": nome, "linhas": len(df), "nulos_pct": round(df[cols].isna().mean().mean() * 100, 2),
                "duplic_pct": round(df.duplicated(chave).mean() * 100, 2)}
    pd.DataFrame([
        q("telemetria", tel, ["id_maquina", "data_hora"], SENS),
        q("erros", err, ["id_maquina", "data_hora", "codigo_erro"]),
        q("manutenção", man, ["id_maquina", "data_hora", "peca"]),
        q("falhas", fal, ["id_maquina", "data_hora", "peca"]),
        q("máquinas", maq, ["id_maquina"]),
    ]).to_csv(out / "qualidade.csv", index=False)

    print("dados gerados em", out)
    for f in sorted(out.glob("*.csv")):
        print(f"  {f.name:24s} {f.stat().st_size / 1024:8.1f} KB")


if __name__ == "__main__":
    main()
