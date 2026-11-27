"""Logo da MaBiYama recriada em vetor e animada (página para components.html).

Tudo é vetor: a engrenagem é paramétrica (14 dentes, para girar inteira); o nome e o slogan são contornos da fonte Exo 2
(Black Itálico e SemiBold Itálico), que bate com o desenho original; a bomba, o crescente e as gotas são vetores suaves em
quatro tons com gradientes; a água são faixas de curvas que o script recalcula a cada quadro para ondular.
Geometria em frontend/marca/logo_vetor.json; animação em frontend/logo_anim.js (física simples a 60 qps).

Roteiro (~3,5 s): a água entra desenhando as faixas; a engrenagem cai do céu com gravidade, quica e respinga; a bomba sobe de
dentro da água numa mola amortecida, com respingos e as gotas saltando; um brilho atravessa a bomba; o nome entra num corte
da esquerda para a direita e o slogan sobe. Depois a engrenagem gira devagar, a água ondula e a bomba boia.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

FRONT = Path(__file__).resolve().parent / "frontend"
CX, CY = 497.5, 270.0
R_PONTA, R_BASE, R_FURO, DENTES, FASE = 270, 240, 199, 14, -174
VB = (0, -150, 1294, 908)          # espaço acima da arte para a engrenagem cair

PALETAS = {
    "claro": dict(eng=("#fcb83f", "#f09d1e", "#dc8412"), cres="#0b2a5e", base=("#0f3270", "#081d47"), mid=("#2a70cc", "#1a4f9f"),
                  light=("#64aef0", "#3f89d8"), white=("#ffffff", "#d3e8ff"), gota=("#3cb0ee", "#1482d0"),
                  a=("#0a58a3", "#0c69b9"), b=("#0b5fae", "#1384d2", "#20a0e2"), c=("#1489d4", "#2cabea"), fio=("#1a86d2", "#2aa6e6"),
                  nome=("#5b1d7e", "#3c1056"), slogan="#3b2d4f", linha="#e59c14"),
    "escuro": dict(eng=("#ffc14f", "#f5a52a", "#e38c18"), cres="#3b78e0", base=("#1d4ea6", "#123477"), mid=("#3a86e8", "#2566c4"),
                   light=("#7cc0ff", "#55a2f0"), white=("#ffffff", "#e3f1ff"), gota=("#5cc4f7", "#2898e3"),
                   a=("#1670c8", "#1a7fd6"), b=("#1678d0", "#2697e6", "#43b6f3"), c=("#2aa1ea", "#55c3f6"), fio=("#2f9ce6", "#4cbaf3"),
                   nome=("#dba6f7", "#b87de9"), slogan="#d3c0f0", linha="#f2a93a"),
}


def _engrenagem() -> str:
    passo = 360 / DENTES
    pts = []
    for i in range(DENTES):
        c = FASE + i * passo
        for ang, r in ((c - passo / 2 + 1.2, R_BASE), (c - 8.4, R_BASE), (c - 6.2, R_PONTA - 6), (c - 5.0, R_PONTA), (c + 5.0, R_PONTA),
                       (c + 6.2, R_PONTA - 6), (c + 8.4, R_BASE)):
            a = math.radians(ang)
            pts.append(f"{CX + r * math.cos(a):.1f},{CY + r * math.sin(a):.1f}")
    furo = f"M{CX + R_FURO},{CY} a{R_FURO},{R_FURO} 0 1,0 {-2 * R_FURO},0 a{R_FURO},{R_FURO} 0 1,0 {2 * R_FURO},0 Z"
    return "M" + " L".join(pts) + " Z " + furo


def _setor() -> str:
    """Setor da engrenagem visível na arte original (da esquerda-baixo, pelo topo, até perto da alça da bomba)."""
    pts = [f"{CX},{CY}"]
    for ang in range(-63, -196, -4):
        a = math.radians(ang)
        pts.append(f"{CX + 430 * math.cos(a):.0f},{CY + 430 * math.sin(a):.0f}")
    return " ".join(pts)


@lru_cache(maxsize=2)
def _geo(versao: int) -> dict:
    return json.loads((FRONT / "marca" / "logo_vetor.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=2)
def _js(versao: int) -> str:
    return (FRONT / "logo_anim.js").read_text(encoding="utf-8")


def _superficie(geo: dict, folga: float) -> str:
    sup = geo["superficie"]
    pts = [f"{x},{y - folga:.0f}" for x, y in sup]
    return f"-50,-2000 1344,-2000 1344,{sup[-1][1] - folga:.0f} " + " ".join(reversed(pts)) + f" -50,{sup[0][1] - folga:.0f}"


def _grad(id_, cores, vertical=True) -> str:
    x2, y2 = ("0", "1") if vertical else ("1", "0")
    paradas = "".join(f'<stop offset="{i / (len(cores) - 1):.2f}" stop-color="{c}"/>' for i, c in enumerate(cores))
    return f'<linearGradient id="{id_}" x1="0" y1="0" x2="{x2}" y2="{y2}">{paradas}</linearGradient>'


def html(variante: str = "claro", esquema: str = "light") -> str:
    """Página completa (fundo transparente) para st.components.v1.html. esquema: color-scheme da página que a embute
    (se for diferente, o navegador pinta um fundo opaco atrás do iframe)."""
    v = int((FRONT / "marca" / "logo_vetor.json").stat().st_mtime_ns + (FRONT / "logo_anim.js").stat().st_mtime_ns)
    geo, js, P = _geo(v), _js(v), PALETAS["escuro" if variante == "escuro" else "claro"]
    b = geo["bomba"]
    (le, ld) = geo["linhas"][:2] if len(geo["linhas"]) >= 2 else ([7, 721, 132, 732], [1161, 721, 1286, 732])
    defs = "".join([
        _grad("gEng", P["eng"]), _grad("gBase", P["base"]), _grad("gMid", P["mid"]), _grad("gLight", P["light"]), _grad("gWhite", P["white"]),
        _grad("gGota", P["gota"]), _grad("gA", P["a"], False), _grad("gB", P["b"], False), _grad("gC", P["c"], False), _grad("gFio", P["fio"], False),
        _grad("gNome", P["nome"]),
        '<linearGradient id="gBrilho" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>',
        f'<clipPath id="clipEng"><polygon points="{_superficie(geo, 13)}"/></clipPath>',
        f'<clipPath id="clipBomba"><polygon points="{_superficie(geo, 4)}"/></clipPath>',
        f'<clipPath id="clipBrilho"><path d="{b["base"]}"/></clipPath>',
        '<clipPath id="clipNome"><rect id="clip-nome-r" x="-10" y="470" width="0" height="215"/></clipPath>',
        f'<mask id="mSetor" maskUnits="userSpaceOnUse" x="-300" y="-1600" width="1900" height="2600"><polygon points="{_setor()}" fill="#fff"/>'
        '<rect class="tudo" x="-300" y="-1600" width="1900" height="2600" fill="#fff"/></mask>',
    ])
    svg = f"""<svg viewBox="{' '.join(map(str, VB))}" preserveAspectRatio="xMidYMax meet" role="img" aria-label="MaBiYama · Bombas e Sistemas Hidráulicos">
