"""MaBiYama · Painel da Frota Industrial (Streamlit), com o mesmo visual do painel feito no Lovable.

Telas: login, Previsão & Modelagem, Análise Exploratória e Perfil.
  - Cabeçalho, abas, login e perfil: componentes do Streamlit estilizados com o CSS do Lovable.
  - Conteúdo das abas: o próprio componente do Lovable (React + Recharts + Tailwind), embutido sem depender de
    internet (frontend/), alimentado com os dados reais da pasta dados/ (painel_dados.py).

Rodar:  streamlit run app.py
"""
import hashlib
import hmac
import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import animacao
import painel_dados
import paginas
import tema

RAIZ = Path(__file__).resolve().parent
DADOS = RAIZ / "dados"
FRONT = RAIZ / "frontend"

st.set_page_config(page_title="MaBiYama · Painel da Frota", page_icon="⚙️", layout="wide",
                   initial_sidebar_state="expanded" if "usuario" in st.session_state else "collapsed")


# ------------------------------------------------------------------ recursos estáticos
@st.cache_resource
def _recurso(nome: str, versao: int) -> str:
    return (FRONT / nome).read_text(encoding="utf-8")


def recurso(nome: str) -> str:
    """Lê um arquivo do frontend; recarrega sozinho quando o arquivo muda (evita servir o JS/CSS antigo após deploy)."""
    return _recurso(nome, (FRONT / nome).stat().st_mtime_ns)


@st.cache_resource
def _extras(versao: int) -> dict:
    return json.loads((DADOS / "extras.json").read_text(encoding="utf-8"))


def extras() -> dict:
    """Replay, raio-X e simulador (dados/extras.json, gerado a partir da validação temporal)."""
    f = DADOS / "extras.json"
    return _extras(f.stat().st_mtime_ns) if f.exists() else {}


def svg_uri(svg: str) -> str:
    from urllib.parse import quote
    return "data:image/svg+xml," + quote(svg)


SVG = {
    "factory": '<path d="M12 16h.01"/><path d="M16 16h.01"/><path d="M3 19a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.5a.5.5 0 0 0-.769-.422l-4.462 2.844A.5.5 0 0 1 15 10.5v-2a.5.5 0 0 0-.769-.422L9.77 10.922A.5.5 0 0 1 9 10.5V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2z"/><path d="M8 16h.01"/>',
    "lock": '<circle cx="12" cy="16" r="1"/><rect x="3" y="10" width="18" height="12" rx="2"/><path d="M7 10V7a5 5 0 0 1 10 0v3"/>',
    "user": '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    "upload": '<path d="M12 3v12"/><path d="m17 8-5-5-5 5"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>',
    "camera": '<path d="M13.997 4a2 2 0 0 1 1.76 1.05l.486.9A2 2 0 0 0 18.003 7H20a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1.997a2 2 0 0 0 1.759-1.048l.489-.904A2 2 0 0 1 10.004 4z"/><circle cx="12" cy="13" r="3"/>',
    "save": '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/>',
    "logout": '<path d="m16 17 5-5-5-5"/><path d="M21 12H9"/><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>',
}


def icone(nome, classe="", cor="currentColor", tam=24):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{tam}" height="{tam}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{cor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="{classe}">'
            f'{SVG[nome]}</svg>')


def mascara(nome):
    """URI de um ícone para usar como máscara CSS (herda a cor do texto do botão)."""
    return svg_uri(icone(nome, cor="black"))


GOOGLE = svg_uri('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82z"/><path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24z"/><path fill="#FBBC05" d="M5.27 14.29c-.25-.72-.38-1.49-.38-2.29s.14-1.57.38-2.29V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.98-3.09z"/><path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.98 3.09c.95-2.85 3.6-4.96 6.73-4.96z"/></svg>')
LOVABLE = svg_uri('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122 122"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff7a59"/><stop offset=".5" stop-color="#ff3d77"/><stop offset="1" stop-color="#6b5bff"/></linearGradient></defs><path fill="url(#g)" fill-rule="evenodd" d="M36.07 0C55.99 0 72.14 16.16 72.14 36.08V49.8H84.14C104.06 49.8 120.21 65.95 120.21 85.88S104.06 121.96 84.14 121.96H0V36.08C0 16.16 16.15 0 36.07 0Z"/></svg>')


