"""Prepara o calendário e as variáveis auxiliares do m07 com os Parquets tratados."""

from pathlib import Path

import pandas as pd

PECAS = [f"peca_{p}" for p in "ABCD"]
CHAVE = ["id_maquina", "dia_ref"]
EXTRAS = ["op_utilizacao_pct_media", "op_consumo_energia_kwh", "op_hora_extra", "op_taxa_defeito",
          "op_pct_meta", "op_qtd_operadores_media", "op_tempo_setup_min", "op_n_turnos",
          "temp_ambiente_c_media", "umidade_relativa_media"]
ENTRADAS = ("base_integrada_maquina_dia", "telemetria_corrigido", "erros_corrigido", "falhas_corrigido",
            "manutencao_corrigido", "maquinas_corrigido")
HORA_CORTE = pd.Timedelta(hours=5)


def _juntar_evento(base, eventos, chave, valor):
    eventos = eventos.dropna(subset=[*chave, "data_hora", valor])
    return pd.merge_asof(base.sort_values("corte"), eventos[[*chave, "data_hora", valor]].sort_values("data_hora"),
                         by=chave, left_on="corte", right_on="data_hora").drop(columns="data_hora")


def _extras(base, manut, erros):
    formato = base[[*CHAVE, *EXTRAS]].merge(pd.DataFrame({"peca": PECAS}), how="cross")
    formato["corte"] = formato["dia_ref"] + HORA_CORTE
    formato = _juntar_evento(formato, erros, ["id_maquina"], "versao_firmware")
    manut = manut.rename(columns={"fornecedor_peca": "fornecedor_peca_atual"})
    formato = _juntar_evento(formato, manut, ["id_maquina", "peca"], "fornecedor_peca_atual")
    return formato.drop(columns="corte")


def preparar(publicados: Path, temporaria: Path):
    """Exporta as entradas do notebook e calcula a janela de previsão e os rótulos utilizáveis."""
    ultimo = None
    maquinas = set()
    for nome in ENTRADAS:
        dados = pd.read_parquet(publicados / f"{nome}.parquet")
        for coluna in {"data_hora", "dia_ref"} & set(dados):
            dados[coluna] = pd.to_datetime(dados[coluna], format="ISO8601", errors="coerce").astype("datetime64[ns]")
        dados.to_csv(temporaria / f"{nome}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
        if nome == "telemetria_corrigido":
            observadas = dados.loc[dados["flag_hora_faltante"].eq(0), ["id_maquina", "data_hora"]]
            ultima_leitura = observadas["data_hora"].max()
            if pd.isna(ultima_leitura):
                raise ValueError("A base de telemetria não tem leituras com data válida.")
            ultimo = (ultima_leitura - HORA_CORTE).normalize()
            maquinas = set(observadas["id_maquina"].dropna())
            del observadas
        del dados

    base = pd.read_csv(temporaria / "base_integrada_maquina_dia.csv", parse_dates=["dia_ref"])
    base["dia_ref"] = base["dia_ref"].astype("datetime64[ns]")
    base = base[base["id_maquina"].isin(maquinas) & base["dia_ref"].le(ultimo)].copy()
    if base.empty:
        raise ValueError("As bases precisam ter telemetria observada até pelo menos um corte das 05h.")

    falhas = pd.read_csv(temporaria / "falhas_corrigido.csv", parse_dates=["data_hora"])
    falhas = falhas.dropna(subset=["data_hora", "id_maquina", "peca"])
    if falhas.empty:
        raise ValueError("A previsão m07 requer histórico de falhas rotuladas.")
    # A receita do notebook associa a falha do dia D+1 à previsão do dia D.
    falhas["dia_ref"] = falhas["data_hora"].dt.normalize().astype("datetime64[ns]") - pd.Timedelta(days=1)
    primeiro_dia = min(ultimo, falhas["dia_ref"].max() + pd.Timedelta(days=1))
    historico = base.loc[base["dia_ref"].lt(primeiro_dia - pd.Timedelta(days=1)), CHAVE]
    suspeitas = falhas.loc[falhas["flag_falha_suspeita"].eq(1), CHAVE].drop_duplicates()
    conhecidas = historico.merge(suspeitas, on=CHAVE, how="left", indicator=True)
    grade = conhecidas.loc[conhecidas["_merge"].eq("left_only"), CHAVE].merge(pd.DataFrame({"peca": PECAS}), how="cross")
    positivas = falhas.loc[falhas["flag_falha_suspeita"].eq(0), [*CHAVE, "peca"]]
    indice = pd.MultiIndex.from_frame(grade)
    rotulos = pd.Series(indice.isin(pd.MultiIndex.from_frame(positivas)).astype(int), index=indice)
    if not rotulos.any():
        raise ValueError("As bases precisam conter histórico de falhas rotuladas antes do início da previsão.")

    manut = pd.read_csv(temporaria / "manutencao_corrigido.csv", parse_dates=["data_hora"])
    erros = pd.read_csv(temporaria / "erros_corrigido.csv", parse_dates=["data_hora"])
    manut["data_hora"] = manut["data_hora"].astype("datetime64[ns]")
    erros["data_hora"] = erros["data_hora"].astype("datetime64[ns]")
    _extras(base, manut, erros).to_csv(temporaria / "base_modelagem.csv", index=False, date_format="%Y-%m-%d")

    previsao = base[base["dia_ref"].ge(primeiro_dia)].sort_values(CHAVE)
    ids = previsao["id_maquina"] + "_" + previsao["dia_ref"].dt.strftime("%Y-%m-%d")
    if ids.empty or ids.duplicated().any():
        raise ValueError("A base integrada precisa ter uma linha por máquina e dia na janela de previsão.")
    ids.to_csv(temporaria / "ids_previsao.csv", index=False, header=["id"])
    ultimo_dia = previsao["dia_ref"].max()
    return pd.date_range(base["dia_ref"].min(), ultimo_dia), primeiro_dia, ultimo_dia, rotulos

