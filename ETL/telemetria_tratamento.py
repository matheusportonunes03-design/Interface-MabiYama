"""Tratamento da telemetria (máquina x hora).

Ordem das regras (importa): formatos -> duplicatas exatas -> -999 -> sinal -> zeros ->
escala (M017 e afins, por regra) -> sensor_b <-> sensor_b_aux -> conflitos -> grade horária.
Cada tratamento que altera valor deixa uma coluna flag_<problema> (0/1).
Rodar:  python ETL/telemetria_tratamento.py [--dados <pasta>]
"""
import numpy as np
import pandas as pd

import comum as c

NOME = "telemetria"
CHAVE = ["id_maquina", "data_hora"]

SENTINELA = -999  # valor usado no lugar de "sem leitura"

# coluna -> casas decimais (conforme o dicionário de dados)
COLUNAS_DECIMAIS = {
    "sensor_a": 3, "sensor_b": 3, "sensor_c": 3, "sensor_d": 3,
    "temp_ambiente_c": 1, "sensor_b_aux": 2, "vibracao_mm_s": 2,
}
SENSORES = ["sensor_a", "sensor_b", "sensor_c", "sensor_d"]
VALIDOS_QUALIDADE = ["ok", "suspeita"]

# Erro de escala (valor ~10x maior): detectado por regra, sem citar máquina no código.
SENSORES_ESCALA = ["sensor_a"]
FATOR_ESCALA = 10
JANELA_ESCALA = 24                # horas (linhas) da janela móvel centrada
RAZAO_CANDIDATO = (6, 16)         # valor / mediana da máquina para ser "candidato"
RAZAO_ANOMALO = (4, 20)           # faixa aceita para a própria linha
FRACAO_JANELA = 0.3               # fração de candidatos na janela para confirmar
FRACAO_MAX_POR_MAQUINA = 0.4      # acima disso a mediana da máquina não é confiável

# sensor_b (rpm) = sensor_b_aux (rad/s) x 60 / 2π
K_RAD_S_RPM = 60 / (2 * np.pi)
TOLERANCIA_K = 0.01               # desvio relativo máximo aceito da razão observada

FLAGS = (["flag_sentinela_999", "flag_sinal_corrigido", "flag_zero_sensor"]
         + [f"flag_escala_{s}" for s in SENSORES_ESCALA]
         + ["flag_sensor_b_recuperado", "flag_sensor_b_aux_recuperado", "flag_suspeita"])


def padronizar_qualidade(valor):
    if pd.isna(valor):
        return valor
    s = c.so_letras(valor)
    return s if s in VALIDOS_QUALIDADE else valor


def janelas_afetadas(df, mascara, folga_dias=7, limite=12):
    """Resumo textual: máquina, período (início→fim) e nº de linhas de cada janela."""
    sub = df.loc[mascara, ["id_maquina", "data_hora"]].sort_values(CHAVE)
    saida = []
    for maq, g in sub.groupby("id_maquina"):
        t = g["data_hora"].reset_index(drop=True)
        novo = t.diff() > pd.Timedelta(days=folga_dias)
        for _, seg in t.groupby(novo.cumsum()):
            saida.append(f"{maq}: {seg.min():%Y-%m-%d} a {seg.max():%Y-%m-%d} ({len(seg)} linhas)")
    return saida[:limite]


