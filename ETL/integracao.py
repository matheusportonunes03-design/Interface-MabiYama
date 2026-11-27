"""Roda as limpezas em sequência e gera a base integrada máquina x dia.

Rodar:  python ETL/integracao.py [--dados <pasta>] [--so-integrar]

Regra de tempo (evita vazamento, Passo 1 do treinamento: só entra o que existirá na hora da previsão):
  - A previsão do dia D é feita às D 05:00 (c.HORA_CORTE).
  - Variáveis do dia D usam só o que aconteceu em (D-1 05:00, D 05:00].
  - O alvo do dia D é a falha em (D 05:00, D+1 05:00]. A falha lançada às 06:00 de D cai no alvo
    de D (e nunca nas variáveis de D, que acabam às 05:00).
  - dias_desde_prev_* (só preventivas) e dias_desde_troca_* (qualquer troca) contam até o corte;
    ficam vazios se a peça ainda não teve troca. validar_base aceita vazio e barra negativo.
Saída: dados/tratados/base_integrada_maquina_dia.csv e relatorio_qualidade.md
"""
import argparse
from pathlib import Path

import pandas as pd

import comum as c
import erros_tratamento
import falhas_tratamento
import maquinas_tratamento
import manutencao_tratamento
import operacao_tratamento
import relatorio_qualidade
import telemetria_tratamento

NOME = "integracao"
CHAVE = ["id_maquina", "dia_ref"]
# "excluir_do_alvo": falhas suspeitas não viram rótulo positivo; "manter": entram como falha normal
ACAO_FALHA_SUSPEITA = "excluir_do_alvo"
SENSORES = telemetria_tratamento.SENSORES + ["vibracao_mm_s"]
COLUNAS_REDUNDANTES = ["fabricante", "pais_origem", "capacidade_nominal_h", "potencia_kw"]


def dia_de_referencia(ts):
    """Dia D cuja janela (D-1 05:00, D 05:00] contém o instante `ts`."""
    return (ts - pd.Timedelta(hours=c.HORA_CORTE)).dt.ceil("D")


def _ns(serie):
    return serie.astype("datetime64[ns]")


def _agregar_telemetria(tel):
    tel = tel.assign(dia_ref=dia_de_referencia(tel["data_hora"]))
    nomes = {"mean": "media", "std": "dp", "min": "min", "max": "max"}
    agg = {s: ["mean", "std", "min", "max"] for s in SENSORES}
    agg.update({s: ["mean"] for s in ["temp_ambiente_c", "umidade_relativa"]})
    flags = [col for col in tel.columns if col.startswith("flag_")]
    agg.update({f: ["sum"] for f in flags})
    g = tel.groupby(CHAVE).agg(agg)
    g.columns = [f"n_{a[5:]}" if b == "sum" else f"{a}_{nomes[b]}" for a, b in g.columns]
    g["n_horas_na_janela"] = tel.groupby(CHAVE).size()
    g["n_horas_com_leitura"] = g["n_horas_na_janela"] - g["n_hora_faltante"]
    return g.reset_index()


def _agregar_erros(er):
    er = er.dropna(subset=["data_hora"]).assign(dia_ref=lambda d: dia_de_referencia(d["data_hora"]))
    pico = er["flag_horario_pico"] == 1
    er["n_erros"] = (~pico).astype(int)
    er["n_erros_pico"] = pico.astype(int)
    cols = ["n_erros", "n_erros_pico"]
    for sev in ["baixa", "media", "alta"]:
        er[f"n_erros_sev_{sev}"] = ((er["severidade"] == sev) & ~pico).astype(int)
        cols.append(f"n_erros_sev_{sev}")
    for cod in sorted(er["codigo_erro"].dropna().unique()):
        er[f"n_{cod}"] = ((er["codigo_erro"] == cod) & ~pico).astype(int)
        cols.append(f"n_{cod}")
    g = er.groupby(CHAVE)[cols].sum()
    g["tempo_reconhecimento_min_media"] = er.groupby(CHAVE)["tempo_reconhecimento_min"].mean()
    return g.reset_index()


