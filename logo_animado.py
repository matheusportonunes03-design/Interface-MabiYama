"""Logo da MaBiYama animada (SVG + CSS, sem JavaScript).

Roteiro (~3,2 s): a água entra ondulando; a engrenagem cai do céu girando, quica e respinga ao tocar a água; a bomba sobe de
dentro da água (com respingos e as gotas saltando à direita); o nome aparece num corte da esquerda para a direita e o slogan
sobe. Depois fica em repouso animado: a engrenagem gira devagar, a água balança e a bomba boia.

A engrenagem é desenhada em vetor (14 dentes, ajustada à arte original) para poder girar inteira; as outras partes são
recortes da logo original (versões clara e escura, em alta resolução) servidos de static/logo/ (enableStaticServing),
baixados uma vez por navegador. caixas.json guarda onde cada recorte fica na arte; superficie.json, a linha da água.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

PASTA = Path(__file__).resolve().parent / "static" / "logo"
W, H = 1294, 758
CX, CY = 497.5, 270.0                      # centro da engrenagem na arte original
R_PONTA, R_BASE, R_FURO, DENTES, FASE = 270, 240, 199, 14, -174


def _engrenagem() -> str:
    """Contorno dos dentes + furo central (evenodd)."""
    passo = 360 / DENTES
    pts = []
    for i in range(DENTES):
        c = FASE + i * passo
        for ang, r in ((c - passo / 2 + 1.2, R_BASE), (c - 8.2, R_BASE), (c - 5.6, R_PONTA), (c + 5.6, R_PONTA), (c + 8.2, R_BASE)):
            a = math.radians(ang)
            pts.append(f"{CX + r * math.cos(a):.1f},{CY + r * math.sin(a):.1f}")
    furo = (f"M{CX + R_FURO},{CY} a{R_FURO},{R_FURO} 0 1,0 {-2 * R_FURO},0 a{R_FURO},{R_FURO} 0 1,0 {2 * R_FURO},0 Z")
    return "M" + " L".join(pts) + " Z " + furo


@lru_cache(maxsize=1)
def _meta():
    caixas = json.loads((PASTA / "caixas.json").read_text())
    sup = json.loads((PASTA / "superficie.json").read_text())
    return caixas, sup


def _setor() -> str:
    """Setor da engrenagem que aparece na arte original (da esquerda-baixo, pelo topo, até perto da alça da bomba)."""
    pts = [f"{CX},{CY}"]
    for ang in range(-58, -196, -4):
        a = math.radians(ang)
        pts.append(f"{CX + 420 * math.cos(a):.0f},{CY + 420 * math.sin(a):.0f}")
    return " ".join(pts)


def _clip_superficie(folga: float) -> str:
    """Polígono de tudo o que fica acima da superfície da água (menos uma folga)."""
    _, sup = _meta()
    pts = [f"{x},{min(y - folga, H)}" for x, y in sup] + [f"{W},{min(sup[-1][1] - folga, H)}"]
    return f"0,-1200 {W},-1200 " + " ".join(reversed(pts))


CSS = """<style>
.lga{display:block;width:100%;height:auto;overflow:visible}
.lga *{transform-box:view-box}
.lga .eng-cai{transform-origin:497.5px 270px;animation:lgaCai 1.3s cubic-bezier(.55,0,1,.45) .25s both}
.lga .eng-gira{transform-origin:497.5px 270px;animation:lgaGira 18s linear 1.55s infinite}
.lga .bomba-sobe{transform-origin:669px 230px;animation:lgaSobe 1.15s cubic-bezier(.2,.75,.25,1) 1.3s both}
.lga .eng-tudo{animation:lgaSome .35s ease-out 2.05s both}
.lga .bomba-boia{animation:lgaBoia 4.2s ease-in-out 2.6s infinite}
.lga .ag-in{animation:lgaAguaIn 1s cubic-bezier(.3,.7,.2,1) both}
.lga .ag-in.b{animation-delay:.08s}.lga .ag-in.c{animation-delay:.18s}
.lga .ag-a{animation:lgaBal 4.6s ease-in-out 1s infinite}
.lga .ag-b{animation:lgaBal 3.8s ease-in-out 1s infinite reverse}
.lga .ag-c{animation:lgaBal2 4.2s ease-in-out 1.2s infinite}
.lga .gotas{transform-origin:1175px 300px;animation:lgaGotas .75s cubic-bezier(.2,1.4,.4,1) 1.75s both}
.lga .gotas image{animation:lgaGotasBoia 3s ease-in-out 2.6s infinite}
.lga .nome{animation:lgaNome .85s cubic-bezier(.3,.7,.2,1) 2.2s both}
.lga .slogan{animation:lgaSlogan .7s ease-out 2.75s both}
.lga .sp{opacity:0;animation:lgaSp .8s cubic-bezier(.2,.7,.3,1) both}
.lga .rp{opacity:0;fill:none;stroke-width:5;animation:lgaRp 1s ease-out both}
@keyframes lgaCai{0%{transform:translateY(-1150px) rotate(-240deg);opacity:0}6%{opacity:1}
  60%{transform:translateY(0) rotate(0);animation-timing-function:cubic-bezier(.2,.6,.4,1)}
  73%{transform:translateY(-38px) rotate(10deg);animation-timing-function:cubic-bezier(.6,0,1,.6)}
  85%{transform:translateY(0) rotate(0);animation-timing-function:ease-out}93%{transform:translateY(-9px)}100%{transform:none;opacity:1}}
