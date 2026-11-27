"""Tratamento do cadastro de máquinas.

A idade NÃO é mais recalculada com um ano de referência arbitrário: o cadastro traz a idade
em 2022 (idade + ano de instalação = 2022 em todas as máquinas que têm os dois dados). Aqui
só se recupera o que falta e se cria `ano_instalacao`; a idade de cada previsão
(data da previsão - data de instalação) é calculada na integração/modelagem.

Rodar:  python ETL/maquinas_tratamento.py [--dados <pasta>]
"""
import re

import pandas as pd

import comum as c

NOME = "maquinas"
TRIO = ["modelo", "fabricante", "pais_origem"]
ANO_REFERENCIA_CADASTRO = 2022  # ano em que a coluna `idade` foi levantada (conferido nos dados)


def padronizar_modelo(valor):
    if pd.isna(valor):
        return valor
    achado = re.search(r"modelo[\s_]*([a-d])\s*$", valor, flags=re.IGNORECASE)
    return f"modelo_{achado.group(1).upper()}" if achado else valor


def capitalizar(valor):
    return valor if pd.isna(valor) else valor.capitalize()


def padronizar_linha(valor):
    if pd.isna(valor):
        return valor
    achado = re.search(r"\d+", valor)
    return f"L{int(achado.group())}" if achado else valor


def aprender_correspondencia(df):
    """Modelo, fabricante e país são 1 para 1; se deixar de ser, o script para."""
    tabela = df.dropna(subset=TRIO)[TRIO].drop_duplicates()
    for col in TRIO:
        repetidos = tabela[col][tabela[col].duplicated()]
        if len(repetidos):
            raise ValueError(f"A relação não é 1 para 1: '{col}' = {repetidos.unique()} aparece com "
                             f"combinações diferentes:\n{tabela[tabela[col].isin(repetidos)]}")
    return tabela.reset_index(drop=True)


def preencher_trio(df, tabela):
    preenchidos = []
    for i, linha in df.iterrows():
        faltando = [col for col in TRIO if pd.isna(linha[col])]
        if not faltando:
            continue
        grupo = None
        for chave in TRIO:
            if pd.notna(linha[chave]):
                achou = tabela[tabela[chave] == linha[chave]]
                if len(achou) == 1:
                    grupo = achou.iloc[0]
                    break
        if grupo is None:
            continue
        for col in faltando:
            df.at[i, col] = grupo[col]
            preenchidos.append((linha["id_maquina"], col, grupo[col]))
    return df, preenchidos


def recuperar_idade(df, reg):
    idade = c.texto_para_inteiro(df["idade"])
    inst = c.converter_datas(df["data_instalacao"], reg, "data_instalacao")
    ano_data = inst.dt.year.astype("Int64")

    ambos = ano_data.notna() & idade.notna()
    soma = (idade + ano_data)[ambos]
    if (soma != ANO_REFERENCIA_CADASTRO).any():
        raise ValueError(f"idade + ano de instalação deveria ser {ANO_REFERENCIA_CADASTRO}; diverge em: "
                         f"{df.loc[ambos[ambos].index[(soma != ANO_REFERENCIA_CADASTRO).to_numpy()], 'id_maquina'].tolist()}. "
                         "Revisar o ano de referência do cadastro.")

    ano = ano_data.copy()
    do_idade = ano.isna() & idade.notna()
    ano[do_idade] = ANO_REFERENCIA_CADASTRO - idade[do_idade]
    idade_nova = idade.copy()
    recuperar = idade.isna() & ano.notna()
    idade_nova[recuperar] = ANO_REFERENCIA_CADASTRO - ano[recuperar]

    df["data_instalacao"] = inst
    df["ano_instalacao"] = ano
    df["idade"] = idade_nova
    df["flag_idade_recuperada"] = recuperar.fillna(False).astype("int8")
    df["flag_ano_instalacao_imputado"] = do_idade.fillna(False).astype("int8")
    df["flag_sem_idade_nem_data"] = ano.isna().astype("int8")

    reg.adicionar("idade vazia", int(idade.isna().sum()),
                  f"{int(recuperar.sum())} recuperadas ({ANO_REFERENCIA_CADASTRO} - ano de instalação) + "
                  f"flag_idade_recuperada; {int(ano.isna().sum())} continuam vazias com flag_sem_idade_nem_data",
                  f"idade + ano de instalação = {ANO_REFERENCIA_CADASTRO} em todas as {int(ambos.sum())} máquinas "
                  "que têm os dois dados (o script para se isso deixar de valer). As sem idade e sem data não "
                  "têm de onde recuperar.")
    reg.adicionar("data_instalacao vazia", int(inst.isna().sum()),
                  f"mantida vazia; ano recuperado da idade em {int(do_idade.sum())} (flag_ano_instalacao_imputado)",
                  "O ano é recuperável (referência - idade), o dia não. Na integração usa-se o meio do ano "
                  "(1º de julho), e a idade fica marcada como aproximada.")
    reg.adicionar("Idade com ano de referência arbitrário (2024)", 0,
                  f"não recalculada: a coluna fica na referência {ANO_REFERENCIA_CADASTRO}",
                  "A idade correta depende da data da previsão (data - data de instalação), calculada na "
                  "integração. Fixar um ano criaria uma idade que não vale para nenhuma data real.")
    return df


