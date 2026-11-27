"""Funções e regras compartilhadas pelos scripts de tratamento (Etapa 2).

Tudo que é usado por mais de um script fica aqui: caminhos relativos à raiz do
repositório, leitura/escrita padronizadas, conversão de números e o `Registro`,
que guarda cada decisão (casos, o que foi feito, por quê). Os números do
Relatório de Qualidade saem desse registro, nunca são escritos à mão.
"""
import argparse
import json
import os
import re
import unicodedata
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------- caminhos
# ETL/comum.py -> parents[1] é a raiz do repositório (funciona em qualquer PC).
RAIZ = Path(__file__).resolve().parents[1]


def pasta_dados(pasta=None):
    """Ordem: argumento > variável de ambiente DADOS_DIR > <raiz>/dados."""
    if pasta is not None:
        return Path(pasta)
    if os.environ.get("DADOS_DIR"):
        return Path(os.environ["DADOS_DIR"])
    return RAIZ / "dados"


def caminhos(pasta=None):
    base = pasta_dados(pasta)
    return base / "extraídos", base / "tratados"


def pasta_da_linha_de_comando():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", default=None, help="pasta 'dados' (padrão: <raiz>/dados)")
    return ap.parse_args().dados


# ---------------------------------------------------------- regras do projeto
FORMATO_DATA_HORA = "%Y-%m-%d %H:%M:%S"  # ISO: todas as saídas usam o mesmo formato
FORMATO_DATA = "%Y-%m-%d"

# Corte diário da previsão: só entra no dia D o que aconteceu até D 05:00 (inclusive).
HORA_CORTE = 5

# Horário dos turnos: (hora de início, duração em horas).
# ATENÇÃO: valores ASSUMIDOS, o levantamento com o cliente ainda precisa confirmá-los.
# Se a noite termina depois das 05:00, a noite de D-1 não entra na previsão de D.
TURNOS = {"manha": (6, 8), "tarde": (14, 8), "noite": (22, 8)}

PECAS = {"pecaa": "peca_A", "pecab": "peca_B", "pecac": "peca_C", "pecad": "peca_D"}


# ------------------------------------------------------------------ textos
def tirar_acentos(texto):
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in texto if not unicodedata.combining(ch))


def consertar_encoding(texto):
    try:
        return texto.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def so_letras(valor):
    """minúsculas, sem acento, só letras (chave de comparação)."""
    return re.sub(r"[^a-z]", "", tirar_acentos(str(valor)).lower())


def padronizar_categoria(valor, mapa):
    """mapa: chave normalizada (so_letras) -> valor padrão. Não reconhecido: mantém."""
    if pd.isna(valor):
        return valor
    return mapa.get(so_letras(valor), valor)


def padronizar_peca(valor):
    return padronizar_categoria(valor, PECAS)


# ------------------------------------------------------------------ números
def contar_dois_separadores(serie):
    """Quantas células têm mais de um separador (ex.: '1,736,809')."""
    return serie.astype("string").str.count(r"[.,]").fillna(0) > 1


def _texto_numerico(serie):
    s = serie.astype("string").str.strip().str.replace(" ", "", regex=False)
    # Com mais de um separador, o ÚLTIMO é o decimal e os anteriores são milhar:
    # '1,736,809' -> '1736.809'. (Antes: todas as vírgulas viravam ponto, dava
    # '1.736.809', que não é número e o valor virava vazio.)
    s = s.str.replace(r"[.,](?=.*[.,])", "", regex=True)
    s = s.str.replace(",", ".", regex=False)
    return s.replace("", pd.NA)


def texto_para_float(serie):
    return pd.to_numeric(_texto_numerico(serie), errors="coerce").astype("float")


def texto_para_decimal(serie, casas):
    return texto_para_float(serie).round(casas)


def texto_para_inteiro(serie):
    return pd.to_numeric(_texto_numerico(serie), errors="coerce").round().astype("Int64")


def _datas_iso_e_resto(serie):
    s = serie.astype("string").str.strip()
    iso = pd.to_datetime(s, format="ISO8601", errors="coerce")
    resto = iso.isna() & s.notna() & (s != "")
    return s, iso, resto


def dia_primeiro(serie):
    """Decide a ordem das datas com barra (dd/mm ou mm/dd) pelos próprios dados.

    Se algum primeiro campo passa de 12, só pode ser dia (dd/mm/aaaa, padrão Brasil); se algum segundo
    campo passa de 12, é mês/dia/ano (arquivo salvo pelo Excel em inglês). Sem nenhum caso decisivo,
    fica o padrão brasileiro.
    """
    partes = serie.astype("string").str.extract(r"^\s*(\d{1,2})[/.-](\d{1,2})[/.-]\d{2,4}")
    primeiro, segundo = pd.to_numeric(partes[0]), pd.to_numeric(partes[1])
    if (primeiro > 12).any():
        return True
    if (segundo > 12).any():
        return False
    return True


def para_datetime(serie):
    """Converte datas aceitando formatos misturados.

    Sem `format`, o pandas 3 adivinha o formato pela PRIMEIRA linha e transforma em vazio tudo o
    que vier diferente (data sem hora, 'T' no meio, dd/mm/aaaa), e essas linhas sumiriam como
    "sem data". Aqui: ISO primeiro (AAAA-MM-DD [HH:MM[:SS]]); o que sobrar, na ordem que os dados
    mostram (dia_primeiro: dd/mm/aaaa ou mm/dd/aaaa).
    """
    s, iso, resto = _datas_iso_e_resto(serie)
    if resto.any():
        iso = iso.copy()
        iso[resto] = pd.to_datetime(s[resto], format="mixed", dayfirst=dia_primeiro(s[resto]), errors="coerce")
    return iso