def _agregar_operacao(op, reg=None):
    op = op.dropna(subset=["data"]).copy()
    fim_h = op["turno"].map({t: ini + dur for t, (ini, dur) in c.TURNOS.items()})
    sem_turno = fim_h.isna()
    if reg is not None:
        reg.adicionar("Turno vazio ou fora de comum.TURNOS", int(sem_turno.sum()),
                      "linha fora da agregação da operação",
                      "Sem saber o fim do turno não dá para garantir que ele terminou antes do corte "
                      f"das {c.HORA_CORTE:02d}:00. Valores encontrados: {sorted(op.loc[sem_turno, 'turno'].dropna().unique().tolist())}.")
    op, fim_h = op[~sem_turno], fim_h[~sem_turno]
    op["fim_turno"] = _ns(op["data"]) + pd.to_timedelta(fim_h, unit="h")
    # um turno só conta no dia D se terminou até D 05:00
    op["dia_ref"] = dia_de_referencia(op["fim_turno"])
    op["pecas_produzidas"] = op["pecas_produzidas"].astype("float")
    op["meta_producao"] = op["meta_producao"].astype("float")
    op["pecas_defeituosas"] = op["pecas_defeituosas"].astype("float")
    g = op.groupby(CHAVE).agg(
        op_pecas_produzidas=("pecas_produzidas", "sum"),
        op_meta_producao=("meta_producao", lambda s: s.sum(min_count=1)),
        op_pecas_defeituosas=("pecas_defeituosas", "sum"),
        op_qtd_operadores_media=("qtd_operadores", "mean"),
        op_tempo_setup_min=("tempo_setup_min", "sum"),
        op_consumo_energia_kwh=("consumo_energia_kwh", "sum"),
        op_utilizacao_pct_media=("utilizacao_pct", "mean"),
        op_ind_quebra=("ind_quebra", "mean"),
        op_score_saude=("score_saude", "mean"),
        op_hora_extra=("hora_extra", "max"),
        op_n_turnos=("turno", "size"),
    ).reset_index()
    g["op_taxa_defeito"] = g["op_pecas_defeituosas"] / g["op_pecas_produzidas"].where(g["op_pecas_produzidas"] > 0)
    g["op_pct_meta"] = g["op_pecas_produzidas"] / g["op_meta_producao"].where(g["op_meta_producao"] > 0)
    return g


def _dias_desde_troca(base, manut, prefixo, tipos=None):
    """Dias entre o corte (D 05:00) e a última troca da peça ATÉ o corte (inclusive), por peça.

    `tipos` filtra a coluna `tipo` (None = qualquer troca). Sem troca antes do corte: vazio.
    """
    trocas = manut.dropna(subset=["data_hora", "peca"])
    if tipos is not None:
        trocas = trocas[trocas["tipo"].isin(tipos)]
    corte = base[["id_maquina", "dia_ref"]].copy()
    corte["_i"] = corte.index
    corte["corte"] = _ns(corte["dia_ref"]) + pd.Timedelta(hours=c.HORA_CORTE)
    corte = corte.sort_values("corte")
    for peca in sorted(c.PECAS.values()):
        r = trocas.loc[trocas["peca"] == peca, ["id_maquina", "data_hora"]].rename(columns={"data_hora": "ult"})
        r = r.assign(ult=_ns(r["ult"])).sort_values("ult")
        m = pd.merge_asof(corte, r, left_on="corte", right_on="ult", by="id_maquina", direction="backward")
        dias = ((m["corte"] - m["ult"]).dt.total_seconds() / 86400).set_axis(m["_i"])
        base[f"{prefixo}_{peca}"] = dias.reindex(base.index)
    return base


def _dias_desde_preventiva(base, manut):
    """Só trocas PREVENTIVAS (idade da peça pelo calendário)."""
    return _dias_desde_troca(base, manut, "dias_desde_prev", tipos=["preventiva"])


