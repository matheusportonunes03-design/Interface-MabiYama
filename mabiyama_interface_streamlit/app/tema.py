"""Aparência do painel: modo claro/escuro, marca na barra lateral, navegação e ondas animadas (fluxo de água)."""
from pathlib import Path
from urllib.parse import quote

import streamlit as st

RAIZ = Path(__file__).resolve().parent
MARCA = RAIZ / "frontend" / "marca"

# ------------------------------------------------------------------ paleta escura (mesmas variáveis do tema claro do Lovable)
VARS_ESCURO = """
  --background: oklch(17.5% .032 262); --foreground: oklch(95% .01 250); --card: oklch(22% .038 262);
  --border: oklch(31% .04 262); --input: oklch(35% .04 262); --ring: oklch(55% .08 258);
  --muted: oklch(26.5% .038 262); --muted-foreground: oklch(73% .03 255);
  --secondary: oklch(26.5% .038 262); --secondary-foreground: oklch(93% .01 250); --accent: oklch(29% .045 262);
  --primary: oklch(32% .06 262); --primary-foreground: oklch(98.4% .003 247.858);
  --brand: oklch(66% .17 254); --brand-deep: oklch(60% .17 258); --brand-sky: oklch(78% .1 228);
  --violet: oklch(74% .13 300); --violet-soft: oklch(31% .07 300); --amber: oklch(80% .15 72); --success: oklch(73% .15 155);
  --chart-1: oklch(66% .17 254); --chart-2: oklch(80% .15 72); --chart-3: oklch(74% .13 300); --chart-4: oklch(78% .1 228);
  --chart-5: oklch(68% .19 25);
  --gradient-header: linear-gradient(100deg, oklch(23% .08 264), oklch(36% .14 259) 58%, oklch(50% .11 232));
  --shadow-card: 0 6px 18px -8px rgb(0 0 0 / .55);
  color-scheme: dark;
"""


def escuro() -> bool:
    return st.session_state.get("tema", "claro") == "escuro"


def classe_html() -> str:
    return "dark" if escuro() else ""


def css_iframe() -> str:
    """Estilo extra das páginas em iframe (painel React e simulador) no modo escuro."""
    if not escuro():
        return ""
    return (":root{" + VARS_ESCURO + "}"
            ".recharts-default-tooltip{background:var(--card)!important;border-color:var(--border)!important;color:var(--foreground)}"
            ".recharts-cartesian-grid line{stroke:var(--border)}"
            "img[src*='webp']{filter:brightness(.9) contrast(1.05);border-radius:.5rem}")


# ------------------------------------------------------------------ ondas (fluxo de água)
def _onda(fill: str, opac: float, amp: int, fase: int = 0) -> str:
    y = 40
    d = f"M0 {y} " + " ".join(f"Q {150 + 600 * k + fase} {y - amp} {300 + 600 * k + fase} {y} T {600 + 600 * k + fase} {y}" for k in range(2))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 80" preserveAspectRatio="none">'
           f'<path d="{d} V80 H0Z" fill="{fill}" fill-opacity="{opac}"/></svg>')
    return "url(\"data:image/svg+xml," + quote(svg) + "\")"


def _borda(amp: int = 11) -> str:
    """Máscara da borda inferior ondulada (área opaca acima da curva)."""
    d = "M0 16 " + " ".join(f"Q {150 + 600 * k} {16 - amp} {300 + 600 * k} 16 T {600 + 600 * k} 16" for k in range(2)) + " V0 H0Z"
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 30" preserveAspectRatio="none"><path d="{d}" fill="black"/></svg>'
    return "url(\"data:image/svg+xml," + quote(svg) + "\")"


