"""Gera o Relatório de Qualidade a partir do registro que os scripts gravam.

Nenhum número é escrito à mão: tudo vem de dados/tratados/_registro/*.json.
"""
import json
from datetime import date
from pathlib import Path

import comum as c

ORDEM = ["telemetria", "falhas", "manutencao", "erros", "operacao", "maquinas", "integracao"]


def _celula(txt):
    return str(txt).replace("|", "/").replace("\n", " ")


def gerar(pasta_saida):
    pasta_saida = Path(pasta_saida)
    registros = {}
    for arq in (pasta_saida / "_registro").glob("*.json"):
        r = json.loads(arq.read_text(encoding="utf-8"))
        registros[r["tabela"]] = r

    L = ["# Relatório de Qualidade dos Dados (gerado pelo código)", "",
         f"Gerado em {date.today():%d/%m/%Y} por `ETL/integracao.py`. Os números vêm da execução, não de "
         "digitação. Rodar de novo atualiza tudo.", "",
         "## Premissas (o que estará disponível na hora da previsão)", "",
         f"- A previsão do dia D é feita às {c.HORA_CORTE:02d}:00. Variáveis do dia D usam só dados em "
         f"(D-1 {c.HORA_CORTE:02d}:00, D {c.HORA_CORTE:02d}:00].",
         f"- O alvo do dia D é a falha de cada peça em (D {c.HORA_CORTE:02d}:00, D+1 {c.HORA_CORTE:02d}:00].",
         "- Falhas e manutenções são lançadas às 06:00, depois do corte, e por isso não entram nas variáveis do próprio dia.",
         "- Horário dos turnos (**assumido, confirmar com o cliente**): "
         + ", ".join(f"{t} {h:02d}:00 por {d} h" for t, (h, d) in c.TURNOS.items())
         + ". Um turno só entra no dia D se terminou até o corte.",
         "- `dias_desde_prev_*` (só preventivas) e `dias_desde_troca_*` (qualquer troca) contam até o corte; "
         "ficam vazios enquanto a peça não teve troca (não é erro).",
         "- Datas fora do ISO são lidas como dia/mês/ano; as ilegíveis vão para `_rejeitados/`.",
         "- Flags `flag_<problema>` (0/1) marcam toda linha cujo valor foi alterado; formatação pura "
         "(caixa, vírgula decimal) é contada aqui, mas não marcada.", ""]
    for nome in ORDEM:
        r = registros.get(nome)
        if not r:
            continue
        res = r["resumo"]
        L += [f"## {nome}", ""]
        if "linhas_entrada" in res:
            L.append(f"Linhas lidas: **{res['linhas_entrada']}** | linhas na saída: **{res.get('linhas_saida', '?')}**"
                     + (f" | máquinas: {res['maquinas']}" if "maquinas" in res else ""))
        else:
            L.append(f"Linhas na saída: **{res.get('linhas_saida', '?')}**")
        L += ["", "| Problema | Casos | Decisão | Justificativa |", "|---|---:|---|---|"]
        for it in r["itens"]:
            L.append(f"| {_celula(it['problema'])} | {it['casos']} | {_celula(it['decisao'])} | {_celula(it['justificativa'])} |")
        L.append("")
    destino = pasta_saida / "relatorio_qualidade.md"
    destino.write_text("\n".join(L), encoding="utf-8")
    return destino