def _alvo(base, falhas, reg):
    f = falhas.dropna(subset=["data_hora", "peca"]).copy()
    f["dia_ref"] = dia_de_referencia(f["data_hora"]) - pd.Timedelta(days=1)
    susp = f["flag_falha_suspeita"] == 1
    validas = f if ACAO_FALHA_SUSPEITA == "manter" else f[~susp]
    pecas = sorted(c.PECAS.values())

    piv = (validas.assign(v=1).pivot_table(index=CHAVE, columns="peca", values="v", aggfunc="max", fill_value=0)
           .reindex(columns=pecas, fill_value=0))
    piv.columns = [f"alvo_falha_{p}" for p in piv.columns]
    base = base.merge(piv.reset_index(), on=CHAVE, how="left")
    alvo_cols = [f"alvo_falha_{p}" for p in pecas]
    base[alvo_cols] = base[alvo_cols].fillna(0).astype("Int64")
    base["alvo_falha_qualquer"] = base[alvo_cols].max(axis=1)

    incerto = f[susp].assign(i=1).groupby(CHAVE)["i"].max().rename("alvo_incerto").reset_index()
    base = base.merge(incerto, on=CHAVE, how="left")
    base["alvo_incerto"] = base["alvo_incerto"].fillna(0).astype("int8")

    # Último dia cuja janela do alvo contém uma falha registrada. Usar a data da falha (normalize)
    # erraria quando ela não é das 06:00: uma falha às 03:00 de X pertence à janela do dia X-1.
    ultima = f["dia_ref"].max()
    base["alvo_disponivel"] = (base["dia_ref"] <= ultima).astype("int8")
    sem_alvo = base["alvo_disponivel"] == 0
    for col in alvo_cols + ["alvo_falha_qualquer"]:
        base[col] = base[col].astype("Int64").mask(sem_alvo)

    reg.adicionar("Dias depois da última falha registrada", int(sem_alvo.sum()),
                  "alvo vazio e alvo_disponivel = 0",
                  f"A tabela de falhas termina em {ultima:%Y-%m-%d}. Esses dias não são 'sem falha': não "
                  "se sabe. Rotulá-los 0 criaria negativos falsos. Excluir do treino/validação.")
    reg.adicionar("Máquina-dias com falha suspeita na janela do alvo", int((base["alvo_incerto"] == 1).sum()),
                  f"alvo_incerto = 1 (ACAO_FALHA_SUSPEITA = '{ACAO_FALHA_SUSPEITA}')",
                  "Recomenda-se tirar essas linhas do treino enquanto a origem das falhas suspeitas não é "
                  "confirmada com o cliente.")
    return base