def converter_datas(serie, reg, coluna):
    """para_datetime + registro de quantas datas vieram fora do ISO e quantas não deu para ler."""
    s, _, resto = _datas_iso_e_resto(serie)
    convertida = para_datetime(serie)
    ilegivel = convertida.isna() & s.notna() & (s != "")
    reg.adicionar(f"{coluna} fora do formato ISO", int(resto.sum()),
                  f"{int(resto.sum() - ilegivel.sum())} convertidas lendo "
                  f"{'dia/mês/ano' if dia_primeiro(s[resto]) else 'mês/dia/ano'}; "
                  f"{int(ilegivel.sum())} ilegíveis viram vazio (e a linha vai para _rejeitados/ se for chave)",
                  "Formatos misturados no mesmo arquivo. A saída sai toda em ISO. Exemplos ilegíveis: "
                  + (", ".join(map(str, s[ilegivel].unique()[:5])) or "nenhum"))
    return convertida


# --------------------------------------------------------------- leitura/escrita
def ler_csv(caminho, usecols=None):
    df = pd.read_csv(caminho, dtype=str, keep_default_na=False,
                     encoding="utf-8-sig", usecols=usecols)
    for col in df.columns:
        df[col] = df[col].str.strip()
    return df


def vazio_para_na(df):
    return df.mask(df == "")


def salvar_csv(df, caminho, decimais=None):
    """CSV é a saída principal (o .xlsx não comporta bases com mais de 1.048.576 linhas)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    saida = df.copy()
    for col in saida.columns:
        if pd.api.types.is_datetime64_any_dtype(saida[col]):
            so_data = (saida[col].dropna().dt.normalize() == saida[col].dropna()).all()
            saida[col] = saida[col].dt.strftime(FORMATO_DATA if so_data else FORMATO_DATA_HORA)
    for col, casas in (decimais or {}).items():
        saida[col] = saida[col].map(lambda v, c=casas: f"{v:.{c}f}", na_action="ignore")
    saida.to_csv(caminho, index=False, encoding="utf-8-sig")
    return caminho


def chaves_evento(caminho):
    """(id_maquina, data_hora, peca) de um CSV bruto de eventos (falhas/manutenção).

    Serve para cruzar falha x manutenção sem um script depender do outro.
    Retorna None se o arquivo não existe.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        return None
    df = ler_csv(caminho, usecols=["id_maquina", "data_hora", "peca"])
    df["data_hora"] = para_datetime(df["data_hora"])
    df["peca"] = df["peca"].map(padronizar_peca)
    return df.dropna().drop_duplicates().reset_index(drop=True)


def marcar_presenca(df, chaves, colunas=("id_maquina", "data_hora", "peca")):
    """Série booleana: a linha de df tem (colunas) presente na tabela `chaves`?"""
    colunas = list(colunas)
    ref = chaves[colunas].drop_duplicates().assign(_achou=1)
    m = df[colunas].merge(ref, on=colunas, how="left")
    return m["_achou"].notna().to_numpy()


# ---------------------------------------------------------------- registro
class Registro:
    """Guarda, por tabela, cada problema: quantos casos, o que foi feito e por quê."""

    def __init__(self, tabela):
        self.tabela = tabela
        self.itens = []
        self.resumo = {}
        self.rejeitados = None  # linhas que não puderam ser tratadas (sem data/ID)

    def adicionar(self, problema, casos, decisao, justificativa):
        if not isinstance(casos, str):
            casos = int(casos)
        self.itens.append({"problema": problema, "casos": casos,
                           "decisao": decisao, "justificativa": justificativa})
        print(f"  [{self.tabela}] {problema}: {casos} -> {decisao}")

    def salvar(self, pasta_saida):
        destino = Path(pasta_saida) / "_registro" / f"{self.tabela}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "w", encoding="utf-8") as f:
            json.dump({"tabela": self.tabela, "resumo": self.resumo, "itens": self.itens},
                      f, ensure_ascii=False, indent=2, default=str)
        rej = Path(pasta_saida) / "_rejeitados" / f"{self.tabela}_rejeitados.csv"
        if self.rejeitados is not None and len(self.rejeitados):
            rej.parent.mkdir(parents=True, exist_ok=True)
            self.rejeitados.to_csv(rej, index=False, encoding="utf-8-sig")
        elif rej.exists():
            rej.unlink()  # arquivo de uma execução anterior não pode sobrar e parecer atual


def separar_rejeitados(df, mascara, reg, motivo):
    """Tira do df as linhas sem chave utilizável (data/ID), registra e guarda à parte."""
    mascara = pd.Series(mascara, index=df.index).fillna(False).astype(bool)
    if mascara.any():
        reg.rejeitados = df[mascara].copy()
    reg.adicionar(f"Linhas sem {motivo}", mascara.sum(),
                  "removidas da base tratada e salvas em _rejeitados/",
                  "Sem a chave não dá para posicionar a linha no tempo nem cruzar com as outras "
                  "tabelas; ficam guardadas à parte para conferência com o cliente.")
    return df[~mascara].reset_index(drop=True)
