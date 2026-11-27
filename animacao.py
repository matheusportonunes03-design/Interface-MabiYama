"""Animação de boas-vindas em 3D isométrico (estilo Habbo Hotel) e ajudantes que acompanham a rolagem.

Ao entrar no painel, o operário Beto chega à fábrica, veste os EPIs, pega as ferramentas, para diante das máquinas e
pergunta em qual fazer a manutenção primeiro. O Floco (robô-boneco-de-neve, que representa o modelo de previsão) responde
com as 5 máquinas de maior probabilidade de falha da previsão em uso. Depois a rolagem é liberada e os dois ficam juntos
na lateral direita: o Beto pergunta e o Floco explica o bloco que está no centro da tela, em todas as páginas.

Como funciona: um componente de altura 0 injeta o motor (frontend/fabrica_*.js) no documento da página, onde ele
cria uma camada fixa (canvas + balões). A camada sobrevive aos reruns do Streamlit; cada rerun só atualiza os dados.

Cada página descreve seus blocos com `_b(alvo, rotulo, pergunta_do_beto, resposta_do_floco)`. `alvo` é o começo do título
do bloco como aparece na tela ("=" na frente exige o título exato). O motor acha o título na página (inclusive dentro dos
iframes do painel), mede o cartão em volta e escolhe o bloco mais perto do centro da tela; se o mouse ficar parado sobre
um bloco, ele passa a valer.
"""
import hashlib
import json
import uuid
from functools import lru_cache
from pathlib import Path

RITMO = 1.0  # velocidade da cena de boas-vindas: 1 = normal (~25 s); 2 = o dobro da velocidade; 0.7 = mais lenta
FRONT = Path(__file__).resolve().parent / "frontend"
ARQS = ("fabrica_cena.js", "fabrica_motor.js", "fabrica_perso.js", "fabrica.css")

CAPA_CSS = """<style>
.mby-capa{position:fixed;inset:0;z-index:2147483001;background:#143a85;overflow:hidden;display:grid;place-items:center;transition:opacity .6s;animation:mbyFalha .5s 18s forwards}
.mby-capa::before{content:"";position:absolute;inset:-30px;background:var(--mby-bg,linear-gradient(#143a85,#4f8fe0)) center/cover no-repeat;filter:blur(10px)}
.mby-capa p{position:relative;color:#fff;font:800 13px "Nunito",system-ui,sans-serif;letter-spacing:.2em;text-transform:uppercase;animation:mbyPisca 1.1s ease-in-out infinite}
@keyframes mbyPisca{50%{opacity:.35}}@keyframes mbyFalha{to{opacity:0;visibility:hidden}}
</style><div class="mby-capa"><p>Entrando na fábrica…</p></div>"""


# ------------------------------------------------------------------ utilidades (sem Streamlit: testável)
def _br(x, casas=0):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _num(s) -> float:
    return float(str(s).replace("%", "").replace(".", "").replace(",", "."))


def _lista_txt(itens: list[str]) -> str:
    return ", ".join(itens[:-1]) + " e " + itens[-1] if len(itens) > 1 else (itens[0] if itens else "")


def _resumir(txt: str, limite: int = 300) -> str:
    """Corta um texto longo no fim de uma frase, sem passar do limite."""
    txt = " ".join(str(txt).split())
    if len(txt) <= limite:
        return txt
    corte = txt[:limite]
    p = corte.rfind(". ")
    return corte[:p + 1] if p > 80 else corte.rsplit(" ", 1)[0] + "…"


def _b(alvo: str, rot: str, beto: str, floco: str, cont: str | None = None) -> dict:
    """Um bloco da página: onde fica (título), o rótulo do balão, a pergunta do Beto e a explicação do Floco."""
    b = {"alvo": alvo, "rot": rot, "beto": beto, "floco": floco}
    if cont:
        b["cont"] = cont   # seletor CSS do cartão em volta do título, quando o padrão não serve
    return b


def top5(d: dict, n: int = 5) -> list[dict]:
    """As n maiores probabilidades do dia mais recente da previsão em uso (as mesmas do alerta "Atenção" desse dia)."""
    dia = d["dias"][-1]
    return [{"machine": e["machine"], "comp": e["comp"], "model": e.get("model", "–"), "prob": int(e["prob"]), "fim": dia["fimCurto"]}
            for e in dia.get("lista", [])[:n]]