def montar_base(maquinas, telemetria, erros, manutencao, operacao, falhas, reg):
    tel = _agregar_telemetria(telemetria)
    dias = pd.date_range(tel["dia_ref"].min(), tel["dia_ref"].max(), freq="D")
    base = pd.MultiIndex.from_product([sorted(maquinas["id_maquina"]), dias], names=CHAVE).to_frame(index=False)
    base["dia_ref"] = base["dia_ref"].astype(tel["dia_ref"].dtype)

    # ---- cadastro: só o modelo (fabricante, país, capacidade e potência são 1 para 1 com ele)
    cad = maquinas[["id_maquina", "modelo", "linha_producao", "data_instalacao", "ano_instalacao"]
                   + [col for col in maquinas.columns if col.startswith("flag_")]].copy()
    base = base.merge(cad, on="id_maquina", how="left")
    meio = pd.to_datetime(base["ano_instalacao"].astype("Int64").astype("string") + "-07-01", errors="coerce")
    inst = base["data_instalacao"].fillna(meio)
    base["idade_anos"] = (_ns(base["dia_ref"]) - _ns(inst)).dt.days / 365.25
    base["flag_idade_aproximada"] = (base["data_instalacao"].isna() & base["ano_instalacao"].notna()).astype("int8")
    base = base.drop(columns=["data_instalacao", "ano_instalacao"])
    base = base.rename(columns={col: f"cad_{col}" for col in base.columns if col.startswith("flag_") and col != "flag_idade_aproximada"})
    reg.adicionar("Colunas redundantes do cadastro (fabricante, país, capacidade, potência)",
                  len(COLUNAS_REDUNDANTES), "fora da base integrada (continuam em maquinas_corrigido.csv)",
                  "São 1 para 1 com o modelo; usar só o modelo evita variáveis duplicadas.")

    ids_outros = set(telemetria["id_maquina"]) | set(erros["id_maquina"]) | set(operacao["id_maquina"]) \
        | set(manutencao["id_maquina"]) | set(falhas["id_maquina"])
    reg.adicionar("id_maquina fora do cadastro (em qualquer tabela)", len(ids_outros - set(maquinas["id_maquina"])),
                  "ignorados na integração (checagem)", "Esperado 0 casos.")

    base = base.merge(tel, on=CHAVE, how="left")
    base = base.merge(_agregar_erros(erros), on=CHAVE, how="left")
    contagens = [col for col in base.columns if col.startswith("n_erro") or col.startswith("n_erros")]
    base[contagens] = base[contagens].fillna(0).astype(int)
    base = base.merge(_agregar_operacao(operacao, reg), on=CHAVE, how="left")

    base = _dias_desde_preventiva(base, manutencao)
    base = _dias_desde_troca(base, manutencao, "dias_desde_troca")
    prev = [col for col in base.columns if col.startswith("dias_desde_prev_")]
    vazios = base[prev].isna().sum()
    reg.adicionar("dias_desde_prev vazio (nenhuma preventiva da peça antes do corte)", int(vazios.sum()),
                  "mantido vazio",
                  "Não existe troca anterior para medir; zero ou outro número inventaria uma idade de peça. "
                  "Acontece nos primeiros dias da série e em peças sem preventiva registrada. A modelagem "
                  "decide (ex.: indicador de 'sem histórico' + imputação ajustada só no treino). Por peça: "
                  + ", ".join(f"{col[16:]}={int(n)}" for col, n in vazios.items()))
    reg.adicionar("dias_desde_troca (qualquer troca, preventiva ou corretiva)", len(prev),
                  "colunas dias_desde_troca_peca_X criadas, com o mesmo corte das 05:00",
                  "Depois de uma troca corretiva a peça é nova, e só a contagem por preventiva diria que ela é "
                  "velha. A corretiva de uma falha lançada às 06:00 de D entra só nas variáveis de D+1 (depois "
                  "do corte), então não vaza o alvo de D; o teste de vazamento cobre isso.")

    base = _alvo(base, falhas, reg)

    cobertura = {"telemetria": telemetria["data_hora"], "erros": erros["data_hora"],
                 "manutencao": manutencao["data_hora"], "falhas": falhas["data_hora"],
                 "operacao": operacao["data"]}
    reg.adicionar("Cobertura temporal por tabela", "; ".join(
        f"{k} {v.min():%Y-%m-%d} a {v.max():%Y-%m-%d}" for k, v in cobertura.items() if v.notna().any()),
        "registrada (checagem)",
        "Tabelas que começam depois ou terminam antes das outras deixam variáveis vazias nesses dias. "
        "Se falhas começar depois da telemetria, os dias anteriores ficam rotulados 0 sem que se saiba "
        "se houve falha: conferir antes de treinar.")
    reg.adicionar("idade_anos negativa (dia anterior à instalação)", int((base["idade_anos"] < 0).sum()),
                  "mantida (checagem)", "Esperado 0 casos; se houver, a data de instalação ou a série está errada.")

    reg.adicionar("Janela de previsão", len(base),
                  f"máquina x dia; variáveis em (D-1 {c.HORA_CORTE:02d}:00, D {c.HORA_CORTE:02d}:00]; "
                  f"alvo em (D {c.HORA_CORTE:02d}:00, D+1 {c.HORA_CORTE:02d}:00]",
                  "Falhas e manutenções são lançadas às 06:00; o corte às 05:00 impede que o registro do "
                  "dia entre nas variáveis do próprio dia (vazamento).")
    return base.sort_values(CHAVE).reset_index(drop=True)