@keyframes lgaSome{to{opacity:0}}
@keyframes lgaGira{to{transform:rotate(360deg)}}
@keyframes lgaSobe{0%{transform:translateY(400px) rotate(-4deg)}62%{transform:translateY(-20px) rotate(1.2deg)}82%{transform:translateY(5px) rotate(-.4deg)}100%{transform:none}}
@keyframes lgaBoia{0%,100%{transform:none}50%{transform:translateY(-5px) rotate(-.6deg)}}
@keyframes lgaAguaIn{0%{transform:translateX(-90px) scaleY(.4);opacity:0;clip-path:inset(0 100% 0 0)}100%{transform:none;opacity:1;clip-path:inset(0 0 0 0)}}
@keyframes lgaBal{0%,100%{transform:translateX(0)}50%{transform:translateX(9px) translateY(-2px)}}
@keyframes lgaBal2{0%,100%{transform:translateX(0)}50%{transform:translateX(-8px) translateY(2px)}}
@keyframes lgaGotas{0%{transform:translate(-120px,90px) scale(.2) rotate(-25deg);opacity:0}30%{opacity:1}100%{transform:none;opacity:1}}
@keyframes lgaGotasBoia{0%,100%{transform:none}50%{transform:translate(4px,-6px)}}
@keyframes lgaNome{0%{clip-path:inset(0 100% 0 0);transform:translateY(18px);opacity:.2}100%{clip-path:inset(0 0 0 0);transform:none;opacity:1}}
@keyframes lgaSlogan{0%{transform:translateY(16px);opacity:0}100%{transform:none;opacity:1}}
@keyframes lgaSp{0%{opacity:0;transform:translate(0,0) scale(.4)}12%{opacity:1}100%{opacity:0;transform:translate(var(--dx),var(--dy)) scale(1)}}
@keyframes lgaRp{0%{opacity:.9;transform:scale(.2)}100%{opacity:0;transform:scale(1.25)}}
@media (prefers-reduced-motion:reduce){.lga *{animation:none!important}}
</style>"""


def _respingos(x0: float, x1: float, y: float, t0: float, n: int, cor: str) -> str:
    """Gotinhas que saltam da superfície (posições determinísticas para o HTML não mudar entre reruns)."""
    out = []
    for i in range(n):
        f = (i + .5) / n
        x = x0 + (x1 - x0) * f
        dx = (f - .5) * 160 + (17 * i % 7 - 3) * 6
        dy = -(70 + (37 * i % 9) * 11)
        r = 7 + (i * 5 % 4) * 2.5
        out.append(f'<circle class="sp" cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{cor}" '
                   f'style="--dx:{dx:.0f}px;--dy:{dy:.0f}px;animation-delay:{t0 + (i % 4) * .03:.2f}s;transform-origin:{x:.0f}px {y:.0f}px"/>')
    return "".join(out)


def html(variante: str = "claro", uid: str = "lg") -> str:
    """SVG pronto para st.markdown(..., unsafe_allow_html=True). variante: 'claro' (fundo claro) ou 'escuro'."""
    caixas, _ = _meta()

    def img(nome, cls=""):
        x0, y0, x1, y1 = caixas[nome]
        return (f'<image class="{cls}" href="app/static/logo/{variante}_{nome}.webp" x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" '
                f'preserveAspectRatio="none"/>')

    cor_sp = "#bfe6ff" if variante == "escuro" else "#4aa8e6"
    return CSS + f"""<svg class="lga" viewBox="0 -40 {W} {H + 40}" role="img" aria-label="MaBiYama · Bombas e Sistemas Hidráulicos">