# ------------------------------------------------------------------ blocos de cada página
def _bloco_atencao(dia: dict, lista: list[dict]) -> dict:
    t5 = lista[:5]
    if not t5:
        return _b("Atenção:", "Alerta do dia", "Floco, por que o alerta está vazio?",
                  "Nenhuma peça passa nos filtros da barra lateral para este dia. Afrouxe o risco mínimo ou limpe os filtros que eu mostro de novo.")
    nomes = _lista_txt([f"{e['machine']} ({e['comp']}, {e['prob']}%)" for e in t5[:3]])
    return _b("Atenção:", "Alerta do dia", "Floco, quais são as máquinas que precisam de mim primeiro?",
              f"Para até 06:00 de {dia['fimLongo']}, as que eu vejo com mais risco são {nomes}. "
              "Toque em um cartão para descer até a fila completa.")


def blocos_modelo(d: dict, dia_idx: int = 0, lista: list[dict] | None = None) -> list[dict]:
    k, cm = d["kpi"], d["cm"]
    dia = d["dias"][min(max(dia_idx, 0), len(d["dias"]) - 1)]
    lista = dia.get("lista", []) if lista is None else lista
    alto = sum(1 for e in lista if e["prob"] > 50)
    imp = [x["f"] for x in d.get("imp", [])[:3]]
    pesa = _lista_txt(imp) or "as leituras dos sensores"
    tp, fn, fp = _num(cm["tp"]), _num(cm["fn"]), _num(cm["fp"])
    pega = round(100 * tp / (tp + fn)) if tp + fn else 0
    acerta = round(100 * tp / (tp + fp)) if tp + fp else 0
    primeiro = f"Comece pela {lista[0]['machine']} ({lista[0]['comp']}): {lista[0]['prob']}%." if lista else "Hoje ninguém passa nos filtros."
    return [
        _bloco_atencao(dia, lista),
        _b("Peças em alto risco", "Alto risco", "Esse tanque cheio é ruim?",
           (f"O tanque enche com as peças acima de 50% de risco. Para {dia['fimCurto']} são {alto}; "
            "quanto mais cheio, mais trabalho para a equipe." if alto else
            f"Para {dia['fimCurto']} nenhuma peça passa de 50%: tanque baixo é dia tranquilo.")),
        _b("AUC-PR", "AUC-PR", "E esse tal de AUC-PR, Floco?",
           f"É a minha nota para achar falhas raras. Na validação tirei {k['ap']}; escolhendo ao acaso daria {k['baseline']}. "
           f"No Kaggle público a nota foi {k['apKaggle']}."),
        _b("Recall @ top-20", "Recall top-20", "Se eu olhar só as 20 primeiras da lista, perco muita coisa?",
           f"Quase nada: na validação, as 20 primeiras de cada dia pegaram {k['recall20']} das falhas que aconteceram."),
        _b("Última previsão", "Última previsão", "A previsão é de quando?",
           f"Rodo todo dia às 05:00. A última foi em {dia['execCurto']}, olhando {k['pares']} pares máquina×peça."),
        _b("Prioridade de manutenção", "Fila do dia", "Floco, e essa lista grande?",
           f"É a fila de {dia['fimLongo']}, em ordem de risco: {len(lista)} candidatas. {primeiro} A barra mostra a chance de falha até 06:00."),
        _b("Importância das variáveis", "O que eu olho", "Como você decide quem vai falhar?",
           f"Olho principalmente {pesa}. Em resumo: se a peça acabou de entrar no ciclo e se o sensor dela começou a subir."),
        _b("Precisão × recall", "Precisão × recall", "O que essa curva mostra?",
           "Se eu aviso de mais peças, pego mais falhas (recall) mas erro mais (precisão). "
           "Quanto mais a linha fica acima da tracejada, melhor do que chutar."),
        _b("Calibração", "Calibração", "Quando você diz 70%, é 70% mesmo?",
           "É isso que esta curva confere: se a linha cola na diagonal, minhas porcentagens batem com a frequência real de falhas."),
        _b("Matriz de confusão", "Acertos e erros", "E esses quatro quadrados?",
           f"Com corte em 50%: peguei {cm['tp']} falhas, deixei {cm['fn']} escaparem e dei {cm['fp']} alarmes falsos. "
           f"Ou seja, pego {pega}% das falhas e acerto {acerta}% dos alarmes."),
        _b("Raio-X da falha", "Raio-X", "Dá para ver você pensando?",
           "Dá! Aperte o play: a linha de cima é o sensor da peça e a de baixo é a evidência que eu junto hora a hora até o corte das 05:00."),
        _b("Resumo da última previsão", "Resumo", "Fechando: qual é a janela de hoje?",
           f"Das 05:00 de {dia['execCurto']} até 06:00 de {dia['fimCurto']}, cobrindo {k['maquinas']} máquinas. Boa manutenção, {{beto}}!"),
    ]


