"""Gera a base integrada máquina x dia (base_integrada_maquina_dia) a partir das tabelas tratadas.

Entrada: pasta com as seis tabelas corrigidas pelo ETL, em CSV ou Parquet
    maquinas_corrigido, telemetria_corrigido, operacao_corrigido, erros_corrigido,
    manutencao_corrigido, falhas_corrigido

Saída: base_integrada_maquina_dia.csv (e .parquet, com --parquet) na pasta de saída.

Uso:
    python ferramentas/integracao.py --bases dados/tratados --saida dados/tratados [--parquet]

Premissas (as mesmas do Relatório de Qualidade):
- A previsão do dia D é feita às 05:00. As variáveis do dia D usam só dados em (D-1 05:00, D 05:00].
- O alvo do dia D é a falha de cada peça em (D 05:00, D+1 05:00]. Falhas e manutenções são lançadas
  às 06:00, depois do corte, então não entram nas variáveis do próprio dia.
- Turnos (assumido, confirmar com o cliente): manha 06:00, tarde 14:00, noite 22:00, 8 h cada. Um turno
  só entra no dia D se terminou até o corte.
- Falhas com flag_falha_suspeita ficam fora do alvo e marcam alvo_incerto = 1 (ACAO_FALHA_SUSPEITA).
- Depois da última falha registrada o alvo fica vazio e alvo_disponivel = 0 (não se sabe se houve falha).
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HORA_CORTE = 5
TURNOS = {"manha": 6, "tarde": 14, "noite": 22}
DURACAO_TURNO_H = 8
ACAO_FALHA_SUSPEITA = "excluir_do_alvo"  # ou "manter_no_alvo"
PECAS = ["peca_A", "peca_B", "peca_C", "peca_D"]
SENSORES = ["sensor_a", "sensor_b", "sensor_c", "sensor_d", "vibracao_mm_s"]
CODIGOS = [f"erro_E{i}" for i in range(1, 6)]
FLAGS_TELEMETRIA = ["sentinela_999", "sinal_corrigido", "zero_sensor", "escala_sensor_a", "sensor_b_recuperado",
                    "sensor_b_aux_recuperado", "suspeita", "conflito", "hora_faltante"]
FLAGS_CADASTRO = ["flag_trio_preenchido", "flag_idade_recuperada", "flag_ano_instalacao_imputado",
                  "flag_sem_idade_nem_data"]
CHAVE = ["id_maquina", "dia_ref"]


def ler(pasta, nome):
    pasta = Path(pasta)
    for ext in ("parquet", "csv"):
        arq = pasta / f"{nome}.{ext}"
        if arq.exists():
            return pd.read_parquet(arq) if ext == "parquet" else pd.read_csv(arq, encoding="utf-8-sig")
    raise FileNotFoundError(f"{nome}.csv ou {nome}.parquet não encontrado em {pasta}")


def dia_da_janela(instante):
    """Dia D cuja janela de variáveis (D-1 05:00, D 05:00] contém o instante."""
    return (instante - pd.Timedelta(hours=HORA_CORTE) - pd.Timedelta(microseconds=1)).dt.normalize() + pd.Timedelta(days=1)


def grade(maquinas, dias):
    g = pd.MultiIndex.from_product([sorted(maquinas), dias], names=CHAVE).to_frame(index=False)
    return g


def telemetria_dia(tel):
    tel = tel.copy()
    tel["dia_ref"] = dia_da_janela(pd.to_datetime(tel["data_hora"]))
    agg = {}
    for s in SENSORES:
        agg[f"{s}_media"] = (s, "mean")
        agg[f"{s}_dp"] = (s, "std")
        agg[f"{s}_min"] = (s, "min")
        agg[f"{s}_max"] = (s, "max")
    agg["temp_ambiente_c_media"] = ("temp_ambiente_c", "mean")
    agg["umidade_relativa_media"] = ("umidade_relativa", "mean")
    for f in FLAGS_TELEMETRIA:
        agg[f"n_{f}"] = (f"flag_{f}", "sum")
    agg["n_horas_na_janela"] = ("data_hora", "size")
    tel["_com_leitura"] = 1 - tel["flag_hora_faltante"]
    agg["n_horas_com_leitura"] = ("_com_leitura", "sum")
    return tel.groupby(CHAVE).agg(**agg).reset_index()


def erros_dia(er):
    er = er.copy()
    er["dia_ref"] = dia_da_janela(pd.to_datetime(er["data_hora"]))
    pico = er["flag_horario_pico"] == 1
    # Erros lançados no horário de pico não têm horário informativo: contam só em n_erros_pico.
    normal = er[~pico]
    res = normal.groupby(CHAVE).agg(
        n_erros=("codigo_erro", "size"),
        n_erros_sev_baixa=("severidade", lambda s: (s == "baixa").sum()),
        n_erros_sev_media=("severidade", lambda s: (s == "media").sum()),
        n_erros_sev_alta=("severidade", lambda s: (s == "alta").sum()))
    # O tempo de reconhecimento vale para todos os erros, inclusive os do pico.
    tempo = er.groupby(CHAVE)["tempo_reconhecimento_min"].mean().rename("tempo_reconhecimento_min_media")
    cod = (normal.groupby(CHAVE + ["codigo_erro"]).size().unstack(fill_value=0)
           .reindex(columns=CODIGOS, fill_value=0))
    cod.columns = [f"n_{c}" for c in cod.columns]
    n_pico = er[pico].groupby(CHAVE).size().rename("n_erros_pico")
    return res.join(n_pico, how="outer").join(cod, how="outer").join(tempo, how="outer").reset_index()


def operacao_dia(op):
    op = op[op["turno"].isin(TURNOS)].copy()
    fim = (pd.to_datetime(op["data"]) + pd.to_timedelta(op["turno"].map(TURNOS) + DURACAO_TURNO_H, unit="h"))
    op["dia_ref"] = dia_da_janela(fim)
    d = op.groupby(CHAVE).agg(
        op_pecas_produzidas=("pecas_produzidas", lambda s: s.sum(min_count=1)),
        op_meta_producao=("meta_producao", lambda s: s.sum(min_count=1)),
        op_pecas_defeituosas=("pecas_defeituosas", lambda s: s.sum(min_count=1)),
        op_qtd_operadores_media=("qtd_operadores", "mean"),
        op_tempo_setup_min=("tempo_setup_min", "sum"),
        op_consumo_energia_kwh=("consumo_energia_kwh", "sum"),
        op_utilizacao_pct_media=("utilizacao_pct", "mean"),
        op_ind_quebra=("ind_quebra", "mean"),
        op_score_saude=("score_saude", "mean"),
        op_hora_extra=("hora_extra", "max"),  # 1 se algum turno do dia teve hora extra
        op_n_turnos=("turno", "size")).reset_index()
    d[["op_pecas_produzidas", "op_pecas_defeituosas"]] = d[["op_pecas_produzidas", "op_pecas_defeituosas"]].astype(float)
    d["op_taxa_defeito"] = d["op_pecas_defeituosas"] / d["op_pecas_produzidas"].replace(0, np.nan)
    d["op_pct_meta"] = d["op_pecas_produzidas"] / d["op_meta_producao"].replace(0, np.nan)
    return d


def dias_desde(base, mn, prefixo, filtro=None):
    """Dias entre o corte de D (05:00) e a última troca da peça antes dele. Vazio se não houve troca."""
    mn = mn if filtro is None else mn[filtro]
    corte = pd.to_datetime(base["dia_ref"]) + pd.Timedelta(hours=HORA_CORTE)
    for p in PECAS:
        trocas = (mn.loc[mn["peca"] == p, ["id_maquina", "data_hora"]]
                  .assign(ultima=lambda x: pd.to_datetime(x["data_hora"])).drop(columns="data_hora")
                  .sort_values("ultima"))
        esq = base[["id_maquina"]].assign(corte=corte).reset_index().sort_values("corte")
        m = pd.merge_asof(esq, trocas, left_on="corte", right_on="ultima", by="id_maquina",
                          direction="backward", allow_exact_matches=True).set_index("index").sort_index()
        base[f"{prefixo}_{p}"] = (m["corte"] - m["ultima"]).dt.total_seconds() / 86400
    return base


def cadastro(maq):
    c = maq[["id_maquina", "modelo", "linha_producao"] + FLAGS_CADASTRO].rename(
        columns={f: f"cad_{f}" for f in FLAGS_CADASTRO})
    inst = pd.to_datetime(maq["data_instalacao"], errors="coerce")
    aprox = inst.isna() & maq["ano_instalacao"].notna()
    # Sem a data, só o ano é conhecido: usa-se o meio do ano e a idade fica marcada como aproximada.
    inst = inst.where(~aprox, pd.to_datetime(maq["ano_instalacao"].astype("Int64").astype(str) + "-07-01", errors="coerce"))
    c["_instalacao"] = inst.values
    c["flag_idade_aproximada"] = aprox.astype(int).values
    return c


def alvos(base, fa):
    fa = fa.copy()
    fa["dia_ref"] = (pd.to_datetime(fa["data_hora"]) - pd.Timedelta(hours=HORA_CORTE) - pd.Timedelta(microseconds=1)).dt.normalize()
    ultima = fa["dia_ref"].max()
    suspeita = fa["flag_falha_suspeita"] == 1
    validas = fa[~suspeita] if ACAO_FALHA_SUSPEITA == "excluir_do_alvo" else fa
    t = (validas.assign(v=1).pivot_table(index=CHAVE, columns="peca", values="v", aggfunc="max", fill_value=0)
         .reindex(columns=PECAS, fill_value=0))
    t.columns = [f"alvo_falha_{p}" for p in t.columns]
    t = t.reset_index()
    t["dia_ref"] = t["dia_ref"].dt.strftime("%Y-%m-%d")
    base = base.merge(t, on=CHAVE, how="left")
    cols = [f"alvo_falha_{p}" for p in PECAS]
    base[cols] = base[cols].fillna(0)
    base["alvo_falha_qualquer"] = base[cols].max(axis=1)
    inc = fa[suspeita].assign(dia_ref=lambda x: x["dia_ref"].dt.strftime("%Y-%m-%d"))[CHAVE].drop_duplicates()
    base = base.merge(inc.assign(alvo_incerto=1), on=CHAVE, how="left")
    base["alvo_incerto"] = base["alvo_incerto"].fillna(0).astype("int64")
    base["alvo_disponivel"] = (pd.to_datetime(base["dia_ref"]) <= ultima).astype("int64")
    base.loc[base["alvo_disponivel"] == 0, cols + ["alvo_falha_qualquer"]] = np.nan
    return base


def integrar(pasta):
    maq = ler(pasta, "maquinas_corrigido")
    tel = ler(pasta, "telemetria_corrigido")
    ids = set(maq["id_maquina"])

    tel_d = telemetria_dia(tel[tel["id_maquina"].isin(ids)])
    dias = pd.date_range(tel_d["dia_ref"].min(), tel_d["dia_ref"].max(), freq="D")
    base = grade(ids, dias)

    base = base.merge(cadastro(maq), on="id_maquina", how="left")
    base["idade_anos"] = (base["dia_ref"] - base["_instalacao"]).dt.days / 365.25
    base = base.drop(columns="_instalacao")

    base = base.merge(tel_d, on=CHAVE, how="left")
    base = base.merge(erros_dia(ler(pasta, "erros_corrigido")), on=CHAVE, how="left")
    base = base.merge(operacao_dia(ler(pasta, "operacao_corrigido")), on=CHAVE, how="left")

    contagens = [f"n_{f}" for f in FLAGS_TELEMETRIA] + ["n_horas_na_janela", "n_horas_com_leitura", "n_erros",
                 "n_erros_pico", "n_erros_sev_baixa", "n_erros_sev_media", "n_erros_sev_alta"] + \
                [f"n_{c}" for c in CODIGOS] + ["op_tempo_setup_min", "op_hora_extra", "op_n_turnos"]
    base[contagens] = base[contagens].fillna(0).astype("int64")

    mn = ler(pasta, "manutencao_corrigido")
    base["dia_ref"] = base["dia_ref"].dt.strftime("%Y-%m-%d")
    base = dias_desde(base, mn, "dias_desde_prev", mn["tipo"] == "preventiva")
    base = dias_desde(base, mn, "dias_desde_troca")

    base = alvos(base, ler(pasta, "falhas_corrigido"))
    base = base.sort_values(CHAVE).reset_index(drop=True)

    ordem = (["id_maquina", "dia_ref", "modelo", "linha_producao"] + [f"cad_{f}" for f in FLAGS_CADASTRO]
             + ["idade_anos", "flag_idade_aproximada"]
             + [f"{s}_{a}" for s in SENSORES for a in ("media", "dp", "min", "max")]
             + ["temp_ambiente_c_media", "umidade_relativa_media"]
             + [f"n_{f}" for f in FLAGS_TELEMETRIA] + ["n_horas_na_janela", "n_horas_com_leitura"]
             + ["n_erros", "n_erros_pico", "n_erros_sev_baixa", "n_erros_sev_media", "n_erros_sev_alta"]
             + [f"n_{c}" for c in CODIGOS] + ["tempo_reconhecimento_min_media"]
             + ["op_pecas_produzidas", "op_meta_producao", "op_pecas_defeituosas", "op_qtd_operadores_media",
                "op_tempo_setup_min", "op_consumo_energia_kwh", "op_utilizacao_pct_media", "op_ind_quebra",
                "op_score_saude", "op_hora_extra", "op_n_turnos", "op_taxa_defeito", "op_pct_meta"]
             + [f"dias_desde_prev_{p}" for p in PECAS] + [f"dias_desde_troca_{p}" for p in PECAS]
             + [f"alvo_falha_{p}" for p in PECAS] + ["alvo_falha_qualquer", "alvo_incerto", "alvo_disponivel"])
    return base[ordem]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bases", default="dados/tratados", help="pasta com as tabelas *_corrigido")
    ap.add_argument("--saida", default=None, help="pasta de saída (padrão: a mesma de --bases)")
    ap.add_argument("--parquet", action="store_true", help="salvar também em Parquet (float32, zstd)")
    a = ap.parse_args()
    saida = Path(a.saida or a.bases)
    saida.mkdir(parents=True, exist_ok=True)

    base = integrar(a.bases)
    base.to_csv(saida / "base_integrada_maquina_dia.csv", index=False, encoding="utf-8-sig")
    if a.parquet:
        p = base.copy()
        for c in p.columns:
            if p[c].dtype == "float64":
                p[c] = p[c].astype("float32")
        p.to_parquet(saida / "base_integrada_maquina_dia.parquet", compression="zstd", index=False)

    disp = base["alvo_disponivel"] == 1
    print(f"Base integrada: {base['id_maquina'].nunique()} máquinas x {base['dia_ref'].nunique()} dias = {len(base)} linhas; "
          f"alvo em {disp.sum()} linhas ({base.loc[disp, 'alvo_falha_qualquer'].mean():.2%} com falha), "
          f"{base['alvo_incerto'].sum()} incertas. Salvo em {saida}")


if __name__ == "__main__":
    main()
