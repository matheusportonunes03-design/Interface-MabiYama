"""Tratamento da tabela de falhas (é o ALVO do modelo).

Colunas esperadas: id_maquina, data_hora, peca (as demais são mantidas como vieram).
Rodar:  python ETL/falhas_tratamento.py [--dados <pasta>]
"""
import pandas as pd

import comum as c

NOME = "falhas"
CHAVE_EVENTO = ["id_maquina", "data_hora", "peca"]


def tratar(bruto, reg, chaves_manutencao=None, hora_padrao=None):
    df = bruto.copy()
    reg.resumo["linhas_entrada"] = len(df)

    df["data_hora"] = c.converter_datas(df["data_hora"], reg, "data_hora")
    df["peca"] = df["peca"].map(c.padronizar_peca)
    reg.adicionar("peca fora do padrão", (bruto["peca"] != df["peca"]).sum(),
                  "padronizada (peca_A..peca_D)", "Mesma regra da tabela de manutenção, para cruzar por peça.")
    nao_rec = int((~df["peca"].isin(c.PECAS.values())).sum()
                  + (~df["id_maquina"].str.fullmatch(r"M\d{3}", na=False)).sum())
    reg.adicionar("Peça ou id_maquina fora do padrão", nao_rec, "mantidos como vieram (checagem)", "Esperado 0.")

    sem_chave = df["data_hora"].isna() | ~df["id_maquina"].str.fullmatch(r"M\d{3}", na=False) | df["peca"].isna()
    df = c.separar_rejeitados(df, sem_chave, reg, "data_hora, id_maquina ou peca válidos")

    dup = df.duplicated(keep="first")
    df = df[~dup].reset_index(drop=True)
    reg.adicionar("Duplicatas exatas", dup.sum(), "removidas (mantida a 1ª ocorrência)",
                  "Mesma falha lançada duas vezes duplicaria o rótulo positivo.")

    mesma_hora = df.duplicated(["id_maquina", "data_hora"], keep=False)
    reg.adicionar("Duas peças ou mais na mesma máquina e hora", int(df.loc[mesma_hora].groupby(
        ["id_maquina", "data_hora"]).ngroups), "mantidas",
        "É legítimo: o alvo é por peça, cada peça vira um rótulo próprio.")

    # ---- lançamentos suspeitos: fora do horário padrão E sem manutenção correspondente
    hora = df["data_hora"].dt.hour
    if hora.empty:
        for coluna in ("flag_horario_atipico", "flag_sem_manutencao", "flag_falha_suspeita"):
            df[coluna] = pd.Series(index=df.index, dtype="int8")
        reg.resumo["linhas_saida"] = 0
        return df
    modal = int(hora.mode().iloc[0]) if hora_padrao is None else hora_padrao
    df["flag_horario_atipico"] = (hora != modal).astype("int8")
    if chaves_manutencao is not None:
        sem_manut = ~c.marcar_presenca(df, chaves_manutencao)
        df["flag_sem_manutencao"] = sem_manut.astype("int8")
        df["flag_falha_suspeita"] = ((df["flag_horario_atipico"] == 1) & sem_manut).astype("int8")
        susp = df[df["flag_falha_suspeita"] == 1]
        instantes = susp.groupby("data_hora").size()
        detalhe = "; ".join(f"{t:%Y-%m-%d %H:%M} ({n} falhas)" for t, n in instantes.head(8).items())
        reg.adicionar("Falhas fora do horário padrão e sem manutenção correspondente", len(susp),
                      "mantidas na tabela com flag_falha_suspeita; EXCLUÍDAS do alvo na integração "
                      "(e o dia fica marcado alvo_incerto)",
                      f"O horário padrão de lançamento é {modal:02d}:00 e as falhas normais têm manutenção "
                      f"no mesmo instante. Estas não têm nenhuma e caem em poucos instantes ({detalhe or 'nenhum'}), "
                      "padrão de lançamento em lote errado, que ainda explicaria o pico do mês. "
                      "Não se remove da tabela porque a origem precisa ser confirmada com o cliente; "
                      "a decisão está num parâmetro da integração (ACAO_FALHA_SUSPEITA).")
    else:
        df["flag_sem_manutencao"] = 0
        df["flag_falha_suspeita"] = 0
        reg.adicionar("Cruzamento falha x manutenção", "não executado", "flags zeradas",
                      "manutencao.csv não foi encontrado em extraídos/.")

    ultima = df["data_hora"].max()
    reg.resumo["primeira_falha"] = str(df["data_hora"].min())
    reg.resumo["ultima_falha"] = str(ultima)
    reg.adicionar("Cobertura temporal das falhas", f"{df['data_hora'].min():%Y-%m-%d} a {ultima:%Y-%m-%d}",
                  "registrada (a integração só rotula os dias até a última falha)",
                  "Depois da última falha não se sabe se houve ou não falha. Tratar esses dias como "
                  "'sem falha' ensinaria negativos falsos ao modelo; por isso o alvo fica vazio neles.")

    reg.resumo["linhas_saida"] = len(df)
    return df.sort_values(["data_hora", "id_maquina", "peca"]).reset_index(drop=True)


def executar(pasta=None):
    entrada, saida = c.caminhos(pasta)
    reg = c.Registro(NOME)
    print(f"== {NOME}: lendo {entrada / (NOME + '.csv')}")
    df = tratar(c.ler_csv(entrada / f"{NOME}.csv"), reg, c.chaves_evento(entrada / "manutencao.csv"))
    c.salvar_csv(df, saida / f"{NOME}_corrigido.csv")
    reg.salvar(saida)
    print(f"Salvo {saida / (NOME + '_corrigido.csv')} ({len(df)} linhas)")
    return df


if __name__ == "__main__":
    executar(c.pasta_da_linha_de_comando())