def blocos_eda(d: dict, graficos: list[dict] | None = None) -> list[dict]:
    e = d["eda"]
    kp = e["kpi"]
    pico = max(e["sinal"], key=lambda s: s["antes"])
    pp = max(e["porPeca"], key=lambda s: s["n"])
    mens = e["mensal"]
    idade = max(e["idade"], key=lambda s: s["taxa"])
    erro = max(e["erros"], key=lambda s: s["antes"])
    mod = max(e["modelos"], key=lambda s: s["falhas"])
    miss = max(_num(q["miss"]) for q in e["qualidade"])
    dia = d["dias"][-1]
    bl = [
        _bloco_atencao(dia, dia.get("lista", [])),
        _b("=Máquinas", "Frota", "Quantas máquinas a gente cuida?", f"{kp['maquinas']} máquinas: {kp['maquinasSub']}. Eu acompanho as quatro peças de cada uma."),
        _b("Falhas no período", "Falhas", "E quantas quebraram?", f"{kp['falhas']} falhas no período ({kp['falhasSub']}). É com elas que eu aprendi."),
        _b("=Manutenções", "Manutenções", "E as preventivas?", f"{kp['manut']} manutenções, seguindo a grade de 15 dias de cada peça."),
        _b("Leituras de sensores", "Sensores", "De onde vêm os dados?", f"{kp['leituras']} de leituras horárias dos sensores, vibração e clima. É o que eu leio toda madrugada."),
        _b("Sinal antes da falha", "Sinal", "Dá para ver a falha chegando?",
           f"Dá: nas 48 h antes, o sensor da peça se afasta do normal e chega a {_br(pico['antes'], 1)} desvios. É essa rampa que eu procuro."),
        _b("Falhas por peça", "Por peça", "Qual peça mais dá problema?", f"A {pp['c']}: {pp['n']} falhas no período."),
        _b("Falhas × manutenções", "Por mês", "As falhas estão aumentando?",
           f"Não: ficam entre {min(m['falhas'] for m in mens)} e {max(m['falhas'] for m in mens)} por mês, sem tendência. "
           "Mais preventivas num mês não derrubam as falhas daquele mês."),
        _b("Falhas por máquina, por idade", "Idade", "Máquina velha quebra mais?",
           f"Um pouco: na faixa de {idade['faixa']} anos são {_br(idade['taxa'], 1)} falhas por máquina, a maior taxa."),
        _b("Alertas de erro", "Erros", "Os códigos de erro avisam alguma coisa?",
           f"O {erro['e']} é o que mais avisa: {_br(erro['antes'], 0)}% aparecem nas 24 h antes de uma falha."),
        _b("Falhas por modelo", "Modelos", "Algum modelo de máquina é pior?", f"O {mod['m']}: {_br(mod['falhas'], 1)} falhas por máquina, a maior taxa."),
        _b("Qualidade da base", "Qualidade", "Dá para confiar nesses dados?",
           f"Depois do tratamento, nenhuma tabela passa de {_br(miss, 1)}% de vazios. Base limpa, previsão melhor."),
        _b("Principais análises", "Principais", "Por que só esses gráficos?",
           "São os sete que mais explicam as falhas. Cada um tem um botão Insight com a conclusão; o resto da Etapa 3 fica logo abaixo.", cont=".ga-tit"),
        _b("Todas as análises da Etapa 3", "Galeria", "E se eu quiser ver tudo?",
           "Abra Ver todas as análises: são os 23 gráficos da Etapa 3, separados por tema. Clique na imagem para ampliar e "
           "passe o mouse em cima de um que eu explico.", cont=".ga"),
    ]
    perguntas = ["E esse gráfico?", "O que esse aqui mostra?", "Floco, me explica esse?", "E este, o que diz?"]
    for i, g in enumerate(graficos or []):
        bl.append(_b("=" + g["titulo"], f"Gráfico {g['n']}", perguntas[i % len(perguntas)], _resumir(g.get("insight", ""))))
    return bl


