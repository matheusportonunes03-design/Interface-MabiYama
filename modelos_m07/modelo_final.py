"""Gera a previsão operacional com as 22 listas do m07, modelo final do notebook da Etapa 4."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import warnings

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier

from comum_modelo import prever_binario
import modelo_membros as M
import modelo_preditivo_v2 as B
import modelo_preditivo_y09 as A
from preparar_previsao import HORA_CORTE, preparar

warnings.filterwarnings("ignore", category=RuntimeWarning)
SIGMAS = (1.25, 1.0, 1.6)
HATS = ("v15", "v21", "v28", "v30", "p06_v31", "p06_v32", "p06_v33")


def membro_catboost(L, conj, ids, sementes, tau=180):
    """Membro CatBoost do notebook, com as variáveis do membro B e decaimento de 180 dias."""
    filtros = [c for c in L.columns if c.startswith("mf_")]
    cols = M.especificacoes(L, conj, filtros)["B"]["cols"]
    treino = L[L["y_known"] & ~L["incerto"]]
    alvo = L[L["dia_ref"].between(A.INICIO_TESTE, A.INICIO_TESTE + pd.Timedelta(days=A.DIAS_TESTE - 1))]
    treino = treino[treino["cand"] & (treino["pf1_hat"].fillna(0) < M.GATE)]
    candidatas = alvo[alvo["cand"] & (alvo["pf1_hat"].fillna(0) < M.GATE)]
    pesos = np.exp(-(A.INICIO_TESTE - treino["dia_ref"]).dt.days / tau)
    resultado = pd.Series(np.nan, index=candidatas.index)
    for p in A.PECAS:
        treinar, prever = treino[treino["peca"].eq(p)], candidatas[candidatas["peca"].eq(p)]
        resultados = [prever_binario(CatBoostClassifier(iterations=600, learning_rate=0.03, depth=4, l2_leaf_reg=10,
                                   random_seed=seed, verbose=False, allow_writing_files=False, thread_count=2),
                      treinar[cols], treinar["y"], prever[cols], sample_weight=pesos.loc[treinar.index])
                      for seed in range(sementes)]
        resultado.loc[prever.index] = np.mean(resultados, axis=0)
    resultado = resultado.groupby(candidatas["peca"]).rank(pct=True) * 0.99 + 1e-3
    saida = pd.Series(1e-5, index=alvo.index)
    saida.loc[candidatas.index] = resultado
    return M.tabela(saida, alvo, ids)


def gerar(publicados, saida, arvore, sementes=3):
    with TemporaryDirectory(prefix="mabiyama_m07_") as pasta:
        dados = Path(pasta)
        periodo, inicio, fim, rotulos = preparar(publicados, dados)
        A.INICIO_TESTE = B.INICIO_TESTE = inicio
        A.DIAS_TESTE = B.DIAS_TESTE = (fim - inicio).days + 1
        A.FIM_NORMAL = B.FIM_NORMAL = inicio + HORA_CORTE

        print("Treinando a família y09 e as listas hat.", flush=True)
        L, conj = A.montar_tudo(dados / "base_integrada_maquina_dia.csv", dados / "telemetria_corrigido.csv",
                                dados / "erros_corrigido.csv", dados / "falhas_corrigido.csv",
                                dados / "base_modelagem.csv", periodo=periodo, rotulos=rotulos)
        treino = L[L["y_known"] & ~L["incerto"]]
        alvo = L[L["dia_ref"].between(inicio, fim)]
        rec, p06, _ = A.pipeline(treino, alvo, conj, sementes, 30, dados / "ids_previsao.csv", dados / "y09", 3)
        ids = rec["sub41"]["id"]
        listas = [rec[n] for n in ("sub41", "sub43", "sub42", "sub44", "sub40")] + [p06]
        listas += [pd.read_csv(dados / "y09" / f"lista_{n}.csv").set_index("id").loc[ids].reset_index() for n in HATS]

        for sigma in SIGMAS:
            print(f"Treinando a família v2 com sigma {sigma}.", flush=True)
            B.SIG = sigma
            v2 = B.gerar_submissao(dados, dados / "v2", sementes, periodo=periodo, rotulos=rotulos)
            listas.append(v2.set_index("id").loc[ids].reset_index())
        print("Treinando os membros A–E e CatBoost.", flush=True)
        listas.extend(M.membros(L, conj, ids, seeds=sementes).values())
        listas.append(membro_catboost(L.join(M.filtros_casados(L)), conj, ids, sementes))
        assert len(listas) == 22
        final = A.melhores_n(listas, n=3, k=10)

    if final.empty or final["id"].duplicated().any() or not final[A.PECAS].apply(lambda s: s.between(0, 1)).all().all():
        raise ValueError("O modelo gerou uma previsão incompleta ou com escores inválidos.")
    saida.mkdir(parents=True, exist_ok=True)
    final.to_csv(saida / "previsao_m07.csv", index=False)
    manifesto = {"arvore_bases": arvore, "linhas": len(final), "inicio": str(inicio.date()), "fim": str(fim.date())}
    (saida / "previsao_m07.json").write_text(json.dumps(manifesto, indent=2) + "\n", encoding="utf-8")
    return manifesto


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dados", type=Path, required=True, help="Pasta com os Parquets tratados.")
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--arvore", required=True, help="SHA da árvore dados/tratados da versão avaliada.")
    parser.add_argument("--seeds", type=int, default=3)
    args = parser.parse_args()
    print(gerar(args.dados, args.saida, args.arvore, max(1, args.seeds)))