# ------------------------------------------------------------------ estilo (CSS do Lovable aplicado ao Streamlit)
def css_base():
    st.markdown(f"""<style>
{recurso("fontes.css")}
:root {{
  --background: oklch(98.5% .005 250); --foreground: oklch(12.9% .042 264.695); --card: oklch(100% 0 0);
  --border: oklch(92.9% .013 255.508); --input: oklch(92.9% .013 255.508); --muted-foreground: oklch(55.4% .046 257.417);
  --secondary: oklch(96.8% .007 247.896); --accent: oklch(96.8% .007 247.896); --primary-foreground: oklch(98.4% .003 247.858);
  --brand: oklch(55% .19 258); --brand-deep: oklch(38% .17 262); --ring: oklch(70.4% .04 256.788);
  --gradient-header: linear-gradient(100deg, oklch(38% .17 262), oklch(55% .19 258) 60%, oklch(80% .09 230));
  --google-background:#fff; --google-foreground:#1f1f1f; --google-border:#747775;
}}
html, body, .stApp, .stApp * {{ font-family: "Nunito", system-ui, sans-serif; }}
.stApp [data-testid="stIconMaterial"], .stApp .material-symbols-rounded {{ font-family: "Material Symbols Rounded" !important; }}
.stApp {{ background: var(--background); color: var(--foreground); }}
[data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="stToolbarActions"], [data-testid="stMainMenu"],
[data-testid="stAppDeployButton"], #MainMenu, footer, .stDeployButton {{ display: none !important; }}
[data-testid="stToolbar"] {{ background: transparent !important; pointer-events: none; }}
[data-testid="stToolbar"] [data-testid="stExpandSidebarButton"] {{ pointer-events: auto; }}
header[data-testid="stHeader"] {{ background: transparent !important; height: 0 !important; min-height: 0 !important; }}
[data-testid="stExpandSidebarButton"] {{ position: fixed !important; top: .75rem; left: .75rem; z-index: 999990; display: inline-flex !important;
  align-items: center; gap: .375rem; height: 2.25rem; padding: 0 .75rem 0 .5rem !important; background: var(--card) !important;
  border: 1px solid var(--border) !important; border-radius: 8px; box-shadow: 0 2px 6px rgb(0 0 0 / .18); color: var(--brand-deep) !important; }}
[data-testid="stExpandSidebarButton"]::after {{ content: "Menu"; font-weight: 700; font-size: .8125rem; }}
[data-testid="stExpandSidebarButton"]:hover {{ background: var(--accent) !important; }}

/* barra lateral */
[data-testid="stSidebar"] {{ background: var(--card) !important; border-right: 1px solid var(--border); }}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding: 0 1.25rem 2rem; }}
[data-testid="stSidebarHeader"] {{ padding: .75rem 1rem 0; height: auto; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: .75rem; }}
[data-testid="stSidebar"] label p, [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{ font-size: .8125rem !important; font-weight: 700; color: var(--foreground); }}
.lb-marca {{ border-radius: 10px; background-image: var(--gradient-header); color: var(--primary-foreground); padding: .875rem 1rem; }}
.lb-marca p {{ margin: 0; }}
[data-testid="stSidebar"] p.lb-sec {{ font-size: .6875rem !important; line-height: 1rem; }}
.lb-sec {{ margin: .75rem 0 -.25rem; padding-top: .875rem; border-top: 1px solid var(--border); font-size: .6875rem; font-weight: 800;
  letter-spacing: .14em; text-transform: uppercase; color: var(--muted-foreground); }}
[data-testid="stSidebar"] .lb-sobre, [data-testid="stSidebar"] .lb-sobre * {{ font-size: .8125rem !important; }}
.lb-marca .eyebrow {{ font-size: .625rem !important; letter-spacing: .2em; }}
.lb-sobre {{ font-size: .8125rem; line-height: 1.5; color: var(--muted-foreground); }}
.lb-sobre b {{ color: var(--foreground); font-weight: 700; }}
[data-testid="stSidebar"] [data-baseweb="tag"] {{ background: var(--secondary) !important; color: var(--brand-deep) !important; }}
[data-testid="stSidebar"] [data-baseweb="select"] > div {{ border-color: var(--input) !important; background: var(--card) !important; }}
[data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {{ background: var(--brand) !important; }}
[data-testid="stSidebar"] .stDownloadButton button {{ width: 100%; background: var(--brand) !important; color: var(--primary-foreground) !important;
  border: 0 !important; height: 2.25rem; }}
[data-testid="stSidebar"] .stDownloadButton button:hover {{ background: var(--brand-deep) !important; }}
[data-testid="stSidebar"] .stButton button {{ width: 100%; height: 2.25rem; background: var(--background) !important; color: var(--foreground) !important;
  border: 1px solid var(--input) !important; }}
[data-testid="stSidebar"] .stButton button:hover {{ background: var(--accent) !important; }}
[data-testid="stMainBlockContainer"], .block-container {{ padding: 0 !important; max-width: 100% !important; }}
[data-testid="stMain"] [data-testid="stVerticalBlock"] {{ gap: 0; }}
.stApp .stMarkdown, .stApp [data-testid="stMarkdown"] {{ margin-bottom: 0 !important; }}
.stApp [data-testid="stMarkdownContainer"] > :last-child {{ margin-bottom: 0; }}
.stApp .stButton button > div, .stApp [data-testid="stFormSubmitButton"] button > div {{ width: auto; flex: 0 0 auto; }}
[data-testid="stElementContainer"]:has(iframe) {{ width: 100% !important; }}
iframe {{ border: 0; display: block; }}
h1, h2, h3 {{ padding: 0 !important; margin: 0; }}
[data-testid="stHeaderActionElements"], .stMarkdown h1 a, .stMarkdown h2 a {{ display: none !important; }}
.titulo-painel {{ font-size: 1.875rem !important; line-height: 2.25rem !important; }}
@media (min-width: 768px) {{ .titulo-painel {{ font-size: 2.25rem !important; line-height: 2.5rem !important; }} }}

/* cabeçalho em degradê (classe bg-header) */
.cab-grad {{ background-image: var(--gradient-header) !important; color: var(--primary-foreground); }}
.eyebrow {{ font-size: .75rem; line-height: 1rem; font-weight: 700; letter-spacing: .25em; text-transform: uppercase; }}
.titulo {{ font-weight: 800; font-style: italic; color: var(--primary-foreground) !important; letter-spacing: 0; }}

/* entradas (classe account-input) */
.stApp [data-testid="stTextInput"] label p {{ font-size: .875rem; font-weight: 700; color: var(--foreground); }}
.stApp [data-testid="stTextInput"] label {{ margin-bottom: .5rem; min-height: 0; }}
.stApp [data-testid="stTextInputRootElement"], .stApp [data-baseweb="input"] {{ border: 1px solid var(--input) !important;
  background: var(--card) !important; border-radius: 6px !important; box-shadow: none !important; }}
.stApp [data-testid="stTextInputRootElement"]:focus-within, .stApp [data-baseweb="input"]:focus-within {{ outline: 2px solid var(--brand);
  outline-offset: 0; border-color: var(--input) !important; }}
.stApp [data-testid="stTextInputRootElement"] *, .stApp [data-baseweb="input"] > div {{ background: transparent !important; }}
.stApp [data-testid="stTextInputField"] {{ padding: 10px 12px; font-size: 1rem; color: var(--foreground); min-height: 0; }}
.stApp [data-testid="InputInstructions"] {{ display: none; }}

/* botões (classes do Button shadcn) */
.stApp .stButton button, .stApp [data-testid="stFormSubmitButton"] button, .stApp [data-testid="stPopover"] button {{
  border-radius: 6px; font-size: .875rem; font-weight: 500; min-height: 0; box-shadow: none; gap: .5rem; transition: background .15s, color .15s; }}
.stApp .stButton button p, .stApp [data-testid="stFormSubmitButton"] button p, .stApp [data-testid="stPopover"] button p {{ font-size: .875rem; font-weight: inherit; }}
.stApp p.status {{ margin: 1rem 0 0; border-radius: 6px; background: var(--secondary); padding: .75rem; font-size: .875rem !important; line-height: 1.25rem; }}
</style>""", unsafe_allow_html=True)
    tema.css_tema()


