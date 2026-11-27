"""Tratamento da operação (máquina x dia x turno).

Rodar:  python ETL/operacao_tratamento.py [--dados <pasta>]
"""
import pandas as pd

import comum as c

NOME = "operacao"
COLUNAS_INTEIRAS = ["pecas_produzidas", "meta_producao", "pecas_defeituosas", "qtd_operadores", "tempo_setup_min"]
COLUNAS_DECIMAIS = ["consumo_energia_kwh", "utilizacao_pct", "ind_quebra", "score_saude"]  # 1 casa decimal
VALIDOS = {"turno": ["manha", "tarde", "noite"], "hora_extra": ["nao", "sim"],
           "classe_risco": ["baixo", "medio", "alto"]}
# regra do dicionário: ind_quebra <= 40 baixo; <= 70 médio; > 70 alto
LIMITES_RISCO = (40, 70)


def padronizar_categoria(valor, validos):
    if pd.isna(valor):
        return valor
    s = c.so_letras(valor)
    return s if s in validos else valor


def classe_esperada(ind_quebra):
    esperada = pd.Series(pd.NA, index=ind_quebra.index, dtype="object")
    esperada[ind_quebra <= LIMITES_RISCO[0]] = "baixo"
    esperada[(ind_quebra > LIMITES_RISCO[0]) & (ind_quebra <= LIMITES_RISCO[1])] = "medio"
    esperada[ind_quebra > LIMITES_RISCO[1]] = "alto"
    return esperada


def tratar(bruto, reg):
    df = bruto.copy()
    reg.resumo["linhas_entrada"] = len(df)

    for col in COLUNAS_INTEIRAS:
        df[col] = c.texto_para_inteiro(df[col])
    for col in COLUNAS_DECIMAIS:
        df[col] = c.texto_para_decimal(df[col], 1)
    df["data"] = c.converter_datas(df["data"], reg, "data")
    for col, validos in VALIDOS.items():
        df[col] = df[col].apply(padronizar_categoria, validos=validos)
        reg.adicionar(f"{col} fora do padrão", (bruto[col] != df[col]).sum(), "padronizado",
                      "Variações de caixa e acento.")
    for col in COLUNAS_DECIMAIS:
        reg.adicionar(f"{col} com vírgula decimal", bruto[col].str.contains(",", regex=False).sum(),
                      "convertida para ponto", "Formato brasileiro para número.")

    nao_rec = {col: ~df[col].isin(v) for col, v in VALIDOS.items()}
    nao_rec["id_maquina"] = ~df["id_maquina"].str.fullmatch(r"M\d{3}", na=False)
    nao_rec["operador"] = ~df["operador"].str.fullmatch(r"OP\d{2}", na=False)
    nao_rec["produto_fabricado"] = ~df["produto_fabricado"].str.fullmatch(r"PRD-\d{3}", na=False)
    reg.adicionar("Valores fora do padrão (turno, hora_extra, classe_risco, ids)",
                  sum(int((m & df[k].notna()).sum()) for k, m in nao_rec.items()),
                  "mantidos como vieram (checagem)", "Esperado 0 casos.")

    df = c.separar_rejeitados(df, df["data"].isna() | df["id_maquina"].isna(), reg, "data ou id_maquina válidos")

    dup = df.duplicated(keep="first")
    df = df[~dup].reset_index(drop=True)
    reg.adicionar("Duplicatas exatas", dup.sum(), "removidas", "Mesmo turno lançado duas vezes.")
    reg.adicionar("Mesma máquina/data/turno repetida", df.duplicated(["id_maquina", "data", "turno"]).sum(),
                  "mantidas (checagem)", "Esperado 0 casos.")
    n_esperadas = df["id_maquina"].nunique() * df["data"].nunique() * df["turno"].nunique()
    reg.adicionar("Linhas faltando na grade máquina x dia x turno",
                  n_esperadas - len(df.drop_duplicates(["id_maquina", "data", "turno"])),
                  "mantidas (checagem)", "Esperado 0 casos (grade completa).")

    # ---- meta_producao vazia: igual nos 3 turnos do mesmo máquina/dia
    g = df.groupby(["id_maquina", "data"])["meta_producao"]
    distintos = g.transform("nunique")
    conflito = int((distintos > 1).sum())
    valor = g.transform("max")
    preencher = df["meta_producao"].isna() & valor.notna() & (distintos <= 1)
    vazias_antes = int(df["meta_producao"].isna().sum())
    df["flag_meta_imputada"] = preencher.astype("int8")
    df.loc[preencher, "meta_producao"] = valor[preencher]
    reg.adicionar("meta_producao vazia", vazias_antes,
                  f"{int(preencher.sum())} recuperadas pelo valor dos outros turnos do dia + flag_meta_imputada; "
                  f"{vazias_antes - int(preencher.sum())} continuam vazias",
                  f"A meta é igual nos turnos da mesma máquina e dia ({conflito} conflitos), então copiar não "
                  "inventa informação. As que continuam vazias não têm nenhum turno do dia com meta.")

    # ---- classe_risco é derivada de ind_quebra: recalcular pela regra do dicionário
    esperada = classe_esperada(df["ind_quebra"])
    mudar = esperada.notna() & (df["classe_risco"].isna() | (df["classe_risco"] != esperada))
    df["flag_classe_risco_recalculada"] = mudar.astype("int8")
    df.loc[mudar, "classe_risco"] = esperada[mudar]
    reg.adicionar("classe_risco diferente da regra do dicionário (ind_quebra)", int(mudar.sum()),
                  "recalculada pela regra (<=40 baixo, <=70 médio, >70 alto) + flag_classe_risco_recalculada",
                  "A coluna é derivada do índice; manter valor divergente criaria duas fontes de verdade.")

    for col in ["utilizacao_pct", "ind_quebra", "score_saude"]:
        reg.adicionar(f"{col} fora de 0-100", int(((df[col] < 0) | (df[col] > 100)).sum()),
                      "mantidos (checagem)", "Esperado 0 casos.")
    reg.adicionar("pecas_defeituosas maior que pecas_produzidas",
                  int((df["pecas_defeituosas"] > df["pecas_produzidas"]).sum()), "mantidas (checagem)",
                  "Esperado 0 casos; se houver, conferir com o cliente.")
    for col, n in df.isna().sum().items():
        if n and col != "meta_producao":
            reg.adicionar(f"{col} vazio", int(n), "mantido vazio",
                          "Sem informação para recuperar; imputar, se preciso, na modelagem (só no treino).")

    df["data"] = df["data"].dt.normalize()
    df["hora_extra"] = df["hora_extra"].map({"sim": 1, "nao": 0}).astype("Int64")  # 1 = sim, 0 = não
    reg.resumo["linhas_saida"] = len(df)
    return df.sort_values(["data", "id_maquina", "turno"]).reset_index(drop=True)


def executar(pasta=None):
    entrada, saida = c.caminhos(pasta)
    reg = c.Registro(NOME)
    print(f"== {NOME}: lendo {entrada / (NOME + '.csv')}")
    df = tratar(c.ler_csv(entrada / f"{NOME}.csv"), reg)
    c.salvar_csv(df, saida / f"{NOME}_corrigido.csv", decimais={k: 1 for k in COLUNAS_DECIMAIS})
    reg.salvar(saida)
    print(f"Salvo {saida / (NOME + '_corrigido.csv')} ({len(df)} linhas)")
    return df


if __name__ == "__main__":
    executar(c.pasta_da_linha_de_comando())
