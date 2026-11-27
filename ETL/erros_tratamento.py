"""Tratamento da tabela de erros (alarmes dos equipamentos).

Rodar:  python ETL/erros_tratamento.py [--dados <pasta>]
"""
import re

import pandas as pd

import comum as c

NOME = "erros"
RAZAO_PICO = 3  # hora com mais de 3x a média das outras horas é considerada pico


def padronizar_codigo(valor):
    if pd.isna(valor):
        return valor
    achado = re.search(r"e\s*_?\s*([1-5])\b", str(valor), flags=re.IGNORECASE)
    return f"erro_E{achado.group(1)}" if achado else valor


def padronizar_severidade(valor):
    if pd.isna(valor):
        return valor
    s = c.so_letras(c.consertar_encoding(str(valor)))
    if s.startswith("bai"):
        return "baixa"
    if s.startswith("m") and s.endswith("dia"):
        return "media"
    if s.startswith("alt"):
        return "alta"
    return valor


def tratar(bruto, reg):
    df = bruto.copy()
    reg.resumo["linhas_entrada"] = len(df)

    df["tempo_reconhecimento_min"] = c.texto_para_inteiro(df["tempo_reconhecimento_min"])
    df["data_hora"] = c.converter_datas(df["data_hora"], reg, "data_hora")
    df["codigo_erro"] = df["codigo_erro"].apply(padronizar_codigo)
    df["severidade"] = df["severidade"].apply(padronizar_severidade)

    for col in ["codigo_erro", "severidade"]:
        mudou = bruto[col] != df[col]
        reg.adicionar(f"{col} fora do padrão", mudou.sum(), "padronizado (e encoding consertado)",
                      "Variações de caixa, acento, espaço e encoding quebrado do mesmo valor.")
    nao_rec = int((~df["codigo_erro"].str.fullmatch(r"erro_E[1-5]", na=False)).sum()
                  + (~df["severidade"].isin(["baixa", "media", "alta"])).sum())
    reg.adicionar("Valores não reconhecidos em codigo_erro/severidade", nao_rec,
                  "mantidos como vieram (checagem)", "Esperado 0 casos.")

    sem_chave = df["data_hora"].isna() | ~df["id_maquina"].str.fullmatch(r"M\d{3}", na=False)
    df = c.separar_rejeitados(df, sem_chave, reg, "data_hora válida ou id_maquina no padrão Mnnn")

    dup = df.duplicated(keep="first")
    df = df[~dup].reset_index(drop=True)
    reg.adicionar("Duplicatas exatas", dup.sum(), "removidas (mantida a 1ª ocorrência)",
                  "Linha idêntica em todas as colunas é o mesmo alarme lançado duas vezes e "
                  "inflaria qualquer contagem de erros.")

    # ---- pico de horário (provável horário padrão de lançamento)
    hora = df["data_hora"].dt.hour
    cont = hora.value_counts().sort_index()
    pico = int(cont.idxmax())
    media_outras = cont.drop(pico).mean()
    excesso = int(round(cont.max() - media_outras))
    df["flag_horario_pico"] = 0
    if cont.max() > RAZAO_PICO * media_outras:
        chaves = [k for k in ("id_maquina", "codigo_erro") if k in df.columns]
        dia = df["data_hora"].dt.normalize()
        no_pico = df[hora == pico].assign(_dia=dia)
        outros = df[hora != pico].assign(_dia=dia)[chaves + ["_dia"]].drop_duplicates()
        m = no_pico.merge(outros.assign(_g=1), on=chaves + ["_dia"], how="left")
        com_gemeo = int(m["_g"].notna().sum())
        df.loc[hora == pico, "flag_horario_pico"] = 1
        reg.adicionar(f"Pico de erros às {pico:02d}h", excesso,
                      "mantidos e marcados com flag_horario_pico; a integração conta esses erros à parte",
                      f"{int(cont.max())} erros às {pico:02d}h contra média de {media_outras:.0f} nas outras "
                      f"horas (~{excesso} a mais), compatível com horário padrão de lançamento. "
                      f"{com_gemeo} de {len(no_pico)} têm outro registro da mesma "
                      f"{'/'.join(chaves)} no mesmo dia em outra hora (cópia lançada de novo). "
                      "O horário exato desses erros não é informativo, então não entram na contagem "
                      "principal (n_erros); ficam em n_erros_pico para a modelagem testar.")
    else:
        reg.adicionar("Pico de erros em uma hora", 0, "nenhum pico encontrado", "Distribuição por hora sem pico.")

    vazios = int(df["tempo_reconhecimento_min"].isna().sum())
    reg.adicionar("tempo_reconhecimento_min vazio", vazios, "mantido vazio",
                  "Erro ainda não reconhecido ou sem registro; inventar um tempo criaria informação "
                  "falsa. Se o modelo precisar, imputar na modelagem (ajustado só no treino).")

    t = df["tempo_reconhecimento_min"].astype("float")
    q1, q3 = t.quantile([0.25, 0.75])
    lim = q3 + 1.5 * (q3 - q1)
    reg.adicionar("tempo_reconhecimento_min acima do limite IQR", int((t > lim).sum()),
                  "mantidos", f"Q1={q1:.0f}, Q3={q3:.0f}, limite={lim:.0f}, máximo={t.max():.0f} min. "
                  "Tempos longos são plausíveis (alarme esquecido) e não há evidência de erro.")

    reg.resumo["linhas_saida"] = len(df)
    return df.sort_values("data_hora").reset_index(drop=True)


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