def aplicar(regras: dict):
    css = []
    for key, tipos in regras.items():
        sel = f".st-key-{key}"
        for t in tipos:
            if t.startswith("ico:"):
                css.append(f"{sel} {{ --ico: url('{mascara(t[4:])}'); }}")
                css.append(f"{sel} button::before {{ content: ''; width: 16px; height: 16px; background: currentColor; "
                           f"-webkit-mask: var(--ico) center / contain no-repeat; mask: var(--ico) center / contain no-repeat; flex: none; }}")
            elif t.startswith("icodepois:"):
                css.append(f"{sel} {{ --ico: url('{mascara(t[10:])}'); }}")
                css.append(f"{sel} button p {{ display: inline-flex; align-items: center; gap: .5rem; }}"
                           f"{sel} button p::after {{ content: ''; width: 16px; height: 16px; background: currentColor; "
                           f"-webkit-mask: var(--ico) center / contain no-repeat; mask: var(--ico) center / contain no-repeat; flex: none; }}")
            else:
                css.append(BOTOES[t].replace("&", sel))
    st.markdown("<style>" + "\n".join(css) + "</style>", unsafe_allow_html=True)


BOTOES = {
    "primario": "& button { background: var(--brand) !important; color: var(--primary-foreground) !important; border: 0 !important; }"
                "& button:hover { background: var(--brand-deep) !important; color: var(--primary-foreground) !important; }",
    "contorno": "& button { background: var(--background) !important; color: var(--foreground) !important; "
                "border: 1px solid var(--input) !important; box-shadow: 0 1px 2px rgb(0 0 0 / .05) !important; }"
                "& button:hover { background: var(--accent) !important; color: var(--foreground) !important; }",
    "link": "& button { background: transparent !important; border: 0 !important; color: var(--brand) !important; "
            "padding: 0 !important; min-height: 0 !important; box-shadow: none !important; }"
            "& button:hover p { text-decoration: underline; text-underline-offset: 4px; }"
            "& button:hover { color: var(--brand) !important; }",
    "h11": "& button { height: 2.75rem; width: 100%; padding: 0 1rem; }",
    "h9": "& button { height: 2.25rem; padding: 0 1rem; }",
    "google": "& button { background: var(--google-background) !important; color: var(--google-foreground) !important; "
              "border: 1px solid var(--google-border) !important; font-weight: 500; }"
              f"& button::before {{ content: ''; width: 18px; height: 18px; background: url('{GOOGLE}') center / contain no-repeat; flex: none; }}",
    "lovable": f"& button::before {{ content: ''; width: 16px; height: 16px; background: url('{LOVABLE}') center / contain no-repeat; flex: none; }}",
}