def detectar_escala(df, coluna):
    """Máscara das linhas ~10x maiores que o normal da própria máquina, de forma sustentada."""
    x = df[coluna]
    base = x.groupby(df["id_maquina"]).transform("median")
    razao = x / base.where(base > 0)
    candidato = razao.between(*RAZAO_CANDIDATO).astype(float)
    ordem = df.sort_values(CHAVE).index
    frac = (candidato.loc[ordem]
            .groupby(df.loc[ordem, "id_maquina"])
            .transform(lambda s: s.rolling(JANELA_ESCALA, center=True,
                                           min_periods=JANELA_ESCALA // 2).mean())
            .reindex(df.index))
    return razao.between(*RAZAO_ANOMALO) & (frac >= FRACAO_JANELA)


def _qualidade_pior(s):
    if (s == "suspeita").any():
        return "suspeita"
    s = s.dropna()
    return s.iloc[0] if len(s) else pd.NA


def tratar(bruto, reg):
    df = bruto.copy()
    reg.resumo["linhas_entrada"] = len(df)

    # ---- 1. formatos
    dois_sep = sum(int(c.contar_dois_separadores(df[col]).sum()) for col in COLUNAS_DECIMAIS)
    df["data_hora"] = c.converter_datas(df["data_hora"], reg, "data_hora")
    for col, casas in COLUNAS_DECIMAIS.items():
        df[col] = c.texto_para_decimal(df[col], casas)
    df["umidade_relativa"] = c.texto_para_inteiro(df["umidade_relativa"])
    df["qualidade_leitura"] = df["qualidade_leitura"].apply(padronizar_qualidade)
    df["qualidade_leitura"] = df["qualidade_leitura"].where(df["qualidade_leitura"] != "", pd.NA)
    reg.adicionar("Números com dois separadores (ex.: 1,736,809)", dois_sep,
                  "convertidos: o último separador é o decimal, os anteriores são milhar",
                  "O parser antigo trocava toda vírgula por ponto ('1.736.809'), que não é número, "
                  "e o valor virava vazio. A conversão agora é conferida pela razão "
                  "sensor_b/sensor_b_aux (regra rpm = rad/s x 60/2π).")

    # ---- 2. linhas sem chave utilizável
    invalidas = df["data_hora"].isna() | ~df["id_maquina"].str.fullmatch(r"M\d{3}", na=False)
    df = c.separar_rejeitados(df, invalidas, reg, "data_hora válida ou id_maquina no padrão Mnnn")

    fora_da_hora = (df["data_hora"].dt.minute != 0) | (df["data_hora"].dt.second != 0)
    if fora_da_hora.any():
        df["data_hora"] = df["data_hora"].dt.floor("h")
    reg.adicionar("Timestamps fora da hora cheia", fora_da_hora.sum(),
                  "arredondados para baixo (hora cheia)",
                  "A série é horária; a grade completa exige hora cheia.")

    # ---- 3. duplicatas exatas
    dup = df.duplicated(keep="first")
    df = df[~dup].reset_index(drop=True)
    reg.adicionar("Duplicatas exatas", dup.sum(), "removidas (mantida a 1ª ocorrência)",
                  "Linha idêntica em todas as colunas é o mesmo registro lançado duas vezes.")

    # ---- 4. -999 (sem leitura) -> vazio
    sent = df[SENSORES] == SENTINELA
    outras = [col for col in COLUNAS_DECIMAIS if col not in SENSORES]
    fora_dos_sensores = int((df[outras] == SENTINELA).sum().sum())
    df["flag_sentinela_999"] = sent.any(axis=1).astype("int8")
    df[SENSORES] = df[SENSORES].mask(sent)
    reg.adicionar(f"Valor {SENTINELA} (sem leitura) nos sensores", int(sent.sum().sum()),
                  "convertido para vazio + flag_sentinela_999",
                  f"-999 é código de 'sem leitura', não medida. Fora dos sensores: {fora_dos_sensores} ocorrências.")

    # ---- 5. sensores negativos -> valor absoluto
    neg = df[SENSORES] < 0
    evidencia = []
    for s in SENSORES:
        n, p = df.loc[neg[s], s].abs(), df.loc[df[s] > 0, s]
        if len(n) and len(p):
            evidencia.append(f"{s}: mediana |neg|={n.median():.1f} vs pos={p.median():.1f}; "
                             f"P5-P95 |neg|={n.quantile(.05):.1f}-{n.quantile(.95):.1f} "
                             f"vs pos={p.quantile(.05):.1f}-{p.quantile(.95):.1f}")
    df["flag_sinal_corrigido"] = neg.any(axis=1).astype("int8")
    df[SENSORES] = df[SENSORES].abs()
    reg.adicionar("Sensores com sinal negativo", int(neg.sum().sum()),
                  "valor absoluto + flag_sinal_corrigido",
                  "Em módulo, os negativos caem na mesma faixa dos positivos (erro de sinal, não "
                  "leitura nova). " + " | ".join(evidencia))

    # ---- 6. zeros nos sensores -> vazio
    zero = df[SENSORES] == 0
    linhas_zero = zero.any(axis=1)
    duas = int((zero.sum(axis=1) >= 2).sum())
    susp = int((df.loc[linhas_zero, "qualidade_leitura"] == "suspeita").sum())
    df["flag_zero_sensor"] = linhas_zero.astype("int8")
    df[SENSORES] = df[SENSORES].mask(zero)
    reg.adicionar("Zeros nos sensores", int(zero.sum().sum()),
                  "convertidos para vazio + flag_zero_sensor",
                  f"{int(linhas_zero.sum())} linhas; {duas} com 2+ sensores zerados na mesma linha "
                  f"(se quase nunca há, é falha do sensor e não máquina parada); {susp} dessas "
                  "linhas já vinham como 'suspeita'. Zero real puxaria as médias para baixo.")

    # ---- 7. erro de escala (~10x) por regra
    for col in SENSORES_ESCALA:
        mask = detectar_escala(df, col)
        por_maq = mask.groupby(df["id_maquina"]).mean()
        inseguras = por_maq[por_maq > FRACAO_MAX_POR_MAQUINA].index.tolist()
        if inseguras:
            mask &= ~df["id_maquina"].isin(inseguras)
        df[f"flag_escala_{col}"] = mask.astype("int8")
        df.loc[mask, col] = (df.loc[mask, col] / FATOR_ESCALA).round(COLUNAS_DECIMAIS[col])
        janelas = janelas_afetadas(df, mask)
        reg.adicionar(f"{col} ~{FATOR_ESCALA}x maior que o normal da máquina", mask.sum(),
                      f"dividido por {FATOR_ESCALA} + flag_escala_{col}",
                      "Detectado por regra (valor / mediana da máquina entre "
                      f"{RAZAO_CANDIDATO[0]} e {RAZAO_CANDIDATO[1]}, sustentado numa janela de "
                      f"{JANELA_ESCALA} h), sem citar máquina no código. Janelas: "
                      + ("; ".join(janelas) or "nenhuma")
                      + (f". NÃO corrigidas por mediana pouco confiável: {inseguras}" if inseguras else ""))

    # ---- 8. sensor_b <-> sensor_b_aux
    b, aux = df["sensor_b"], df["sensor_b_aux"]
    ambos = b.notna() & aux.notna() & (aux > 0) & (b > 0)
    razao = (b[ambos] / aux[ambos])
    if len(razao):
        mediana = razao.median()
        if abs(mediana / K_RAD_S_RPM - 1) > TOLERANCIA_K:
            raise ValueError(f"sensor_b/sensor_b_aux = {mediana:.4f}, esperado {K_RAD_S_RPM:.4f} "
                             "(60/2π). A regra de recuperação deixou de valer: revisar antes de seguir.")
    vazio_b = b.isna() & aux.notna()
    vazio_aux = aux.isna() & b.notna()
    df["flag_sensor_b_recuperado"] = vazio_b.astype("int8")
    df["flag_sensor_b_aux_recuperado"] = vazio_aux.astype("int8")
    df.loc[vazio_b, "sensor_b"] = (aux[vazio_b] * K_RAD_S_RPM).round(COLUNAS_DECIMAIS["sensor_b"])
    df.loc[vazio_aux, "sensor_b_aux"] = (b[vazio_aux] / K_RAD_S_RPM).round(COLUNAS_DECIMAIS["sensor_b_aux"])
    txt = (f"razão observada {razao.median():.3f} ± {razao.std():.3f} em {len(razao)} linhas "
           f"(esperado {K_RAD_S_RPM:.3f} = 60/2π)") if len(razao) else "sem linhas com os dois valores"
    reg.adicionar("sensor_b vazio com sensor_b_aux preenchido", vazio_b.sum(),
                  "recuperado: sensor_b_aux x 60/2π + flag_sensor_b_recuperado",
                  "As duas colunas medem a mesma grandeza (rpm x rad/s); " + txt
                  + ". O script para se a razão deixar de bater.")
    reg.adicionar("sensor_b_aux vazio com sensor_b preenchido", vazio_aux.sum(),
                  "recuperado: sensor_b x 2π/60 + flag_sensor_b_aux_recuperado",
                  "Mesmo caminho no sentido contrário.")

    # ---- 9. qualidade_leitura = suspeita -> flag (continua nas médias)
    df["flag_suspeita"] = (df["qualidade_leitura"] == "suspeita").astype("int8")
    reg.adicionar("qualidade_leitura = suspeita", df["flag_suspeita"].sum(),
                  "mantida como flag_suspeita; as leituras continuam nas médias",
                  "É pequena fração da base e os defeitos graves (-999, zeros, escala) já foram "
                  "tratados à parte. A integração conta as suspeitas por dia (n_suspeita), assim a "
                  "modelagem pode testar o efeito de excluí-las.")

    # ---- 10. mesma máquina e hora com valores diferentes -> média + flag
    df = resolver_conflitos(df, reg)

    # ---- 11. grade horária completa
    df = completar_grade(df, reg)

    # ---- 12. outliers: só diagnóstico
    partes, total = [], 0
    for col in COLUNAS_DECIMAIS:
        t = df[col]
        q1, q3 = t.quantile([0.25, 0.75])
        lim = q3 + 1.5 * (q3 - q1)
        n = int((t > lim).sum())
        total += n
        partes.append(f"{col}: {n} acima de {lim:.1f}")
    reg.adicionar("Outliers (limite superior IQR, após correções)", total,
                  "mantidos, sem alteração",
                  "Pico alto em sensor é, em geral, o sinal que o modelo quer capturar; sem evidência "
                  "de erro de lançamento não há motivo para removê-los. " + " | ".join(partes))

    reg.adicionar("Umidade fora de 0-100", int(((df["umidade_relativa"] < 0) | (df["umidade_relativa"] > 100)).sum()),
                  "mantidos (checagem)", "Esperado 0 casos.")
    reg.adicionar("temp_ambiente_c / vibracao_mm_s negativos",
                  int((df["temp_ambiente_c"] < 0).sum() + (df["vibracao_mm_s"] < 0).sum()),
                  "mantidos (checagem)", "Esperado 0 casos.")

    ordem = CHAVE + list(COLUNAS_DECIMAIS) + ["umidade_relativa", "qualidade_leitura"] \
        + FLAGS + ["flag_conflito", "flag_hora_faltante"]
    df = df[ordem].sort_values(CHAVE).reset_index(drop=True)
    reg.resumo["linhas_saida"] = len(df)
    reg.resumo["maquinas"] = int(df["id_maquina"].nunique())
    return df


def resolver_conflitos(df, reg):
    tam = df.groupby(CHAVE)["id_maquina"].transform("size")
    unico = df[tam == 1].copy()
    unico["flag_conflito"] = 0
    conf = df[tam > 1]
    grupos = conf.groupby(CHAVE).ngroups if len(conf) else 0
    grandes = int((conf.groupby(CHAVE).size() >= 3).sum()) if len(conf) else 0
    if len(conf):
        agg = {col: "mean" for col in COLUNAS_DECIMAIS}
        agg["umidade_relativa"] = "mean"
        agg["qualidade_leitura"] = _qualidade_pior
        agg.update({f: "max" for f in FLAGS if f in conf.columns})
        agrup = conf.groupby(CHAVE, as_index=False).agg(agg)
        for col, casas in COLUNAS_DECIMAIS.items():
            agrup[col] = agrup[col].round(casas)
        agrup["flag_conflito"] = 1
        df = pd.concat([unico, agrup], ignore_index=True)
    else:
        df = unico
    df["umidade_relativa"] = df["umidade_relativa"].round().astype("Int64")
    reg.adicionar("Mesma máquina e hora com valores diferentes", grupos,
                  "média por máquina e hora + flag_conflito (qualidade 'suspeita' se alguma for)",
                  f"As diferenças são pequenas, então a média é a estimativa mais neutra; "
                  f"{grandes} grupos têm 3+ linhas. Sensores já tratados (sem -999/zeros) entram na "
                  "média; células vazias são ignoradas.")
    return df


def completar_grade(df, reg):
    horas = pd.date_range(df["data_hora"].min(), df["data_hora"].max(), freq="h")
    maquinas = sorted(df["id_maquina"].unique())
    grade = pd.MultiIndex.from_product([maquinas, horas], names=CHAVE).to_frame(index=False)
    grade["data_hora"] = grade["data_hora"].astype(df["data_hora"].dtype)
    comp = grade.merge(df.assign(_presente=1), on=CHAVE, how="left")
    comp["flag_hora_faltante"] = comp["_presente"].isna().astype("int8")
    comp = comp.drop(columns="_presente")
    for f in FLAGS + ["flag_conflito"]:
        comp[f] = comp[f].fillna(0).astype("int8")
    ini = df.groupby("id_maquina")["data_hora"].min()
    fim = df.groupby("id_maquina")["data_hora"].max()
    irreg = int(((ini > horas[0]) | (fim < horas[-1])).sum())
    reg.adicionar("Horas faltando na série", comp["flag_hora_faltante"].sum(),
                  "linhas criadas (grade horária completa por máquina), valores vazios + flag_hora_faltante",
                  "Sem a grade, médias e 'horas desde' ficam enviesadas. NÃO foi feita imputação: "
                  "interpolação linear usa a hora seguinte (valor futuro) e atravessa o corte das "
                  f"{c.HORA_CORTE}:00. Imputar, se for o caso, deve ser feito na modelagem, ajustado só no treino. "
                  f"Máquinas que começam depois/terminam antes do período global: {irreg}.")
    return comp


def validar(df):
    """Regras que a base tratada precisa cumprir (usadas também nos testes)."""
    assert not df.duplicated(CHAVE).any(), "chave (id_maquina, data_hora) duplicada"
    assert not (df[SENSORES] == SENTINELA).any().any(), "ainda há -999"
    assert not (df[SENSORES] == 0).any().any(), "ainda há zeros nos sensores"
    assert not (df[SENSORES] < 0).any().any(), "ainda há sensores negativos"
    por_maq = df.groupby("id_maquina").size()
    assert por_maq.nunique() == 1, "grade horária incompleta (máquinas com nº de horas diferente)"


def executar(pasta=None):
    entrada, saida = c.caminhos(pasta)
    reg = c.Registro(NOME)
    print(f"== {NOME}: lendo {entrada / (NOME + '.csv')}")
    df = tratar(c.ler_csv(entrada / f"{NOME}.csv"), reg)
    validar(df)
    c.salvar_csv(df, saida / f"{NOME}_corrigido.csv", decimais=COLUNAS_DECIMAIS)
    reg.salvar(saida)
    print(f"Salvo {saida / (NOME + '_corrigido.csv')} ({len(df)} linhas)")
    return df


if __name__ == "__main__":
    executar(c.pasta_da_linha_de_comando())
