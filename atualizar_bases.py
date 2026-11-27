"""Recebe as bases brutas do cliente, roda o ETL da equipe (ETL/integracao.py) e prepara as tabelas da aba "Dados tratados".

Fluxo: arquivos enviados -> identificados pelo cabeçalho -> pasta temporária da sessão (dados/extraídos) ->
ETL completo num processo separado (libera a memória ao terminar) -> CSVs tratados -> Parquet (o mesmo formato
de dados/tratados). Nada é gravado no repositório: vale para a sessão de quem enviou.
"""
import io
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

RAIZ = Path(__file__).resolve().parent
ETL = RAIZ / "ETL" / "integracao.py"
PASTA_SESSOES = Path(tempfile.gettempdir()) / "mabiyama_bases"

# Colunas mínimas de cada base bruta (pode haver colunas a mais).
COLUNAS = {
    "maquinas": ["id_maquina", "modelo", "idade", "fabricante", "data_instalacao", "numero_serie", "planta",
                 "capacidade_nominal_h", "linha_producao", "potencia_kw", "pais_origem"],
    "telemetria": ["data_hora", "id_maquina", "sensor_a", "sensor_b", "sensor_c", "sensor_d", "temp_ambiente_c",
                   "umidade_relativa", "sensor_b_aux", "vibracao_mm_s", "qualidade_leitura"],
    "operacao": ["id_maquina", "data", "turno", "operador", "pecas_produzidas", "meta_producao", "pecas_defeituosas",
                 "qtd_operadores", "consumo_energia_kwh", "utilizacao_pct", "produto_fabricado", "tempo_setup_min",
                 "hora_extra", "ind_quebra", "classe_risco", "score_saude"],
    "erros": ["data_hora", "id_maquina", "codigo_erro", "versao_firmware", "severidade", "tempo_reconhecimento_min"],
    "manutencao": ["data_hora", "id_maquina", "peca", "tecnico", "duracao_min", "fornecedor_peca", "lote_peca",
                   "custo_troca_reais"],
    "falhas": ["data_hora", "id_maquina", "peca"],
}
TITULOS = {"maquinas": "Máquinas", "telemetria": "Telemetria", "operacao": "Operação", "erros": "Erros",
           "manutencao": "Manutenção", "falhas": "Falhas"}
PECAS = ["peca_A", "peca_B", "peca_C", "peca_D"]
ETAPAS = ["maquinas", "falhas", "manutencao", "erros", "operacao", "telemetria", "integracao"]


def _cabecalho(dados: bytes) -> list[str]:
    linha = dados[:4096].decode("utf-8-sig", errors="replace").splitlines()[0] if dados else ""
    return [c.strip().strip('"').lower() for c in linha.split(",")]


def _manutencao_por_colunas(dados: bytes) -> bytes:
    """Manutenção com uma coluna por peça (peca_A..peca_D = 0/1) vira o formato de uma coluna 'peca'."""
    d = pd.read_csv(io.BytesIO(dados), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    marcadas = d[PECAS].apply(lambda s: s.str.strip().isin(["1", "1.0", "True", "true"]))
    longo = d.loc[marcadas.any(axis=1).values].copy()
    longo["peca"] = marcadas.loc[longo.index].idxmax(axis=1)
    resto = [c for c in COLUNAS["manutencao"] if c != "peca" and c in d.columns]
    return longo[resto[:2] + ["peca"] + resto[2:]].to_csv(index=False).encode("utf-8")


def identificar(arquivos: list[tuple[str, bytes]]) -> tuple[dict, list[str]]:
    """Casa cada arquivo com uma base pelo cabeçalho (o nome do arquivo não importa).

    Retorna ({base: bytes}, [problemas]). Em caso de dúvida vence a base com mais colunas exigidas presentes
    (manutenção contém as colunas de falhas, então um arquivo de manutenção nunca é lido como falhas)."""
    achados, problemas = {}, []
    for nome, dados in arquivos:
        cab = set(_cabecalho(dados))
        if {"data_hora", "id_maquina", "tecnico", "lote_peca"} <= cab and "peca" not in cab and {p.lower() for p in PECAS} <= cab:
            dados = _manutencao_por_colunas(dados)
            cab = set(_cabecalho(dados))
        casam = [b for b, cols in COLUNAS.items() if set(cols) <= cab]
        if not casam:
            parecidas = max(COLUNAS, key=lambda b: len(set(COLUNAS[b]) & cab))
            faltam = [c for c in COLUNAS[parecidas] if c not in cab]
            problemas.append(f"**{nome}** não tem as colunas de nenhuma base. Parece {TITULOS[parecidas]}, mas faltam: "
                             + ", ".join(f"`{c}`" for c in faltam[:8]) + ("…" if len(faltam) > 8 else ""))
            continue
        base = max(casam, key=lambda b: len(COLUNAS[b]))
        if base in achados:
            problemas.append(f"**{nome}** é a base {TITULOS[base]} de novo (já veio em outro arquivo). Mande só um arquivo por base.")
            continue
        achados[base] = dados
    faltando = [TITULOS[b] for b in COLUNAS if b not in achados]
    if faltando and not problemas:
        problemas.append("Faltam as bases: " + ", ".join(faltando) + ". O tratamento cruza as seis, então todas são necessárias.")
    return achados, problemas


def nova_pasta() -> Path:
    PASTA_SESSOES.mkdir(parents=True, exist_ok=True)
    # apaga envios com mais de 1 dia (o servidor guarda em /tmp)
    for p in PASTA_SESSOES.iterdir():
        if p.is_dir() and time.time() - p.stat().st_mtime > 86400:
            shutil.rmtree(p, ignore_errors=True)
    return Path(tempfile.mkdtemp(prefix="envio_", dir=PASTA_SESSOES))


def rodar(bases: dict, aviso=lambda etapa, i, n: None) -> tuple[Path, dict]:
    """Grava as bases, roda o ETL e converte para Parquet. Retorna (pasta com os .parquet, resumo).

    aviso(etapa, i, n) é chamado a cada etapa do ETL, para a barra de progresso."""
    pasta = nova_pasta()
    entrada = pasta / "dados" / "extraídos"
    entrada.mkdir(parents=True)
    for b, dados in bases.items():
        (entrada / f"{b}.csv").write_bytes(dados)

    log = []
    proc = subprocess.Popen([sys.executable, "-u", str(ETL), "--dados", str(pasta / "dados")], cwd=str(RAIZ),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    for linha in proc.stdout:
        log.append(linha.rstrip())
        etapa = "integracao" if linha.startswith("=== INTEGRA") else (re.match(r"== (\w+):", linha) or [None, None])[1]
        if etapa in ETAPAS:
            aviso(etapa, ETAPAS.index(etapa), len(ETAPAS))
    proc.wait()
    if proc.returncode != 0:
        erro = next((l for l in reversed(log) if l.strip() and not l.startswith(" ")), "erro desconhecido")
        raise RuntimeError(f"O tratamento parou: {erro}\n\n" + "\n".join(log[-25:]))

    import preparar_dados
    tratados = pasta / "dados" / "tratados"
    destino = pasta / "parquet"
    preparar_dados.exportar_tabelas(tratados, destino)
    resumo = {"quando": pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%d/%m/%Y %H:%M"),
              "linhas": {p.stem: pq.ParquetFile(p).metadata.num_rows for p in sorted(destino.glob("*.parquet"))},
              "rejeitados": sorted(p.name for p in (tratados / "_rejeitados").glob("*.csv")) if (tratados / "_rejeitados").exists() else []}
    shutil.rmtree(entrada, ignore_errors=True)
    return destino, resumo