# ------------------------------------------------------------------ autenticação
def _hash(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def usuarios() -> dict:
    try:
        return dict(st.secrets.get("usuarios", {}))
    except Exception:  # sem secrets.toml
        return {}


def autenticar(email: str, senha: str):
    u = usuarios().get(email.strip().lower())
    if u and hmac.compare_digest(_hash(senha), u.get("senha_sha256", "")):
        return {"email": email.strip().lower(), "nome": u.get("nome", email.split("@")[0])}
    return None


def _resumo_login():
    """Números do dia para a tela de entrada (previsão padrão)."""
    try:
        d = dados_painel(None)
        dia = d["dias"][0]
        lista = dia.get("lista", [])
        return dia["execCurto"], sum(e["prob"] > 50 for e in lista), len(lista)
    except Exception:
        return None


def tela_login():
    """Tela de entrada "Maré": mar profundo com ondas e bolhas, marca à esquerda e o acesso num cartão."""
    st.markdown(f"""<style>
      .stApp {{ background: linear-gradient(170deg, #0a1a3f 0%, #123a8a 52%, #1f6fd1 100%) fixed !important; }}
      [data-testid="stSidebar"], [data-testid="stExpandSidebarButton"] {{ display: none !important; }}
      .mare {{ position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }}
      .mare svg {{ position: absolute; left: 0; bottom: 0; width: 200%; }}
      .mare .o1 {{ height: 34vh; animation: mareOnda 16s linear infinite; }}
      .mare .o2 {{ height: 27vh; animation: mareOnda 24s linear infinite reverse; }}
      .mare .o3 {{ height: 18vh; animation: mareOnda 11s linear infinite; }}
      .mare i {{ position: absolute; border-radius: 50%; border: 2px solid rgba(186,224,255,.45); animation: mareBolha 10s ease-in infinite; }}
      @keyframes mareOnda {{ to {{ transform: translateX(-50%); }} }}
      @keyframes mareBolha {{ 0% {{ transform: translateY(0) scale(.6); opacity: 0; }} 20% {{ opacity: .8; }} 100% {{ transform: translateY(-55vh) scale(1); opacity: 0; }} }}
      @media (prefers-reduced-motion: reduce) {{ .mare svg, .mare i {{ animation: none; }} }}
      .st-key-entrada {{ position: relative; z-index: 1; max-width: 76rem; margin: 0 auto; padding: 4rem 2rem 8rem; gap: 4rem !important;
        flex-wrap: wrap; align-items: flex-start !important; }}
      .st-key-entrada_esq {{ flex: 1 1 26rem; gap: 1.25rem !important; color: #eaf2ff; }}
      .st-key-entrada_esq [data-testid="stImage"] img {{ width: 330px !important; max-width: 100%; filter: drop-shadow(0 10px 24px rgb(0 0 0 / .35)); }}
      .mare-h1 {{ margin: .5rem 0 0 !important; font-size: 2.75rem !important; line-height: 1.1 !important; font-weight: 800; color: #fff; max-width: 36rem; }}
      .mare-p {{ margin: 0; font-size: 1.05rem !important; line-height: 1.55; color: #bcd3f5; max-width: 33rem; }}
      .mare-chips {{ display: flex; flex-wrap: wrap; gap: .75rem; margin-top: .4rem; }}
      .mare-chips span {{ display: inline-flex; align-items: center; gap: .5rem; border-radius: 999px; padding: .5rem .9rem; font-size: .82rem; font-weight: 700;
        color: #eaf2ff; background: rgb(10 26 63 / .45); border: 1px solid rgb(143 211 255 / .35); backdrop-filter: blur(4px); }}
      .mare-chips i {{ width: 8px; height: 8px; border-radius: 50%; }}
      .st-key-login {{ flex: 0 0 25rem; max-width: 100%; background: var(--card); border-radius: 22px; padding: 2.1rem 2.1rem 1.8rem;
        box-shadow: 0 30px 60px -20px rgb(3 10 30 / .65); margin-top: .5rem; }}
      .st-key-login [data-testid="stForm"] {{ border: 0; padding: 0; margin-top: 1.25rem !important; }}
      .st-key-login [data-testid="stForm"] [data-testid="stVerticalBlock"] {{ gap: 1rem !important; }}
      .st-key-esqueci {{ align-self: flex-end; }}
      .st-key-esqueci button {{ width: auto !important; }}
      .st-key-entrar button {{ width: 100%; height: 3rem !important; border-radius: 12px !important; border: 0 !important;
        background: linear-gradient(100deg, #163283, #2563d8) !important; color: #fff !important; font-weight: 800 !important; }}
      .st-key-entrar button p {{ font-weight: 800 !important; font-size: 1rem !important; }}
      .st-key-entrar button:hover {{ filter: brightness(1.08); }}
    </style>""", unsafe_allow_html=True)
    st.markdown('''<div class="mare" aria-hidden="true"><i style="bottom:15vh;left:14%;width:14px;height:14px"></i><i style="bottom:11vh;left:31%;width:9px;height:9px;animation-delay:3s"></i><i style="bottom:17vh;left:47%;width:11px;height:11px;animation-delay:5.5s"></i><i style="bottom:12vh;left:72%;width:10px;height:10px;animation-delay:7s"></i><svg class="o1" viewBox="0 0 1600 200" preserveAspectRatio="none"><path d="M0 90 Q200 30 400 90 T800 90 T1200 90 T1600 90 V200 H0Z" fill="#5fb4f2" fill-opacity=".22"/></svg><svg class="o2" viewBox="0 0 1600 200" preserveAspectRatio="none"><path d="M0 100 Q200 50 400 100 T800 100 T1200 100 T1600 100 V200 H0Z" fill="#8fd3ff" fill-opacity=".2"/></svg><svg class="o3" viewBox="0 0 1600 200" preserveAspectRatio="none"><path d="M0 110 Q200 70 400 110 T800 110 T1200 110 T1600 110 V200 H0Z" fill="#eaf4ff" fill-opacity=".9"/></svg></div>''', unsafe_allow_html=True)
    aplicar({"entrar": ["primario", "h11", "icodepois:arrow-right"], "esqueci": ["link"]})

    resumo = _resumo_login()
    with st.container(key="entrada", horizontal=True):
        with st.container(key="entrada_esq"):
            st.image(str(tema.MARCA / "logo_escuro.webp"), width=330)
            chips = ""
            if resumo:
                ex, alto, jan = resumo
                chips = (f'<div class="mare-chips"><span><i style="background:#5ee0a0"></i>Previsão pronta · 05:00 de {ex}</span>'
                         f'<span><i style="background:#f5a524"></i>{alto} peça{"s" if alto != 1 else ""} acima de 50%</span>'
                         f'<span><i style="background:#8fd3ff"></i>{jan} peças na janela de risco</span></div>')
            st.markdown('<h1 class="mare-h1">Cada bomba da frota, acompanhada antes de parar.</h1>'
                        '<p class="mare-p">Painel de manutenção preditiva: previsão diária às 05:00, prioridades da equipe e o histórico de cada máquina.</p>'
                        + chips, unsafe_allow_html=True)
        with st.container(key="login"):
            st.markdown("""<h2 style="font-size:1.5rem;line-height:2rem;font-weight:800;color:var(--foreground)">Acesse sua frota</h2>
              <p style="margin:.25rem 0 0;font-size:.875rem;color:var(--muted-foreground)">Bem-vindo à MaBiYama.</p>""", unsafe_allow_html=True)
            with st.form("form_login", border=False, enter_to_submit=True):
                email = st.text_input("Email", key="email", autocomplete="email", placeholder="voce@empresa.com")
                senha = st.text_input("Senha", type="password", key="senha", autocomplete="current-password")
                esqueci = st.form_submit_button("Esqueci minha senha", key="esqueci")
                entrar = st.form_submit_button("Entrar", key="entrar", width="stretch")
            if entrar:
                u = autenticar(email, senha)
                if u:
                    st.session_state.usuario, st.session_state.aba = u, "model"
                    st.session_state.pop("msg_login", None)
                    st.rerun()
                st.session_state.msg_login = "Não foi possível entrar. Confira email e senha."
            if esqueci:
                st.session_state.msg_login = "Para redefinir a senha, fale com a equipe da Poli Júnior responsável pelo painel."
            if st.session_state.get("msg_login"):
                st.markdown(f'<p role="status" class="status">{st.session_state.msg_login}</p>', unsafe_allow_html=True)
            st.markdown(f"""<p style="margin-top:1.25rem;display:flex;align-items:center;justify-content:center;gap:.5rem;
              font-size:.8rem;color:var(--muted-foreground)">{icone("lock", tam=12)} O acesso é criado pela equipe da Poli Júnior.</p>""",
                        unsafe_allow_html=True)
    animacao.login()  # deixa o motor da animação carregado para a entrada no painel


# ------------------------------------------------------------------ painel
def _versao_dados() -> str:
    """Muda quando o código ou os dados mudam: invalida o cache e recarrega painel_dados após um deploy."""
    arqs = [RAIZ / "painel_dados.py"] + sorted(DADOS.rglob("*.csv")) + sorted(DADOS.rglob("*.json"))
    return hashlib.md5("|".join(f"{a.name}:{a.stat().st_mtime_ns}:{a.stat().st_size}" for a in arqs).encode()).hexdigest()


@st.cache_data(show_spinner=False)
def _dados_painel(previsao: bytes | None, versao: str):
    import importlib
    importlib.reload(painel_dados)
    sub = pd.read_csv(io.BytesIO(previsao)) if previsao else None
    return painel_dados.montar(DADOS, sub)


def dados_painel(previsao: bytes | None):
    return _dados_painel(previsao, _versao_dados())


def cabecalho_painel(aba):
    st.markdown("""<style>
      .st-key-cab { background-image: var(--gradient-header); color: var(--primary-foreground); }
      .st-key-cab_topo { max-width: 80rem; margin: 0 auto; padding: 1.75rem 1.5rem; display: flex !important; flex-direction: row !important;
        flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 1rem !important; }
      .st-key-cab_topo > div { width: auto !important; flex: 0 1 auto; }
      .st-key-abas { max-width: 80rem; margin: 0 auto; padding: 0 1rem .35rem; gap: .35rem !important; flex-wrap: wrap; }
      @media (min-width: 640px) { .st-key-abas { padding: 0 1.5rem; } }
      .st-key-abas button { height: auto; border: 0 !important; border-radius: 999px !important; padding: .5rem 1.15rem !important;
        background: transparent !important; color: color-mix(in oklab, var(--primary-foreground) 80%, transparent) !important; }
      .st-key-abas button p { font-weight: 700 !important; font-size: .875rem !important; }
      .st-key-abas button:hover { background: color-mix(in oklab, var(--card) 10%, transparent) !important; }
      .st-key-aba_perfil button { color: var(--primary-foreground) !important; padding: .5rem 1rem !important; }
      .st-key-aba_perfil button p { font-weight: 500 !important; }
      .st-key-envio button { background: var(--card) !important; color: var(--brand-deep) !important; border: 0 !important;
        height: 2.25rem; padding: 0 1rem !important; box-shadow: 0 1px 3px rgb(0 0 0 / .1) !important; }
      .st-key-envio button:hover { background: color-mix(in oklab, var(--card) 90%, transparent) !important; }
      .st-key-envio button [data-testid="stIconMaterial"] { display: none; }
    </style>""", unsafe_allow_html=True)
    st.markdown(f"""<style>.stApp .st-key-abas .st-key-aba_{aba} button {{ background: var(--tab-ativa, var(--card)) !important;
        color: var(--tab-ativa-txt, var(--brand-deep)) !important; border-color: transparent !important; box-shadow: 0 6px 16px -8px rgb(0 0 0 / .45) !important; }}
      .stApp .st-key-abas .st-key-aba_{aba} button p {{ color: inherit !important; }}
      .stApp .st-key-abas .st-key-aba_{aba} button:hover {{ background: var(--tab-ativa, var(--card)) !important; }}</style>""", unsafe_allow_html=True)
    aplicar({"envio": ["ico:upload"], "aba_perfil": ["ico:user"]})

    with st.container(key="cab"):
        with st.container(key="cab_topo"):
            st.markdown("""<div><p class="eyebrow" style="opacity:.8;margin:0">Manutenção preditiva · MaBiYama</p>
              <h1 class="titulo titulo-painel">Painel da Frota Industrial</h1></div>""",
                        unsafe_allow_html=True)
            with st.container(key="envio"):
                with st.popover("Enviar dados do dia"):
                    st.markdown("**Nova previsão** no formato da submissão (id, peca_A, peca_B, peca_C, peca_D).")
                    arq = st.file_uploader("Arquivo CSV", type="csv", label_visibility="collapsed")
                    if arq is not None:
                        try:
                            dados_painel(arq.getvalue())
                            st.session_state.previsao = arq.getvalue()
                            st.success(f"Previsão carregada: {arq.name}")
                        except Exception as e:  # formato inválido
                            st.error(f"Não consegui ler o arquivo: {e}")
                    if st.session_state.get("previsao") and st.button("Voltar à previsão padrão"):
                        st.session_state.previsao = None
                        st.rerun()
        with st.container(key="abas", horizontal=True):
            for k, rotulo in [(k, v) for k, v in ABAS.items() if k != "perfil"] + [("perfil", "Perfil")]:
                if st.button(rotulo, key=f"aba_{k}"):
                    st.session_state.aba = k
                    st.rerun()


def conteudo_painel(aba, filtros):
    d = dict(dados_painel(st.session_state.get("previsao")))
    if aba == "eda":
        d["graficos"] = graficos()
    pagina = f"""<!doctype html><html lang="pt-BR" class="{tema.classe_html()}"><head><meta charset="utf-8">
<style>{recurso("fontes.css")}{recurso("painel.css")} html,body{{margin:0;background:var(--background)}}{tema.css_iframe()}</style></head>
<body><div id="root"></div>
<script>window.DADOS={json.dumps(d, ensure_ascii=False)};window.ABA="{aba}";window.FILTROS={json.dumps(filtros, ensure_ascii=False)};
window.EXTRAS={json.dumps({k: v for k, v in extras().items() if k == "raiox"} if aba == "model" else {}, ensure_ascii=False)};</script>
<script>{recurso("vendor.js")}</script><script>{recurso("extras.js")}</script><script>{recurso("painel.js")}</script></body></html>"""
    components.html(pagina, height=2300 if aba == "model" else 1500, scrolling=False)


CENARIOS = {
    "Padrão": dict(lim=30, cap=6, margem=8, horas=8, custoAnt=400, efic=0.9),
    "Conservador (premissas pessimistas)": dict(lim=40, cap=4, margem=4, horas=4, custoAnt=1200, efic=0.75),
    "Otimista (parada cara)": dict(lim=20, cap=8, margem=15, horas=12, custoAnt=300, efic=0.95),
    "Equipe enxuta (2 por dia)": dict(lim=50, cap=2, margem=8, horas=8, custoAnt=400, efic=0.9),
    "Sem limite de equipe": dict(lim=10, cap=20, margem=8, horas=8, custoAnt=400, efic=0.9),
}
PERIODOS = {"Tudo": None, "jan–mar": ("2022-12-31", "2023-03-31"), "abr–jun": ("2023-04-01", "2023-06-30"), "jul–set": ("2023-07-01", "2023-09-30")}


def _recorte_sim(replay: dict, periodo, pecas, linhas) -> dict:
    """Filtra o replay da validação por período, peças e linhas de produção (o simulador recebe só o recorte)."""
    ip = {p: i for i, p in enumerate(replay["pecas"])}
    okp = {ip[p[-1]] for p in pecas} if pecas else set(range(4))
    okm = {i for i, m in enumerate(replay["maquinas"]) if not linhas or m["linha"] in linhas}
    a, b = PERIODOS[periodo] or ("0000", "9999")
    dias, por = [], []
    for d, x in zip(replay["dias"], replay["porDia"]):
        if a <= d <= b:
            dias.append(d)
            por.append({"c": [e for e in x["c"] if e[1] in okp and e[0] in okm], "f": [e for e in x["f"] if e[1] in okp and e[0] in okm]})
    return {**replay, "dias": dias, "porDia": por}


def replay_frota():
    """Replay da validação (rede hidráulica) numa página própria, usado na aba Máquinas."""
    ex = extras()
    if not ex.get("replay"):
        return
    pagina = f"""<!doctype html><html lang="pt-BR" class="{tema.classe_html()}"><head><meta charset="utf-8">
<style>{recurso("fontes.css")}{recurso("painel.css")} html,body{{margin:0;background:var(--background)}}{tema.css_iframe()}</style></head>
<body><div id="root"></div>
<script>window.EXTRAS={json.dumps({"replay": ex["replay"]}, ensure_ascii=False)};</script>
<script>{recurso("vendor.js")}</script><script>{recurso("extras.js")}</script><script>{recurso("replay_pagina.js")}</script></body></html>"""
    components.html(pagina, height=860, scrolling=False)


def pagina_simulador():
    ex = extras()
    if not ex:
        st.warning("Arquivo dados/extras.json não encontrado.")
        return
    R = ex["replay"]
    with st.sidebar:
        tema.secao("Simulador")
        cen = st.selectbox("Cenário pronto", list(CENARIOS), key="sim_cen",
                           help="Define o ponto de partida dos controles do simulador (limiar, equipe e premissas de custo).")
        st.segmented_control("Período de 2023", list(PERIODOS), key="sim_per", default="Tudo")
        st.pills("Peças", PECAS_NOMES, selection_mode="multi", key="sim_pecas")
        linhas = sorted({m["linha"] for m in R["maquinas"]})
        st.multiselect("Linhas de produção", linhas, key="sim_linhas", placeholder="Todas as linhas")
        runs = st.select_slider("Cenários de Monte Carlo", [200, 500, 1000, 2000], value=500, key="sim_runs")
        per = st.session_state.get("sim_per") or "Tudo"
        rec = _recorte_sim(R, per, st.session_state.get("sim_pecas") or [], st.session_state.get("sim_linhas") or [])
        nf = sum(sum(e[3] for e in d["c"]) + len(d["f"]) for d in rec["porDia"])
        nc = sum(len(d["c"]) for d in rec["porDia"])
        st.markdown(f'<div class="lb-info">Recorte: <b>{len(rec["dias"])} dias</b> · <b>{nf} falhas</b> · '
                    f'{nc:,} peças na janela de risco</div>'.replace(",", "."), unsafe_allow_html=True)
    if not rec["dias"] or nf == 0:
        st.info("O recorte escolhido na barra lateral não tem falhas. Amplie o período, as peças ou as linhas.")
        return
    dados = {"replay": rec, "simul": ex["simul"]}
    pagina = f"""<!doctype html><html lang="pt-BR" class="{tema.classe_html()}"><head><meta charset="utf-8">
<style>{recurso("fontes.css")}{recurso("painel.css")} html,body{{margin:0;background:var(--background)}}{tema.css_iframe()}</style></head>
<body><div id="root"></div>
<script>window.EXTRAS={json.dumps(dados, ensure_ascii=False)};window.INICIAL={json.dumps(CENARIOS[cen])};window.RUNS={runs};
window.CENARIO={json.dumps(cen, ensure_ascii=False)};</script>
<script>{recurso("vendor.js")}</script><script>{recurso("simulador.js")}</script></body></html>"""
    components.html(pagina, height=1900, scrolling=False)


# ------------------------------------------------------------------ barra lateral
PECAS_NOMES = ["Peça A", "Peça B", "Peça C", "Peça D"]
ABAS = {"model": "Previsão & Modelagem", "eda": "Análise Exploratória", "sim": "Simulador", "maquinas": "Máquinas", "dados": "Dados tratados", "perfil": "Perfil"}
FILTROS_PADRAO = {"f_pecas": [], "f_modelos": [], "f_risco": 0, "f_busca": "", "f_grupos": [], "f_expandir": False}


@st.cache_data(show_spinner=False)
def _graficos(versao: str):
    return painel_dados.graficos_eda(DADOS)


def graficos():
    eda = DADOS / "eda"
    return _graficos("|".join(f"{a.name}:{a.stat().st_mtime_ns}" for a in sorted(eda.iterdir())) if eda.exists() else "")


def filtrar_lista(lista, f):
    b = f["busca"].strip().upper()
    return [e for e in lista if (not f["pecas"] or e["comp"] in f["pecas"]) and (not f["modelos"] or e.get("model") in f["modelos"])
            and e["prob"] >= f["riscoMin"] and (not b or b in e["machine"].upper())]


def barra_lateral(d, aba):
    """Navegação, filtros da previsão, exportação da lista do dia, temas da análise exploratória e dados do modelo."""
    u = st.session_state.usuario
    for k, v in FILTROS_PADRAO.items():
        st.session_state.setdefault(k, v)
    with st.sidebar:
        tema.marca_lateral(u["nome"])
        tema.secao("Navegação")
        opcoes = ABAS
        with st.container(key="navbox"):
            escolha = st.radio("Ir para", list(opcoes), format_func=opcoes.get, index=list(opcoes).index(aba),
                               label_visibility="collapsed", key=f"nav_{aba}")
        if escolha != aba:
            st.session_state.aba = escolha
            st.rerun()
        if st.button("Rever animação", key="lb_anim", width="stretch",
                     help="Toca de novo a chegada do Beto à fábrica. Na página, o Floco explica o bloco que estiver no centro da tela."):
            animacao.reiniciar()
            st.rerun()
        if aba in ("perfil", "maquinas", "dados", "sim"):
            return None

        tema.secao("Previsão")
        dias = d["dias"]
        idia = st.selectbox("Dia (até 06:00 de)", range(len(dias) - 1, -1, -1), format_func=lambda i: dias[i]["fimLongo"], key="f_dia",
                            help="Do mais recente para o mais antigo.")
        st.pills("Peças", PECAS_NOMES, selection_mode="multi", key="f_pecas")
        modelos = sorted({e.get("model") for dd in dias for e in dd.get("lista", []) if e.get("model") not in (None, "–")})
        st.multiselect("Modelos de máquina", modelos, key="f_modelos", placeholder="Todos")
        st.slider("Risco mínimo (%)", 0, 100, step=5, key="f_risco")
        st.text_input("Buscar máquina", key="f_busca", placeholder="ex.: M048")
        f = {"dia": idia, "pecas": st.session_state.f_pecas or [], "modelos": st.session_state.f_modelos,
             "riscoMin": st.session_state.f_risco, "busca": st.session_state.f_busca}
        sel = filtrar_lista(dias[idia].get("lista", []), f)
        csv = pd.DataFrame(sel, columns=["machine", "comp", "model", "age", "prob"]).rename(columns={
            "machine": "maquina", "comp": "peca", "model": "modelo", "age": "idade_anos", "prob": "prob_falha_pct"})
        csv.insert(0, "prioridade", range(1, len(csv) + 1))
        st.download_button(f"Baixar lista do dia ({len(sel)})", csv.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           file_name=f"prioridades_ate_06h_{'-'.join(dias[idia]['fimLongo'].split('/')[::-1])}.csv", mime="text/csv", disabled=not sel, width="stretch")
        st.button("Limpar filtros", key="limpar", width="stretch", on_click=lambda: st.session_state.update(FILTROS_PADRAO))

        if aba == "eda":
            tema.secao("Análise exploratória")
            temas = list(dict.fromkeys(g["grupo"] for g in graficos()))
            st.multiselect("Temas", temas, key="f_grupos", placeholder="Todos os temas")
            st.toggle("Abrir todos os insights", key="f_expandir")
            f.update({"grupos": st.session_state.f_grupos, "expandir": st.session_state.f_expandir})

        k = d["kpi"]
        fonte = "arquivo enviado nesta sessão" if st.session_state.get("previsao") else "melhor submissão do time"
        tema.secao("Sobre o modelo")
        st.markdown(f"""<div class="lb-sobre">
          Previsão em uso: <b>{fonte}</b><br>AUC-PR na validação: <b>{k["ap"]}</b><br>
          Kaggle público: <b>{k["apKaggle"]}</b><br>Horizonte: <b>{len(dias)} dias</b> · {k["maquinas"]} máquinas</div>""",
                    unsafe_allow_html=True)
    return f


# ------------------------------------------------------------------ perfil
def tela_perfil():
    u = st.session_state.usuario
    st.markdown("""<style>
      .st-key-pf_cab { background-image: var(--gradient-header); padding: 1.75rem 1.5rem; }
      .st-key-pf_cab_in { max-width: 80rem; margin: 0 auto; width: 100%; }
      .st-key-pf_nav { margin-top: 1.25rem !important; gap: .5rem !important; }
      .st-key-pf_voltar button { background: transparent !important; color: var(--primary-foreground) !important; border: 0 !important; height: 2.25rem; padding: 0 1rem !important; }
      .st-key-pf_voltar button:hover { background: var(--accent) !important; color: var(--foreground) !important; }
      .st-key-pf_atual button { background: var(--tab-ativa, var(--background)) !important; color: var(--tab-ativa-txt, var(--brand-deep)) !important; border: 0 !important; height: 2.25rem; padding: 0 1rem !important; box-shadow: 0 1px 3px rgb(0 0 0 / .1) !important; }
      .st-key-pf_corpo { max-width: 36rem; margin: 0 auto; padding: 2.5rem 1.5rem; width: 100%; }
      .st-key-pf_form { gap: 1.5rem !important; margin-top: 1.5rem; }
      .st-key-pf_foto_linha { gap: 1.25rem !important; align-items: center !important; flex-wrap: wrap; }
      .st-key-pf_foto_linha > div { width: auto !important; flex: 0 0 auto; }
      .avatar { height: 6rem; width: 6rem; border-radius: 9999px; background: var(--secondary); color: var(--brand);
        display: flex; align-items: center; justify-content: center; overflow: hidden; }
      .avatar img { width: 100%; height: 100%; object-fit: cover; }
      .st-key-pf_foto [data-testid="stFileUploader"] section { padding: 0; border: 0; background: transparent; min-height: 0; }
      .st-key-pf_foto [data-testid="stFileUploaderDropzoneInstructions"], .st-key-pf_foto [data-testid="stFileUploaderFile"],
      .st-key-pf_foto [data-testid="stFileUploaderPagination"], .st-key-pf_foto label { display: none !important; }
      .st-key-pf_foto [data-testid="stFileUploaderDropzone"] button { font-size: 0 !important; height: 2.25rem; padding: 0 1rem !important;
        background: var(--background) !important; border: 1px solid var(--input) !important; border-radius: 6px;
        box-shadow: 0 1px 2px rgb(0 0 0 / .05) !important; color: var(--foreground) !important; display: inline-flex; align-items: center; gap: .5rem; }
      .st-key-pf_foto [data-testid="stFileUploaderDropzone"] button:hover { background: var(--accent) !important; }
      .st-key-pf_foto [data-testid="stFileUploaderDropzone"] button::after { content: "Alterar foto"; font-size: .875rem; font-weight: 500; }
      .st-key-pf_email input { color: var(--muted-foreground) !important; -webkit-text-fill-color: var(--muted-foreground); }
      .st-key-pf_email [data-testid="stTextInputRootElement"] { background: var(--secondary) !important; }
      .st-key-pf_sair_box { margin-top: 2.5rem; border-top: 1px solid var(--border); padding-top: 1.25rem; }
    </style>""", unsafe_allow_html=True)
    aplicar({"pf_voltar": ["ico:arrow-left"], "pf_atual": ["ico:user"], "pf_salvar": ["primario", "h9", "ico:save"],
             "pf_sair": ["contorno", "h9", "ico:logout"]})
    st.markdown(f"<style>.st-key-pf_foto [data-testid='stFileUploaderDropzone'] button::before {{ content:''; width:16px; height:16px; "
                f"background: currentColor; -webkit-mask: url('{mascara('camera')}') center/contain no-repeat; "
                f"mask: url('{mascara('camera')}') center/contain no-repeat; }}"
                ".st-key-pf_foto [data-testid='stFileUploaderDropzone'] button > * { display:none; }</style>",
                unsafe_allow_html=True)

    with st.container(key="pf_cab"):
        with st.container(key="pf_cab_in"):
            st.markdown('<h1 class="titulo" style="font-size:1.875rem;line-height:2.25rem">MaBiYama · Meu perfil</h1>',
                        unsafe_allow_html=True)
            with st.container(key="pf_nav", horizontal=True):
                if st.button("Painel da frota", key="pf_voltar"):
                    st.session_state.aba = "model"
                    st.rerun()
                st.button("Perfil", key="pf_atual")

    with st.container(key="pf_corpo"):
        st.markdown('<h2 style="font-size:1.25rem;line-height:1.75rem;font-weight:800">Dados pessoais</h2>',
                    unsafe_allow_html=True)
        with st.container(key="pf_form"):
            with st.container(key="pf_foto_linha", horizontal=True):
                foto = st.session_state.get("foto")
                if foto:
                    import base64
                    st.markdown(f'<div class="avatar"><img alt="Foto do perfil" src="data:image/png;base64,'
                                f'{base64.b64encode(foto).decode()}"></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="avatar">{icone("user", tam=40)}</div>', unsafe_allow_html=True)
                with st.container(key="pf_foto"):
                    arq = st.file_uploader("Foto do perfil", type=["jpg", "jpeg", "png", "webp"], key="pf_arq")
                    st.markdown('<p style="margin:.5rem 0 0;font-size:.75rem;color:var(--muted-foreground)">'
                                'JPG, PNG ou WebP · até 5 MB</p>', unsafe_allow_html=True)
            if arq is not None:
                if arq.size > 5 * 1024 * 1024:
                    st.session_state.msg_perfil = "Selecione JPG, PNG ou WebP com até 5 MB."
                elif st.session_state.get("foto") != arq.getvalue():
                    st.session_state.foto = arq.getvalue()
                    st.rerun()
            nome = st.text_input("Nome", value=u["nome"], max_chars=100, key="pf_nome")
            st.text_input("Email", value=u["email"], disabled=True, key="pf_email")
            if st.button("Salvar perfil", key="pf_salvar"):
                if nome.strip():
                    st.session_state.usuario["nome"] = nome.strip()
                    st.session_state.msg_perfil = "Perfil salvo."
                else:
                    st.session_state.msg_perfil = "Informe um nome."
        if st.session_state.get("msg_perfil"):
            st.markdown(f'<p role="status" style="margin-top:1rem;font-size:.875rem">{st.session_state.msg_perfil}</p>',
                        unsafe_allow_html=True)
        with st.container(key="pf_sair_box"):
            if st.button("Sair da conta", key="pf_sair"):
                t = st.session_state.get("tema", "claro")
                st.session_state.clear()
                st.session_state.tema = t
                st.rerun()


# ------------------------------------------------------------------ main
def main():
    css_base()
    if "usuario" not in st.session_state:
        tela_login()
        return
    aba = st.session_state.get("aba", "model")
    animacao.capa()  # cobre a tela até a cena de boas-vindas abrir (só na 1ª vez / ao rever)
    d = dados_painel(st.session_state.get("previsao"))
    filtros = barra_lateral(d, aba)
    if aba == "perfil":
        tela_perfil()
        tema.rodape_lateral()
        ajudantes(d, aba, filtros)
        return
    cabecalho_painel(aba)
    if aba == "dados":
        paginas.pagina_dados()
    elif aba == "sim":
        pagina_simulador()
    elif aba == "maquinas":
        prev = st.session_state.get("previsao")
        sub = pd.read_csv(io.BytesIO(prev)) if prev else pd.read_csv(DADOS / "previsao.csv")
        d = dados_painel(prev)
        prob = {(e["machine"], "peca_" + e["comp"][-1], dd["fimLongo"]): e["prob"] for dd in d["dias"] for e in dd.get("lista", [])}
        paginas.pagina_maquina(sub, prob, replay=replay_frota)
    else:
        conteudo_painel(aba, filtros)
    tema.rodape_lateral()
    ajudantes(d, aba, filtros)


def ajudantes(d, aba, filtros):
    """Beto e Floco: cena de boas-vindas e, depois, a explicação do bloco no centro da tela (animacao.py)."""
    idia = (filtros or {}).get("dia", len(d["dias"]) - 1)
    lista = filtrar_lista(d["dias"][idia].get("lista", []), filtros) if filtros else None
    animacao.montar(d, aba, idia, lista, graficos() if aba == "eda" else None)


main()
