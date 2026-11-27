"""Tratamento da tabela de manutenção (trocas de peça).

Novidade: coluna `tipo` (corretiva/preventiva). Corretiva = coincide (máquina, hora, peça)
com uma falha. Separar as duas permite medir a idade da peça pelo calendário (só preventivas)
e, à parte, o tempo desde qualquer troca.
Rodar:  python ETL/manutencao_tratamento.py [--dados <pasta>]
"""
import pandas as pd

import comum as c

NOME = "manutencao"
COLUNAS_INTEIRAS = ["duracao_min"]
COLUNAS_DECIMAIS = {"custo_troca_reais": 2}  # coluna -> casas decimais

FORNECEDORES = {"metalparts": "MetalParts", "rolatec": "Rolatec", "rolatecltda": "Rolatec", "usimec": "Usimec"}
PREFIXO_LOTE = {"M": "MetalParts", "R": "Rolatec", "U": "Usimec"}  # letra do lote -> fornecedor


def tratar(bruto, reg, chaves_falhas=None):
    df = c.vazio_para_na(bruto.copy())
    reg.resumo["linhas_entrada"] = len(df)

    df["data_hora"] = c.converter_datas(df["data_hora"], reg, "data_hora")
    for col in COLUNAS_INTEIRAS:
        df[col] = c.texto_para_inteiro(df[col])
    for col, casas in COLUNAS_DECIMAIS.items():
        df[col] = c.texto_para_decimal(df[col], casas)
    df["peca"] = df["peca"].map(c.padronizar_peca)
    df["fornecedor_peca"] = df["fornecedor_peca"].map(lambda v: c.padronizar_categoria(v, FORNECEDORES))

    for col in ["peca", "fornecedor_peca"]:
        mudou = bruto[col].str.strip().ne(df[col]) & bruto[col].ne("")
        reg.adicionar(f"{col} fora do padrão", mudou.sum(), "padronizado", "Variações de caixa, acento e sufixo.")
    for col in list(COLUNAS_DECIMAIS) + COLUNAS_INTEIRAS:
        reg.adicionar(f"{col} com vírgula decimal", bruto[col].str.contains(",", regex=False).sum(),
                      "convertida para ponto", "Formato brasileiro para número.")

    inval = {
        "id_maquina": ~df["id_maquina"].str.fullmatch(r"M\d{3}", na=False),
        "tecnico": ~df["tecnico"].str.fullmatch(r"T\d{2}", na=False),
        "lote_peca": ~df["lote_peca"].str.fullmatch(r"L\d{4}-[A-Z]\d{3}", na=False),
        "peca": ~df["peca"].isin(c.PECAS.values()),
        "fornecedor_peca": ~df["fornecedor_peca"].isin(set(FORNECEDORES.values())),
    }
    reg.adicionar("Valores fora do padrão (id_maquina, tecnico, lote_peca, peca, fornecedor)",
                  sum(int(m.sum()) for m in inval.values()), "mantidos como vieram (checagem)",
                  "Esperado 0 casos. " + ", ".join(f"{k}={int(m.sum())}" for k, m in inval.items()))

    df = c.separar_rejeitados(df, df["data_hora"].isna() | df["id_maquina"].isna() | df["peca"].isna(),
                              reg, "data_hora, id_maquina ou peca")

    for col in df.columns:
        n = int(df[col].isna().sum())
        if n:
            reg.adicionar(f"{col} vazio", n, "mantido vazio",
                          "Sem informação para recuperar; imputar, se preciso, na modelagem (só no treino).")

    dup = df.duplicated(keep="first")
    df = df[~dup].reset_index(drop=True)
    reg.adicionar("Duplicatas exatas", dup.sum(), "removidas", "Mesma troca lançada duas vezes.")
    reg.adicionar("Mesma máquina/data_hora/peça repetida", df.duplicated(["id_maquina", "data_hora", "peca"]).sum(),
                  "mantidas (checagem)", "Esperado 0 casos.")
    reg.adicionar("lote_peca repetido em mais de uma linha", df.duplicated(["lote_peca"], keep=False).sum(),
                  "mantidos (checagem)", "Um lote pode ser usado em mais de uma troca.")
    reg.adicionar("duracao_min <= 0 ou custo_troca_reais <= 0",
                  int((df["duracao_min"] <= 0).sum() + (df["custo_troca_reais"] <= 0).sum()),
                  "mantidos (checagem)", "Esperado 0 casos.")

    letra = df["lote_peca"].str.extract(r"^L\d{4}-([A-Z])")[0]
    esperado = letra.map(PREFIXO_LOTE)
    div_forn = (esperado.notna() & df["fornecedor_peca"].notna() & (esperado != df["fornecedor_peca"])).sum()
    aamm = df["lote_peca"].str.extract(r"^L(\d{4})-")[0]
    data_aamm = df["data_hora"].dt.strftime("%y%m")
    div_data = (aamm.notna() & data_aamm.notna() & (aamm != data_aamm)).sum()
    reg.adicionar("Fornecedor diferente da letra do lote / AAMM do lote diferente da data", int(div_forn + div_data),
                  "mantidos (checagem)", f"fornecedor x letra: {div_forn}; AAMM x data: {div_data}. Esperado 0.")

    # ---- corretiva x preventiva
    if chaves_falhas is not None:
        corretiva = c.marcar_presenca(df, chaves_falhas)
        df["tipo"] = pd.Series(corretiva, index=df.index).map({True: "corretiva", False: "preventiva"})
        reg.adicionar("Manutenção corretiva x preventiva sem marcação", int(corretiva.sum()),
                      "coluna tipo criada (corretiva = coincide máquina/hora/peça com uma falha)",
                      f"{int(corretiva.sum())} de {len(df)} trocas coincidem com falha. A corretiva é "
                      "consequência da falha, não do calendário: misturar as duas confunde a idade da peça "
                      "pelo calendário (dias_desde_prev) com o histórico de falhas. A integração gera as duas "
                      "contagens (dias_desde_prev e dias_desde_troca), sempre com o corte das 05:00.")
    else:
        df["tipo"] = pd.NA
        reg.adicionar("Corretiva x preventiva", "não executado", "tipo vazio",
                      "falhas.csv não foi encontrado em extraídos/.")

    # ---- intervalos entre trocas PREVENTIVAS (informativo). As corretivas caem no dia da falha,
    # em qualquer data, e baixariam a porcentagem sem dizer nada sobre o calendário.
    d = df[df["tipo"] != "corretiva"].sort_values(["id_maquina", "peca", "data_hora"])
    dias = d.groupby(["id_maquina", "peca"])["data_hora"].transform(lambda s: s.dt.normalize().diff().dt.days)
    dias = dias.dropna()
    if len(dias):
        pct = 100 * (dias % 15 == 0).mean()
        reg.adicionar("Intervalo entre trocas preventivas da mesma peça (múltiplo de 15 dias)",
                      int((dias % 15 == 0).sum()), "informativo",
                      f"{pct:.1f}% dos {len(dias)} intervalos entre preventivas são múltiplos de 15 dias, o que "
                      "confirma manutenção por calendário (útil na EDA).")

    q = df["custo_troca_reais"]
    lim = q.quantile(.75) + 1.5 * (q.quantile(.75) - q.quantile(.25))
    reg.adicionar("custo_troca_reais acima do limite IQR", int((q > lim).sum()), "mantidos",
                  f"Limite {lim:.1f}. Peças diferentes têm custos diferentes; sem evidência de erro.")

    reg.resumo["linhas_saida"] = len(df)
    # peca continua como TEXTO: o cruzamento com falhas é por peça (dummies são passo da modelagem)
    return df.sort_values("data_hora").reset_index(drop=True)


def executar(pasta=None):
    entrada, saida = c.caminhos(pasta)
    reg = c.Registro(NOME)
    print(f"== {NOME}: lendo {entrada / (NOME + '.csv')}")
    df = tratar(c.ler_csv(entrada / f"{NOME}.csv"), reg, c.chaves_evento(entrada / "falhas.csv"))
    c.salvar_csv(df, saida / f"{NOME}_corrigido.csv", decimais=COLUNAS_DECIMAIS)
    reg.salvar(saida)
    print(f"Salvo {saida / (NOME + '_corrigido.csv')} ({len(df)} linhas)")
    return df


if __name__ == "__main__":
    executar(c.pasta_da_linha_de_comando())