def blocos_maquinas() -> list[dict]:
    return [
        _b("Replay da frota", "Replay", "Que mapa é esse, Floco?",
           "É a fábrica inteira em 2023. Cada bomba é uma máquina e a cor é o risco que eu dei às 05:00. "
           "Quando quebra de verdade, ela pulsa: verde se eu tinha avisado, vermelho se escapou."),
        _b("Ficha da máquina", "Ficha", "E a ficha da máquina?",
           "Cadastro da máquina escolhida e o maior risco que eu dei para ela no período de teste. "
           "Troque de máquina no seletor do topo da página ou na barra lateral; as setas percorrem a frota."),
        _b("Risco previsto no período de teste", "Risco no teste", "O que são essas bolinhas?",
           "Cada bolinha é um dia de grade de uma peça. Quanto maior, mais risco eu vejo. Fora desses dias o risco é quase zero."),
        _b("=Histórico", "Histórico", "E o passado dela?",
           "Falhas por peça, a última preventiva com a próxima data de grade e os códigos de erro. Ajuda a entender o meu palpite."),
        _b("Sensores ·", "Sensores", "E esse sobe e desce?",
           "É o sensor da peça hora a hora. Antes de uma falha ele costuma subir de patamar por 40 a 65 h; a troca derruba o sinal. "
           "Tracejado vermelho é falha."),
    ]


def blocos_dados() -> list[dict]:
    return [
        _b("Bases tratadas", "Bases", "Floco, de onde você tira tudo isso?",
           "Destas tabelas, já limpas na Etapa 2. Escolha a tabela no topo e filtre por máquina, período e colunas."),
        _b("Linhas no recorte", "Recorte", "Quanta coisa tem aqui?", "Os cartões contam linhas, colunas, máquinas e o período do recorte que você filtrou."),
        _b("=Tabela", "Tabela", "E como eu acho uma linha específica?",
           "Pela barra lateral: ordene, vá direto a uma linha ou coluna, ou busque um valor como M048 ou E3. "
           "O dicionário explica cada coluna e a última aba conta o que foi tratado.", cont='[data-testid="stTabs"]'),
    ]


def blocos_sim() -> list[dict]:
    return [
        _b("E se a fábrica tivesse seguido o modelo", "Simulador", "Floco, valeu a pena seguir você?",
           "Vamos testar! Este simulador repete 2023 com as falhas reais e os riscos que eu dei às 05:00 de cada dia."),
        _b("=Política", "Política", "O que eu mexo aqui?",
           "O limiar diz a partir de quanto risco a preventiva é antecipada; a capacidade, quantas a equipe faz por dia. "
           "Os custos são premissas: ajuste à realidade da planta."),
        _b("Economia vs. só a grade", "Resultado", "E aí, economizou?",
           "Estes cartões comparam com seguir só a grade de 15 dias: economia, falhas evitadas, antecipações e retorno por real investido.",
           cont=".sm-kpis"),
        _b("Custo acumulado", "Custo no ano", "Por que três linhas?",
           "Vermelho é seguir só a grade, amarelo é antecipar ao acaso e azul é antecipar pela minha lista. A distância entre o amarelo e o azul é o valor da ordem que eu dou."),
        _b("Custo total × limiar", "Limiar ótimo", "Qual limiar eu escolho?",
           "O ponto verde é o mais barato. Limiar baixo gasta com antecipação à toa; alto deixa falha passar. Clique na curva para testar."),
        _b("Distribuição da economia", "Incerteza", "E se der azar?",
           "Cada barra junta cenários de Monte Carlo: azul seguindo a minha lista, amarelo ao acaso. Se quase tudo fica à direita do zero, a economia é segura."),
        _b("Mapa de decisão", "Mapa", "E esse quadriculado?",
           "Cada célula é uma combinação de limiar e equipe. Verde economiza, vermelho custa mais que a grade. Clique para aplicar."),
    ]