BORDA = _borda()
ONDAS = ", ".join([_onda("#ffffff", .10, 16), _onda("#ffffff", .08, 22), _onda("#bfe6ff", .12, 12)])
GOTA = ("data:image/svg+xml," + quote('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" '
                                      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/></svg>'))


ICONES_SECAO = {
    "nav": '<path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z"/><circle cx="12" cy="12" r="10"/>',
    "dia": '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    "eda": '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "modelo": '<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/>',
    "sim": '<path d="M10 5H3"/><path d="M12 19H3"/><path d="M14 3v4"/><path d="M16 17v4"/><path d="M21 12h-9"/><path d="M21 19h-5"/><path d="M21 5h-7"/><path d="M8 10v4"/><path d="M8 12H3"/>',
    "maq": '<path d="M3 19a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.5a.5.5 0 0 0-.769-.422l-4.462 2.844A.5.5 0 0 1 15 10.5v-2a.5.5 0 0 0-.769-.422L9.77 10.922A.5.5 0 0 1 9 10.5V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2z"/>',
    "sensor": '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
    "tabela": '<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/>',
    "tema": '<circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>',
    "gota": '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>',
}


def _ico(paths: str) -> str:
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" '
           f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')
    return "data:image/svg+xml," + quote(svg)


ICONES_NAV = [   # na ordem das abas
    _ico('<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
    _ico('<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>'),
    _ico('<path d="M10 5H3"/><path d="M12 19H3"/><path d="M14 3v4"/><path d="M16 17v4"/><path d="M21 12h-9"/><path d="M21 19h-5"/><path d="M21 5h-7"/><path d="M8 10v4"/><path d="M8 12H3"/>'),
    _ico('<path d="M12 16h.01"/><path d="M16 16h.01"/><path d="M3 19a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.5a.5.5 0 0 0-.769-.422l-4.462 2.844A.5.5 0 0 1 15 10.5v-2a.5.5 0 0 0-.769-.422L9.77 10.922A.5.5 0 0 1 9 10.5V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2z"/><path d="M8 16h.01"/>'),
    _ico('<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/>'),
    _ico('<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>'),
]


SOL = '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>'
LUA = '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>'


def css_tema():
    """CSS comum (navegação, marca, ondas) e, no modo escuro, as variáveis e os ajustes dos componentes do Streamlit."""
    nav_icones = "".join(
        f'.st-key-navbox [role="radiogroup"] > div:nth-child({i + 1}) [data-testid="stRadioOption"]::before {{ -webkit-mask-image: url("{u}"); mask-image: url("{u}"); }}'
        for i, u in enumerate(ICONES_NAV))
    css = f"""
:root {{ --brand-sky: oklch(80% .09 230); --violet: oklch(45% .15 300); --violet-soft: oklch(95% .03 300); --amber: oklch(78% .16 70);
  --success: oklch(65% .15 155); --chart-5: oklch(60% .2 25); --radius: .75rem; }}
/* ---------- marca na barra lateral */
.st-key-marca {{ gap: .35rem !important; padding-top: .25rem; }}
.st-key-marca [data-testid="stImage"], .st-key-marca [data-testid="stImageContainer"] {{ display: flex; justify-content: center; }}
.st-key-marca img {{ max-width: 210px !important; width: 100% !important; margin: 0 auto; filter: drop-shadow(0 4px 10px rgb(0 40 120 / .12)); }}
[data-testid="stSidebar"] p.lb-user {{ font-size: .75rem !important; line-height: 1.1rem; }}
.lb-user {{ display: flex; align-items: center; justify-content: center; gap: .4rem; font-size: .75rem; color: var(--muted-foreground);
  font-weight: 700; letter-spacing: .02em; margin: 0; }}
.lb-user i {{ width: 6px; height: 6px; border-radius: 99px; background: var(--success); box-shadow: 0 0 0 3px color-mix(in oklab, var(--success) 25%, transparent); }}
.lb-onda {{ height: 22px; margin: .4rem -1.1rem 0; background-image: {_onda("#3b82f6", .20, 26)}, {_onda("#38bdf8", .16, 18)};
  background-size: 520px 22px, 360px 22px; background-repeat: repeat-x; animation: fluxo 9s linear infinite; }}
@keyframes fluxo {{ to {{ background-position: 600px 0, -400px 0; }} }}

/* ---------- navegação (itens achatados com ícone e marcador lateral) */
.st-key-navbox [data-testid="stElementContainer"], .st-key-navbox [data-testid="stRadio"], .st-key-navbox [role="radiogroup"],
.st-key-navbox [role="radiogroup"] > div {{ width: 100% !important; }}
.st-key-navbox [role="radiogroup"] {{ gap: 2px !important; }}
.st-key-navbox [data-testid="stRadioOption"] {{ position: relative; display: flex; align-items: center; gap: .65rem; margin: 0 !important;
  padding: .4rem .7rem .4rem .8rem !important; border-radius: .55rem; cursor: pointer; transition: background .15s, color .15s;
  color: var(--muted-foreground); width: 100%; min-height: 0; }}
.st-key-navbox [data-testid="stRadioOption"] > div > div:first-child {{ display: none !important; }}
.st-key-navbox [data-testid="stRadioOption"] > div {{ display: flex; align-items: center; padding: 0 !important; }}
.st-key-navbox [data-testid="stRadioOption"]::before {{ content: ""; flex: 0 0 18px; height: 18px; background: currentColor;
  -webkit-mask-size: contain; mask-size: contain; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; -webkit-mask-position: center; mask-position: center; }}
.st-key-navbox [data-testid="stRadioOption"] p {{ font-size: .85rem !important; font-weight: 700 !important; color: inherit !important; margin: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.st-key-navbox [data-testid="stRadioOption"] > div, .st-key-navbox [data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] {{ min-width: 0; }}
.st-key-navbox [data-testid="stRadioOption"]:hover {{ background: color-mix(in oklab, var(--brand) 8%, transparent); color: var(--foreground); }}
.st-key-navbox [data-testid="stRadioOption"][data-selected="true"] {{ background: color-mix(in oklab, var(--brand) 13%, var(--card));
  color: var(--brand-deep); box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--brand) 16%, transparent); }}
.st-key-navbox [data-testid="stRadioOption"][data-selected="true"]::after {{ content: ""; position: absolute; left: -.1rem; top: 20%; bottom: 20%;
  width: 4px; border-radius: 4px; background: var(--amber); }}
{nav_icones}

/* ---------- cabeçalho com ondas correndo e borda inferior ondulada */
.st-key-cab, .st-key-pf_cab {{ position: relative; overflow: hidden; isolation: isolate; padding-bottom: 30px !important;
  -webkit-mask: linear-gradient(#000 0 0) 0 0 / 100% calc(100% - 29px) no-repeat, {BORDA} 0 100% / 1200px 30px repeat-x;
  mask: linear-gradient(#000 0 0) 0 0 / 100% calc(100% - 29px) no-repeat, {BORDA} 0 100% / 1200px 30px repeat-x;
  animation: borda 22s linear infinite; }}
@keyframes borda {{ to {{ -webkit-mask-position: 0 0, 1200px 100%; mask-position: 0 0, 1200px 100%; }} }}
.st-key-cab + div, .st-key-pf_cab + div {{ margin-top: -14px; }}
.st-key-abas button {{ border-radius: 999px !important; padding: .5rem 1.1rem !important; }}
.st-key-cab::before {{ content: ""; position: absolute; inset: auto 0 0 0; height: 70%; z-index: -1; pointer-events: none;
  background-image: {ONDAS}; background-repeat: repeat-x; background-size: 1200px 100%, 900px 85%, 700px 60%;
  background-position: 0 100%, 0 100%, 0 100%; animation: mar 26s linear infinite; }}
@keyframes mar {{ to {{ background-position: 1200px 100%, -900px 100%, 1400px 100%; }} }}
.st-key-cab::after {{ content: ""; position: absolute; top: -40%; right: -10%; width: 45%; height: 160%; z-index: -1; pointer-events: none;
  background: radial-gradient(closest-side, rgb(255 255 255 / .14), transparent); filter: blur(8px); }}

[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-primary"] {{ background: color-mix(in oklab, var(--brand) 16%, var(--card)) !important;
  border-color: var(--brand) !important; color: var(--brand-deep) !important; }}
[data-testid="stSidebar"] .stButton button p {{ font-size: .8125rem !important; font-weight: 700; }}
/* ---------- aparência */
.st-key-tema_box [data-testid="stButtonGroup"] {{ width: 100%; }}
.st-key-tema_box [data-testid="stButtonGroup"] > div {{ width: 100%; display: grid !important; grid-template-columns: 1fr 1fr; }}
.st-key-tema_box button {{ width: 100%; justify-content: center; gap: .4rem; }}
.st-key-tema_box button::before {{ content: ""; width: 15px; height: 15px; background: currentColor; -webkit-mask: var(--ico) center/contain no-repeat; mask: var(--ico) center/contain no-repeat; }}
.st-key-tema_box button:nth-of-type(1) {{ --ico: url("{_ico(SOL)}"); }}
.st-key-tema_box button:nth-of-type(2) {{ --ico: url("{_ico(LUA)}"); }}

/* ---------- títulos de seção da barra lateral */
section[data-testid="stSidebar"] {{ min-width: 19.5rem !important; }}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding: 0 1.1rem 2rem !important; }}
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.lb-titulo) {{ margin-top: .9rem; }}
.lb-titulo {{ display: flex; align-items: center; gap: .55rem; margin: 0 0 .45rem; }}
.lb-titulo .ic {{ flex: 0 0 24px; height: 24px; border-radius: 8px; display: grid; place-items: center; color: #fff;
  background: linear-gradient(135deg, var(--brand-deep), var(--brand) 55%, var(--brand-sky));
  box-shadow: 0 4px 10px -4px color-mix(in oklab, var(--brand) 70%, transparent); }}
[data-testid="stSidebar"] .lb-titulo .tx {{ font-size: .78rem !important; font-weight: 800; letter-spacing: .09em; text-transform: uppercase;
  color: var(--foreground); white-space: nowrap; }}
.lb-titulo::after {{ content: ""; flex: 1; height: 2px; border-radius: 2px; margin-left: .15rem;
  background: linear-gradient(90deg, color-mix(in oklab, var(--brand) 45%, transparent), transparent); }}
/* (antigo) */
.lb-sec.gota::before {{ content: ""; display: inline-block; width: 11px; height: 11px; margin-right: .35rem; vertical-align: -1px;
  background: var(--brand); -webkit-mask: url("{GOTA}") center/contain no-repeat; mask: url("{GOTA}") center/contain no-repeat; }}
.lb-info {{ border-radius: .6rem; background: var(--secondary); padding: .55rem .7rem; font-size: .78rem; line-height: 1.45; color: var(--muted-foreground); }}
.lb-info b {{ color: var(--foreground); }}
.lb-celula {{ border-radius: .6rem; border: 1px solid color-mix(in oklab, var(--amber) 55%, var(--border));
  background: color-mix(in oklab, var(--amber) 12%, var(--card)); padding: .55rem .75rem; }}
.lb-celula .r {{ font-size: .68rem; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: var(--muted-foreground); }}
.lb-celula .v {{ font-size: 1.15rem; font-weight: 800; color: var(--foreground); word-break: break-word; }}
@media (prefers-reduced-motion: reduce) {{ .st-key-cab::before, .st-key-cab, .st-key-pf_cab, .lb-onda {{ animation: none; }} }}
"""
    if escuro():
        css += f"""
:root {{ {VARS_ESCURO} }}
.stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{ color: var(--foreground); }}
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stWidgetLabel"] *,
.stApp label, .stApp [data-testid="stText"] {{ color: var(--foreground); }}
.stApp [data-testid="stCaptionContainer"] {{ color: var(--muted-foreground) !important; }}
.stApp [data-baseweb="select"] > div, .stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp input, .stApp textarea,
.stApp [data-testid="stNumberInputContainer"], .stApp [data-testid="stDateInputField"] {{ background: var(--card) !important; color: var(--foreground) !important;
  border-color: var(--input) !important; -webkit-text-fill-color: var(--foreground); }}
.stApp [data-baseweb="select"] svg, .stApp [data-testid="stNumberInputContainer"] button {{ color: var(--muted-foreground) !important; }}
.stApp [data-testid="stNumberInputContainer"] button {{ background: var(--secondary) !important; }}
.stApp [data-baseweb="select"] [data-baseweb="tag"] span {{ color: var(--brand) !important; }}
[data-baseweb="popover"] > div, [data-baseweb="popover"] ul, [data-baseweb="menu"], [role="listbox"], [data-baseweb="calendar"],
[data-baseweb="calendar"] > div, [data-baseweb="datepicker"] {{ background: var(--card) !important; color: var(--foreground) !important; }}
[data-baseweb="popover"] li, [role="option"] {{ background: var(--card) !important; color: var(--foreground) !important; }}
[data-baseweb="popover"] li:hover, [role="option"][aria-selected="true"], [role="option"]:hover {{ background: var(--accent) !important; }}
[data-baseweb="calendar"] button, [data-baseweb="calendar"] div[role="gridcell"] div {{ color: var(--foreground) !important; }}
[data-baseweb="calendar"] [aria-selected="true"] div {{ background: var(--brand) !important; color: #fff !important; }}
[data-testid="stPopoverBody"], [data-testid="stTooltipContent"] {{ background: var(--card) !important; color: var(--foreground) !important; border-color: var(--border) !important; }}
.stApp [data-baseweb="tab-list"] button p {{ color: var(--muted-foreground); }}
.stApp [data-baseweb="tab-list"] button[aria-selected="true"] p {{ color: var(--brand) !important; }}
.stApp [data-baseweb="tab-border"] {{ background: var(--border) !important; }}
.stApp [data-testid="stSelectbox"] [role="group"], .stApp [data-testid="stMultiSelect"] [role="group"], .stApp [data-testid="stDateInput"] [role="group"],
.stApp [data-testid="stTextInput"] [role="group"] {{ background: var(--card) !important; border-color: var(--input) !important; color: var(--foreground) !important; }}
[data-testid$="VirtualDropdown"], [data-testid$="VirtualDropdown"] > div {{ background: var(--card) !important; color: var(--foreground) !important; border-color: var(--border) !important; }}
[data-testid$="VirtualDropdown"] [role="option"] *, [data-testid$="VirtualDropdown"] li * {{ color: var(--foreground) !important; }}
.stApp [data-testid="stElementToolbar"], .stApp [data-testid="stElementToolbarButtonContainer"] {{ background: var(--card) !important; }}
.stApp button[data-variant="pills"], .stApp button[data-variant="segmented_control"] {{ background: var(--card) !important; color: var(--foreground) !important;
  border-color: var(--input) !important; }}
.stApp button[data-variant="pills"] p, .stApp button[data-variant="segmented_control"] p {{ color: inherit !important; }}
.stApp button[data-variant="pills"][aria-pressed="true"], .stApp button[data-variant="segmented_control"][aria-checked="true"] {{
  background: color-mix(in oklab, var(--brand) 24%, var(--card)) !important; border-color: var(--brand) !important; color: #fff !important; }}
.stApp [data-testid="stBaseButton-pills"], .stApp [data-testid="stBaseButton-segmented_control"],
.stApp [data-testid="stBaseButton-secondary"] {{ background: var(--card) !important; color: var(--foreground) !important; border-color: var(--input) !important; }}
.stApp [data-testid="stBaseButton-pillsActive"], .stApp [data-testid="stBaseButton-segmented_controlActive"] {{
  background: color-mix(in oklab, var(--brand) 22%, var(--card)) !important; color: var(--foreground) !important; border-color: var(--brand) !important; }}
.stApp [data-testid="stSliderTickBarMin"], .stApp [data-testid="stSliderTickBarMax"], .stApp [data-testid="stSliderThumbValue"] {{ color: var(--muted-foreground) !important; }}
.stApp [data-testid="stExpander"] details, .stApp [data-testid="stExpander"] summary {{ background: var(--card) !important; border-color: var(--border) !important; color: var(--foreground); }}
.stApp [data-testid="stFileUploaderDropzone"] {{ background: var(--secondary) !important; color: var(--foreground); }}
.stApp [data-testid="stAlert"] {{ background: color-mix(in oklab, var(--brand) 14%, var(--card)) !important; color: var(--foreground) !important; }}
.stApp [data-testid="stAlert"] * {{ color: var(--foreground) !important; }}
.stApp [data-testid="stDataFrame"], .stApp [data-testid="stTable"] {{ filter: invert(.9) hue-rotate(180deg) saturate(1.1); border-radius: .5rem; }}
.stApp [data-testid="stCheckbox"] span, .stApp [data-testid="stToggle"] span {{ border-color: var(--input); }}
.stApp code {{ background: var(--secondary); color: var(--brand-sky); }}
.st-key-marca img {{ filter: drop-shadow(0 6px 16px rgb(0 0 0 / .45)); }}
.lb-onda {{ background-image: {_onda("#60a5fa", .25, 14)}, {_onda("#38bdf8", .2, 9)}; }}
"""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ------------------------------------------------------------------ peças da barra lateral
def marca_lateral(nome: str):
    with st.container(key="marca"):
        st.image(str(MARCA / ("logo_escuro.webp" if escuro() else "logo_claro.webp")), width="stretch")
        st.markdown(f'<p class="lb-user"><i></i>Manutenção preditiva · {nome}</p><div class="lb-onda"></div>', unsafe_allow_html=True)


SECAO_ICONE = {"Navegação": "nav", "Previsão": "dia", "Análise exploratória": "eda", "Sobre o modelo": "modelo", "Simulador": "sim",
               "Ficha da máquina": "maq", "Sensores": "sensor", "Navegar na tabela": "tabela", "Aparência": "tema"}


def secao(titulo: str):
    """Título de seção da barra lateral: selo com ícone, nome e um traço que some."""
    ic = ICONES_SECAO[SECAO_ICONE.get(titulo, "gota")]
    svg = (f'<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.3" '
           f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ic}</svg>')
    st.markdown(f'<div class="lb-titulo"><span class="ic">{svg}</span><span class="tx">{titulo}</span></div>', unsafe_allow_html=True)


def _tema_mudou():
    v = st.session_state.get("tema_sel")
    if v is None:                                  # clique no botão já ativo: mantém o tema
        st.session_state.tema_sel = st.session_state.get("tema", "claro")
    else:
        st.session_state.tema = v


def rodape_lateral():
    """Aparência (claro/escuro) e sair, sempre no fim da barra lateral."""
    with st.sidebar:
        secao("Aparência")
        st.session_state.setdefault("tema", "claro")
        st.session_state.setdefault("tema_sel", st.session_state.tema)
        with st.container(key="tema_box"):
            st.segmented_control("Tema", ["claro", "escuro"], format_func={"claro": "Claro", "escuro": "Escuro"}.get,
                                 key="tema_sel", on_change=_tema_mudou, label_visibility="collapsed")
        st.markdown('<div style="height:.25rem"></div>', unsafe_allow_html=True)
        if st.button("Sair da conta", key="lb_sair", width="stretch"):
            tema = st.session_state.get("tema", "claro")
            st.session_state.clear()
            st.session_state.tema = tema
            st.rerun()
