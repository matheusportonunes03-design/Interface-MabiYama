"""Trata um CSV novo, acrescenta suas linhas e atualiza a integração da frota."""

import argparse
import json
import shutil
from importlib import import_module
from pathlib import Path

import pandas as pd

import comum as c
import integracao

BASES = ("maquinas", "falhas", "manutencao", "erros", "operacao", "telemetria")
CHAVES = {
    "maquinas": ["id_maquina"],
    "falhas": ["id_maquina", "data_hora", "peca"],
    "operacao": ["id_maquina", "data", "turno"],
    "telemetria": ["id_maquina", "data_hora"],
}
EVENTO = ["id_maquina", "data_hora", "peca"]
INTEGRADA = "base_integrada_maquina_dia"
RELATORIO = "relatorio_qualidade.md"


def _tratar(base, bruto, historico, publicados, reg):
    modulo = import_module(f"{base}_tratamento")
    opcoes = {}
    if base in ("falhas", "manutencao"):
        outra = "manutencao" if base == "falhas" else "falhas"
        eventos = pd.read_parquet(publicados / f"{outra}_corrigido.parquet", columns=EVENTO)
        eventos["data_hora"] = c.para_datetime(eventos["data_hora"])
        opcoes[f"chaves_{outra}"] = eventos.dropna()
    if base == "falhas":
        normais = historico.loc[historico["flag_horario_atipico"].eq(0), "data_hora"]
        referencia = c.para_datetime(normais).dt.hour.mode()
        if not referencia.empty:
            opcoes["hora_padrao"] = int(referencia.iloc[0])
    if base == "erros":
        opcoes["horas_historicas"] = c.para_datetime(historico["data_hora"]).dt.hour
    if base == "telemetria":
        opcoes["preencher_grade"] = False
    tratadas = modulo.tratar(bruto, reg, **opcoes)
    return tratadas, getattr(modulo, "COLUNAS_DECIMAIS", {}) if base in ("manutencao", "telemetria") else {}


def _indice(tabela, colunas):
    valores = tabela[colunas].copy()
    for coluna in ("data", "data_hora"):
        if coluna in valores:
            valores[coluna] = c.para_datetime(valores[coluna])
    return pd.MultiIndex.from_frame(valores)


def _juntar(base, historico, novas):
    chaves = CHAVES.get(base)
    if chaves is None:
        chaves = [coluna for coluna in historico.columns
                  if coluna in novas and coluna != "tipo" and not coluna.startswith("flag_")]
    novas = novas.reindex(columns=historico.columns)
    for coluna, tipo in historico.select_dtypes(include="floating").dtypes.items():
        if pd.api.types.is_numeric_dtype(novas[coluna]):
            novas[coluna] = novas[coluna].astype(tipo)
    chaves_novas = _indice(novas, chaves)
    chaves_atuais = _indice(historico, chaves)
    lacunas = historico["flag_hora_faltante"].eq(1) if base == "telemetria" else pd.Series(False, index=historico.index)
    inserir = ~chaves_novas.isin(chaves_atuais[~lacunas]) & ~chaves_novas.duplicated()
    adicionadas = int(inserir.sum())
    preencher = lacunas & chaves_atuais.isin(chaves_novas[inserir])
    total = pd.concat([historico.loc[~preencher], novas.loc[inserir]], ignore_index=True)
    return total, adicionadas, int(preencher.sum())


def _parquet(tabela, destino):
    for coluna in tabela.select_dtypes(include="float64"):
        tabela[coluna] = tabela[coluna].astype("float32")
    tabela.to_parquet(destino, compression="zstd", index=False)


def _relatorio(anterior, novo, base, destino):
    secoes = anterior.read_text(encoding="utf-8").split("\n## ")
    atualizadas = dict(s.split("\n", 1) for s in novo.read_text(encoding="utf-8").split("\n## ")[1:])
    for titulo in (base, "integracao"):
        for indice, secao in enumerate(secoes[1:], start=1):
            if secao.split("\n", 1)[0] != titulo:
                continue
            previa = secao.split("\n### Último complemento", 1)[0].rstrip()
            secoes[indice] = (f"{previa}\n\n### Último complemento\n{atualizadas[titulo]}"
                              if titulo == base else f"{titulo}\n{atualizadas[titulo]}")
            break
        else:
            secoes.append(f"{titulo}\n{atualizadas[titulo]}")
    destino.write_text("\n## ".join(secoes), encoding="utf-8")


def executar(base: str, publicados: Path, trabalho: Path):
    entrada, tratados = c.caminhos(trabalho / "dados")
    destino = trabalho / "parquet"
    arquivo = f"{base}_corrigido"
    print(f"== {base}: tratando novas linhas")
    historico = pd.read_parquet(publicados / f"{arquivo}.parquet")
    bruto = c.ler_csv(entrada / f"{base}.csv")
    reg = c.Registro(base)
    novas, casas = _tratar(base, bruto, historico, publicados, reg)
    resumo = {"adicionadas": 0, "base": arquivo, "preenchidas": 0,
              "descartadas": 0 if reg.rejeitados is None else len(reg.rejeitados)}
    if not novas.empty:
        temporario = c.salvar_csv(novas, trabalho / "novas_tratadas.csv", decimais=casas)
        total, adicionadas, preenchidas = _juntar(base, historico, pd.read_csv(temporario, encoding="utf-8-sig"))
        resumo.update(adicionadas=adicionadas, preenchidas=preenchidas,
                      ignoradas=len(novas) - adicionadas, total=len(total))
    del historico, novas, bruto
    (trabalho / "resumo_complemento.json").write_text(json.dumps(resumo), encoding="utf-8")
    if not resumo["adicionadas"]:
        return

    destino.mkdir()
    reg.adicionar("Novas linhas tratadas incorporadas", resumo["adicionadas"], "incluídas na tabela existente",
                  f"{resumo['preenchidas']} preencheram lacunas e {resumo['ignoradas']} já tinham registro correspondente.")
    reg.resumo["linhas_saida"] = resumo["total"]
    reg.salvar(tratados)
    _parquet(total, destino / f"{arquivo}.parquet")
    c.salvar_csv(total, tratados / f"{arquivo}.csv")
    del total
    for outra in BASES:
        if outra == base:
            continue
        nome = f"{outra}_corrigido"
        original = publicados / f"{nome}.parquet"
        c.salvar_csv(pd.read_parquet(original), tratados / f"{nome}.csv")
        shutil.copyfile(original, destino / original.name)
    integracao.executar(trabalho / "dados", so_integrar=True)
    _parquet(pd.read_csv(tratados / f"{INTEGRADA}.csv", encoding="utf-8-sig"), destino / f"{INTEGRADA}.parquet")
    _relatorio(publicados / RELATORIO, tratados / RELATORIO, base, destino / RELATORIO)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", choices=BASES)
    parser.add_argument("publicados", type=Path)
    parser.add_argument("trabalho", type=Path)
    args = parser.parse_args()
    executar(args.base, args.publicados, args.trabalho)

