"""Tratamento de grupos pequenos na previsão operacional do m07."""

import numpy as np


def prever_binario(modelo, treino, y, alvo, **opcoes):
    if len(alvo) == 0:
        return np.empty(0)
    classes = np.unique(y)
    if len(classes) < 2:
        return np.full(len(alvo), float(classes[0]) if len(classes) else 0.0)
    return modelo.fit(treino, y, **opcoes).predict_proba(alvo)[:, 1]


def normalizar(escores):
    if not len(escores):
        return escores
    minimo, maximo = escores.min(), escores.max()
    return (escores - minimo) / (maximo - minimo) if maximo > minimo else escores * 0 + 0.5