def tratar(bruto, reg):
    df = c.vazio_para_na(bruto.copy())
    reg.resumo["linhas_entrada"] = len(df)

    df["modelo"] = df["modelo"].map(padronizar_modelo)
    df["fabricante"] = df["fabricante"].map(capitalizar)
    df["pais_origem"] = df["pais_origem"].map(capitalizar)
    df["linha_producao"] = df["linha_producao"].map(padronizar_linha)
    for col in ["modelo", "fabricante", "pais_origem", "linha_producao"]:
        antes = c.vazio_para_na(bruto[[col]])[col]
        reg.adicionar(f"{col} fora do padrão", (antes.notna() & (antes != df[col])).sum(), "padronizado",
                      "Variações de caixa, espaço e formato.")

    if df["id_maquina"].duplicated().any():
        raise ValueError("id_maquina duplicado no cadastro")
    reg.adicionar("Máquinas distintas no cadastro", df["id_maquina"].nunique(), "registrado",
                  "A proposta do projeto cita 100 máquinas; a base tem esta quantidade.")

    tabela = aprender_correspondencia(df)
    antes_trio = df[TRIO].isna()
    df, preenchidos = preencher_trio(df, tabela)
    df["flag_trio_preenchido"] = (antes_trio & df[TRIO].notna()).any(axis=1).astype("int8")
    reg.adicionar("modelo/fabricante/país vazios", int(antes_trio.sum().sum()),
                  f"{len(preenchidos)} células preenchidas pela correspondência 1 para 1 + flag_trio_preenchido",
                  "Cada modelo tem um único fabricante e país (e vice-versa), então um dado conhecido define os "
                  f"outros sem ambiguidade. Vazios restantes: {int(df[TRIO].isna().sum().sum())}. Correspondência: "
                  + "; ".join(f"{r.modelo}={r.fabricante}/{r.pais_origem}" for r in tabela.sort_values("modelo").itertuples()))

    for col in ["capacidade_nominal_h", "potencia_kw"]:
        df[col] = c.texto_para_float(df[col])

    df = recuperar_idade(df, reg)
    # `modelo` continua como texto: dummies são passo da modelagem (Pipeline), não da limpeza
    reg.resumo["linhas_saida"] = len(df)
    return df


def executar(pasta=None):
    entrada, saida = c.caminhos(pasta)
    reg = c.Registro(NOME)
    print(f"== {NOME}: lendo {entrada / (NOME + '.csv')}")
    df = tratar(c.ler_csv(entrada / f"{NOME}.csv"), reg)
    c.salvar_csv(df, saida / f"{NOME}_corrigido.csv")
    reg.salvar(saida)
    print(f"Salvo {saida / (NOME + '_corrigido.csv')} ({len(df)} linhas)")
    return df


if __name__ == "__main__":
    executar(c.pasta_da_linha_de_comando())