def validar_base(base):
    """Regras que a base integrada precisa cumprir (para a execução se alguma falhar)."""
    assert not base.duplicated(CHAVE).any(), "chave (id_maquina, dia_ref) duplicada na base integrada"

    # Vazio = a peça ainda não tinha troca antes do corte; é válido e NÃO pode contar como erro.
    # (Antes: `(df.dropna(how="all") >= 0).all()` tratava NaN como negativo, porque NaN >= 0 é False,
    # e quebrava sempre que uma peça tinha valor e outra ainda não, no mesmo dia.)
    dias = [col for col in base.columns if col.startswith("dias_desde_")]
    negativos = (base[dias] < 0).sum()
    assert not negativos.any(), \
        f"dias_desde_* negativo (troca depois do corte, olhou o futuro): {negativos[negativos > 0].to_dict()}"

    alvo = [col for col in base.columns if col.startswith("alvo_falha_")]
    valores = base[alvo].astype("float")
    assert (valores.isin([0, 1]) | valores.isna()).all().all(), "alvo com valor diferente de 0/1"
    sem_alvo = base["alvo_disponivel"] == 0
    assert valores[sem_alvo].isna().all().all(), "alvo preenchido em dia sem alvo disponível"
    assert valores[~sem_alvo].notna().all().all(), "alvo vazio em dia com alvo disponível"


def executar(pasta=None, so_integrar=False):
    entrada, saida = c.caminhos(pasta)
    if not so_integrar:
        print("=== LIMPEZA ===")
        for modulo in (maquinas_tratamento, falhas_tratamento, manutencao_tratamento,
                       erros_tratamento, operacao_tratamento, telemetria_tratamento):
            modulo.executar(pasta)

    print("\n=== INTEGRAÇÃO ===")
    reg = c.Registro(NOME)
    ler = lambda n: c.ler_csv(saida / f"{n}_corrigido.csv")
    maq = ler("maquinas")
    maq["data_instalacao"] = c.para_datetime(maq["data_instalacao"])
    maq["ano_instalacao"] = c.texto_para_inteiro(maq["ano_instalacao"])

    tel = ler("telemetria")
    tel["data_hora"] = c.para_datetime(tel["data_hora"])
    num = [col for col in tel.columns if col not in ("id_maquina", "data_hora", "qualidade_leitura")]
    tel[num] = tel[num].apply(pd.to_numeric)

    er = ler("erros")
    er["data_hora"] = c.para_datetime(er["data_hora"])
    er["flag_horario_pico"] = er["flag_horario_pico"].astype(int)
    er["tempo_reconhecimento_min"] = c.texto_para_float(er["tempo_reconhecimento_min"])

    man = ler("manutencao")
    man["data_hora"] = c.para_datetime(man["data_hora"])

    op = ler("operacao")
    op["data"] = c.para_datetime(op["data"])
    for col in ["pecas_produzidas", "meta_producao", "pecas_defeituosas", "qtd_operadores", "tempo_setup_min",
                "consumo_energia_kwh", "utilizacao_pct", "ind_quebra", "score_saude", "hora_extra"]:
        op[col] = pd.to_numeric(op[col])

    fa = ler("falhas")
    fa["data_hora"] = c.para_datetime(fa["data_hora"])
    fa["flag_falha_suspeita"] = fa["flag_falha_suspeita"].astype(int)

    base = montar_base(maq, tel, er, man, op, fa, reg)
    validar_base(base)
    c.salvar_csv(base, saida / "base_integrada_maquina_dia.csv")
    reg.resumo["linhas_saida"] = len(base)
    reg.salvar(saida)
    caminho = relatorio_qualidade.gerar(saida)
    print(f"\nSalvo {saida / 'base_integrada_maquina_dia.csv'} ({len(base)} linhas) e {caminho}")
    return base


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", default=None)
    ap.add_argument("--so-integrar", action="store_true", help="pula a limpeza e usa os tratados existentes")
    a = ap.parse_args()
    executar(a.dados, a.so_integrar)