<defs>
  <linearGradient id="{uid}-eng" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fbb53b"/><stop offset=".55" stop-color="#ef9c1d"/><stop offset="1" stop-color="#df8714"/></linearGradient>
  <clipPath id="{uid}-cg"><polygon points="{_clip_superficie(13)}"/></clipPath>
  <mask id="{uid}-ms" maskUnits="userSpaceOnUse" x="-200" y="-1400" width="1700" height="2300">
    <polygon points="{_setor()}" fill="#fff"/><rect class="eng-tudo" x="-200" y="-1400" width="1700" height="2300" fill="#fff"/></mask>
  <clipPath id="{uid}-cb"><polygon points="{_clip_superficie(4)}"/></clipPath>
  <filter id="{uid}-onda" x="-4%" y="-25%" width="108%" height="150%">
    <feTurbulence type="fractalNoise" baseFrequency="0.011 0.045" numOctaves="1" seed="4" result="n">
      <animate attributeName="baseFrequency" dur="7s" values="0.011 0.045;0.014 0.06;0.011 0.045" repeatCount="indefinite"/></feTurbulence>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="0" xChannelSelector="R" yChannelSelector="G">
      <animate attributeName="scale" begin="0.9s" dur="1.2s" from="0" to="9" fill="freeze"/></feDisplacementMap>
  </filter>
</defs>
<g clip-path="url(#{uid}-cg)"><g mask="url(#{uid}-ms)"><g class="eng-cai">
  <g class="eng-gira"><path d="{_engrenagem()}" fill="url(#{uid}-eng)" fill-rule="evenodd"/></g>
  {img("crescente")}
</g></g></g>
<g clip-path="url(#{uid}-cb)"><g class="bomba-sobe"><g class="bomba-boia">{img("bomba")}</g></g></g>
<g filter="url(#{uid}-onda)">
  <g class="ag-in a">{img("agua_a", "ag-a")}</g><g class="ag-in b">{img("agua_b", "ag-b")}</g><g class="ag-in c">{img("agua_c", "ag-c")}</g>
</g>
<ellipse class="rp" cx="300" cy="338" rx="120" ry="22" stroke="{cor_sp}" style="animation-delay:1.03s;transform-origin:300px 338px"/>
<ellipse class="rp" cx="680" cy="400" rx="260" ry="34" stroke="{cor_sp}" style="animation-delay:1.65s;transform-origin:680px 400px"/>
{_respingos(220, 380, 336, 1.02, 8, cor_sp)}
{_respingos(470, 900, 395, 1.62, 12, cor_sp)}
<g class="gotas">{img("gotas")}</g>
{img("nome", "nome")}
{img("slogan", "slogan")}
</svg>"""