def configurar(d: dict, aba: str, nome: str = "", dia_idx: int = 0, tok: str = "", intro: bool = False, fonte: str = "",
               lista: list[dict] | None = None, graficos: list[dict] | None = None) -> dict:
    if aba == "model":
        blocos = blocos_modelo(d, dia_idx, lista)
    elif aba == "eda":
        blocos = blocos_eda(d, graficos)
    elif aba == "maquinas":
        blocos = blocos_maquinas()
    elif aba == "dados":
        blocos = blocos_dados()
    elif aba == "sim":
        blocos = blocos_sim()
    else:
        blocos = []
    k = d["kpi"]
    return {"tok": tok, "intro": intro, "aba": aba, "nome": nome, "fonte": fonte or "o arquivo mais recente da base", "top5": top5(d),
            "dia": d["dias"][-1]["fimLongo"], "pares": k.get("pares"), "blocos": blocos, "ritmo": RITMO}


# ------------------------------------------------------------------ motor JS e HTML do injetor
@lru_cache(maxsize=4)
def _motor(chave: str) -> tuple[str, str]:
    cena, motor, perso, css = [(FRONT / n).read_text(encoding="utf-8") for n in ARQS]
    versao = hashlib.md5((cena + motor + perso + css).encode()).hexdigest()[:10]
    motor = motor.replace("'@@VERSAO@@'", json.dumps(versao)).replace("'@@CSS@@'", json.dumps(css))
    return versao, "(function(){'use strict';\n" + cena + "\n" + motor + "\n" + perso + "\nboot();\n})();"


def motor_js() -> tuple[str, str]:
    return _motor("|".join(f"{n}:{(FRONT / n).stat().st_mtime_ns}" for n in ARQS))


def gerar_html(cfg: dict) -> str:
    versao, js = motor_js()
    dados = json.dumps(cfg, ensure_ascii=True).replace("</", "<\\/")
    fonte = json.dumps(js, ensure_ascii=True).replace("</", "<\\/")
    return f"""<!doctype html><html><body><script>
(function () {{
  var P = window.parent, cfg = {dados}, ver = "{versao}";
  try {{
    if (!P.__MBY || P.__MBY.versao !== ver) {{
      if (P.__MBY) P.__MBY.destruir();
      var s = P.document.createElement("script"); s.textContent = {fonte}; P.document.head.appendChild(s); s.remove();
    }}
    P.__MBY.atualizar(cfg);
  }} catch (e) {{ console.error("MaBiYama · animação:", e); }}
}})();
</script></body></html>"""


# ------------------------------------------------------------------ integração com o Streamlit
def _st():
    import streamlit as st
    return st


def html_iframe(html: str, altura: int, **kw):
    """st.iframe (Streamlit recente) com fallback para components.html (versões antigas)."""
    st = _st()
    if hasattr(st, "iframe"):
        st.iframe(html, height=altura, **kw)
    else:
        import streamlit.components.v1 as components
        components.html(html, height=altura, scrolling=False)


def capa():
    """Cobre a tela com o fundo da animação enquanto o painel carrega (evita o "pisca" do painel antes da cena)."""
    st = _st()
    tok = st.session_state.setdefault("mby_tok", uuid.uuid4().hex)
    if st.session_state.get("mby_tocado") != tok:
        st.markdown(CAPA_CSS, unsafe_allow_html=True)


def login():
    """Na tela de login: carrega o motor (fica pronto para a entrada) sem desenhar nada por cima da tela."""
    html_iframe(gerar_html({"modo": "login"}), 1, alt="mby")


def reiniciar():
    """Faz a animação tocar de novo no próximo rerun (botão "Rever animação"), desde a fábrica vista de fora."""
    _st().session_state.mby_tok = uuid.uuid4().hex


def personalizar():
    """Abre o painel de personalização do operário no próximo rerun (botão "Personalizar operário")."""
    _st().session_state.mby_perso = uuid.uuid4().hex


def montar(d: dict, aba: str, dia_idx: int = 0, lista: list[dict] | None = None, graficos: list[dict] | None = None):
    st = _st()
    tok = st.session_state.setdefault("mby_tok", uuid.uuid4().hex)
    intro = st.session_state.get("mby_tocado") != tok
    fonte = "arquivo enviado nesta sessão" if st.session_state.get("previsao") else "última previsão do time"
    gr = [{"n": g["n"], "titulo": g["titulo"], "insight": g.get("insight", "")} for g in (graficos or [])]
    cfg = configurar(d, aba, st.session_state.get("usuario", {}).get("nome", ""), dia_idx, tok, intro, fonte, lista, gr)
    if st.session_state.get("mby_perso"):
        cfg["abrirPerso"] = st.session_state.pop("mby_perso")
    html_iframe(gerar_html(cfg), 1, alt="mby")
    st.session_state.mby_tocado = tok