<defs>{defs}</defs>
<g clip-path="url(#clipEng)"><g mask="url(#mSetor)"><g id="eng" opacity="0">
  <g id="eng-giro"><path d="{_engrenagem()}" fill="url(#gEng)" fill-rule="evenodd"/></g>
  <path d="{geo['crescente']}" fill="{P['cres']}" fill-rule="evenodd"/>
</g></g></g>
<g clip-path="url(#clipBomba)"><g id="bomba-mov" transform="translate(0,440)">
  <path d="{b['base']}" fill="url(#gBase)" fill-rule="evenodd"/><path d="{b['mid']}" fill="url(#gMid)" fill-rule="evenodd"/>
  <path d="{b['light']}" fill="url(#gLight)" fill-rule="evenodd"/><path d="{b['white']}" fill="url(#gWhite)" fill-rule="evenodd"/>
  <g clip-path="url(#clipBrilho)"><rect id="brilho" x="380" y="-20" width="170" height="480" fill="url(#gBrilho)" opacity="0"/></g>
</g></g>
<path id="ag-a" fill="url(#gA)"/><path id="ag-b" fill="url(#gB)"/><path id="ag-fio" fill="url(#gFio)"/><path id="ag-c" fill="url(#gC)"/>
<g id="gotas" opacity="0"><path d="{geo['gotas']}" fill="url(#gGota)" fill-rule="evenodd"/></g>
<g id="respingos"></g>
<g clip-path="url(#clipNome)"><g id="nome"><path d="{geo['nome']['d']}" transform="{geo['nome']['t']}" fill="url(#gNome)"/></g></g>
<g id="slogan" opacity="0"><path d="{geo['slogan']['d']}" transform="{geo['slogan']['t']}" fill="{P['slogan']}"/></g>
<rect id="lin-e" x="{le[0]}" y="{le[1]}" width="{le[2] - le[0]}" height="{le[3] - le[1] + 1}" rx="5.5" fill="{P['linha']}" transform="scale(0 1)"/>
<rect id="lin-d" x="{ld[0]}" y="{ld[1]}" width="{ld[2] - ld[0]}" height="{ld[3] - ld[1] + 1}" rx="5.5" fill="{P['linha']}" transform="scale(0 1)"/>
</svg>"""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:transparent;overflow:hidden}}
svg{{display:block;width:100%;height:100vh}}
.tudo{{animation:some .35s ease-out 1.6s both}}@keyframes some{{to{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.tudo{{animation:none;opacity:0}}#bomba-mov{{transform:none}}#gotas,#slogan,#eng{{opacity:1}}#lin-e,#lin-d{{transform:none}}}}
</style></head><body>{svg}
<script>window.LOGO_GEO={json.dumps({"agua": geo["agua"]}, separators=(",", ":"))};</script><script>{js}</script></body></html>"""


def altura(largura: int) -> int:
    """Altura do componente para uma largura em px (mantém a proporção do viewBox)."""
    return int(round(largura * VB[3] / VB[2]))
