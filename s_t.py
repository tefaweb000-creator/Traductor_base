import re
import html
import random
from io import BytesIO
from datetime import datetime
from difflib import SequenceMatcher

import pandas as pd
import requests
import streamlit as st
from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from deep_translator import GoogleTranslator
from gtts import gTTS
from streamlit_bokeh_events import streamlit_bokeh_events

try:
    from streamlit_lottie import st_lottie
except ImportError:
    st_lottie = None

# ───────────────────────── CONFIG ─────────────────────────
# Pega aquí URLs .json de lottiefiles.com (si quedan vacías, se usa un emoji)
LOTTIE_HEADER = ""
LOTTIE_GREAT = ""
LOTTIE_GOOD = ""
LOTTIE_RETRY = ""

LANGS = {
    "Español":   {"code": "es", "speech": "es-CO", "tld": "com.mx"},
    "Inglés":    {"code": "en", "speech": "en-US", "tld": "com"},
    "Francés":   {"code": "fr", "speech": "fr-FR", "tld": "fr"},
    "Portugués": {"code": "pt", "speech": "pt-BR", "tld": "com.br"},
    "Italiano":  {"code": "it", "speech": "it-IT", "tld": "it"},
    "Alemán":    {"code": "de", "speech": "de-DE", "tld": "de"},
    "Japonés":   {"code": "ja", "speech": "ja-JP", "tld": "com"},
}
NATIVE_OPTIONS = ["Español", "Inglés", "Portugués"]

FRASES = {
    "Básico": {
        "Viajes": ["¿Dónde está la estación de tren?", "Quisiera un boleto de ida y vuelta.", "¿Cuánto cuesta esta habitación?"],
        "Universidad": ["¿A qué hora empieza la clase?", "Necesito entregar mi tarea mañana.", "La biblioteca está cerrada hoy."],
        "Comida": ["Quiero un café con leche, por favor.", "¿Me trae la cuenta, por favor?", "Esta sopa está deliciosa."],
        "Conversación": ["Mucho gusto, ¿cómo te llamas?", "Hoy hace muy buen clima.", "¿Qué haces el fin de semana?"],
    },
    "Intermedio": {
        "Viajes": ["Perdí mi equipaje y necesito ayuda para encontrarlo.", "¿Me podría recomendar un lugar para visitar cerca de aquí?", "El vuelo se retrasó dos horas por el clima."],
        "Universidad": ["Estoy preparando una presentación sobre psicología del consumidor.", "¿Podrías explicarme otra vez el último tema?", "Si estudio todos los días, voy a aprobar el examen."],
        "Comida": ["Soy alérgico a los mariscos, ¿este plato los tiene?", "Me gustaría reservar una mesa para cuatro personas.", "La comida estaba buena, pero el servicio fue lento."],
        "Conversación": ["Desde que me mudé, he conocido a mucha gente nueva.", "No estoy de acuerdo, pero entiendo tu punto de vista.", "Me encantaría viajar por el mundo algún día."],
    },
}

st.set_page_config(page_title="Tutor de idiomas", page_icon="🗣️", layout="centered")

# ───────────────────────── ESTILO ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Literata:opsz,wght@7..72,500;7..72,700&display=swap');

:root{
  --night:#13112b; --violet:#8b7cf6; --teal:#2dd4bf; --coral:#fb7185; --ink:#f1effa;
  --glass:rgba(255,255,255,.07); --glass-strong:rgba(255,255,255,.11); --edge:rgba(255,255,255,.16);
}
html, body, [class*="css"], .stMarkdown, p, label, input, textarea { font-family:'Inter', system-ui, sans-serif; }
h1, h2, h3, .serif { font-family:'Literata', Georgia, serif !important; letter-spacing:-.01em; }

.stApp{
  background:
    radial-gradient(40rem 30rem at 10% 5%, rgba(139,124,246,.45), transparent 60%),
    radial-gradient(35rem 28rem at 95% 25%, rgba(45,212,191,.28), transparent 60%),
    radial-gradient(38rem 30rem at 40% 105%, rgba(251,113,133,.30), transparent 60%),
    var(--night);
  background-attachment:fixed;
}
header[data-testid="stHeader"]{ background:transparent; }

/* Tarjetas de vidrio */
[class*="st-key-glass"]{
  background:var(--glass);
  backdrop-filter:blur(22px) saturate(150%);
  -webkit-backdrop-filter:blur(22px) saturate(150%);
  border:1px solid var(--edge);
  border-radius:26px;
  padding:1.5rem 1.5rem 1.1rem;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.18), 0 20px 50px rgba(5,3,25,.45);
  margin-bottom:1.1rem;
}
.step{ display:flex; align-items:center; gap:.7rem; margin:0 0 .9rem; }
.step b{
  width:2rem; height:2rem; border-radius:50%; display:grid; place-items:center;
  background:var(--glass-strong); border:1px solid var(--edge); font-weight:600; font-size:.9rem;
}
.step span{ font-family:'Literata', serif; font-size:1.25rem; }

/* Sidebar */
[data-testid="stSidebar"] > div:first-child{
  background:rgba(19,17,43,.55); backdrop-filter:blur(24px); -webkit-backdrop-filter:blur(24px);
  border-right:1px solid var(--edge);
}

/* Widgets */
.stButton > button, .stDownloadButton > button{
  border-radius:999px; background:var(--glass-strong); color:var(--ink);
  border:1px solid var(--edge); backdrop-filter:blur(12px); padding:.55rem 1.3rem; font-weight:500;
  transition:background .2s, border-color .2s;
}
.stButton > button:hover, .stDownloadButton > button:hover{ background:rgba(139,124,246,.28); border-color:var(--violet); color:#fff; }
.stButton > button:focus-visible{ outline:2px solid var(--teal); outline-offset:2px; }
div[data-baseweb="select"] > div, .stTextInput input{
  background:rgba(255,255,255,.06) !important; border:1px solid var(--edge) !important; border-radius:14px !important;
}
[data-testid="stMetric"]{
  background:rgba(255,255,255,.05); border:1px solid var(--edge); border-radius:18px; padding:.8rem 1rem;
}
audio{ width:100%; border-radius:999px; }

/* Hero */
.hero{ padding:1.2rem 0 1.6rem; }
.hero h1{ font-size:clamp(2.2rem, 6vw, 3.3rem); line-height:1.05; margin:0; color:var(--ink); }
.hero p{ color:rgba(241,239,250,.72); max-width:34rem; margin:.6rem 0 0; font-size:1.05rem; }

/* Frase: el elemento protagonista */
.phrase{
  font-family:'Literata', serif; font-size:clamp(1.5rem, 4.5vw, 2.1rem); line-height:1.3;
  color:#fff; margin:.2rem 0 .5rem;
}
.phrase-src{ color:rgba(241,239,250,.6); font-size:.95rem; margin-bottom:1rem; }

/* Feedback */
.score-wrap{ display:flex; align-items:baseline; gap:.8rem; margin:.4rem 0 .8rem; animation:pop .45s ease-out; }
.score{ font-family:'Literata', serif; font-size:3.4rem; font-weight:700; line-height:1; }
.score-msg{ color:rgba(241,239,250,.8); }
.chips{ display:flex; flex-wrap:wrap; gap:.4rem; margin:.4rem 0 .8rem; }
.chip{ padding:.3rem .75rem; border-radius:999px; font-size:.98rem; border:1px solid transparent; }
.chip.ok{ background:rgba(45,212,191,.16); color:#7ef0dd; border-color:rgba(45,212,191,.35); }
.chip.bad{ background:rgba(251,113,133,.16); color:#ffb1bf; border-color:rgba(251,113,133,.35); text-decoration:underline wavy rgba(251,113,133,.6); }
.said{ color:rgba(241,239,250,.65); font-size:.92rem; }
@keyframes pop{ from{ opacity:0; transform:scale(.96);} to{ opacity:1; transform:none;} }
@media (prefers-reduced-motion: reduce){ .score-wrap{ animation:none; } }
</style>
""", unsafe_allow_html=True)

# ───────────────────────── ESTADO ─────────────────────────
for k, v in {
    "src_text": "", "target_text": "", "pair": None,
    "last_dict_ts": None, "last_rep_ts": None,
    "feedback": None, "history": [], "streak": 0, "best_streak": 0,
}.items():
    st.session_state.setdefault(k, v)

# ───────────────────────── HELPERS ─────────────────────────
@st.cache_data(show_spinner=False)
def load_lottie(url):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=6)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def show_lottie(url, emoji, height=120, key=None):
    data = load_lottie(url)
    if data and st_lottie:
        st_lottie(data, height=height, key=key)
    else:
        st.markdown(f"<div style='font-size:{height // 2}px;line-height:1.2'>{emoji}</div>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def translate(text, src, dest):
    if src == dest:
        return text
    return GoogleTranslator(source=src, target=dest).translate(text)


@st.cache_data(show_spinner=False)
def tts_bytes(text, lang, tld, slow):
    buf = BytesIO()
    gTTS(text, lang=lang, tld=tld, slow=slow).write_to_fp(buf)
    return buf.getvalue()


def tokens(text, code):
    t = re.sub(r"[^\w\s']", " ", text.lower())
    if code == "ja":
        return [c for c in t if not c.isspace()]
    return t.split()


def compare(expected, said, code):
    exp, sd = tokens(expected, code), tokens(said, code)
    sm = SequenceMatcher(None, exp, sd)
    chips = []
    for tag, i1, i2, _, _ in sm.get_opcodes():
        cls = "ok" if tag == "equal" else "bad"
        chips += [f"<span class='chip {cls}'>{html.escape(w)}</span>" for w in exp[i1:i2]]
    return round(sm.ratio() * 100), "".join(chips)


def mic_button(label, lang, event, key):
    btn = Button(label=label, width=300, height=48, button_type="primary")
    btn.js_on_event("button_click", CustomJS(code=f"""
        var r = new webkitSpeechRecognition();
        r.continuous = false;
        r.interimResults = false;
        r.lang = '{lang}';
        r.onresult = function (e) {{
            var v = e.results[0][0].transcript;
            if (v) {{
                document.dispatchEvent(new CustomEvent("{event}", {{detail: {{text: v, ts: Date.now()}}}}));
            }}
        }};
        r.start();
    """))
    res = streamlit_bokeh_events(
        btn, events=event, key=f"{key}_{lang}",
        refresh_on_update=False, override_height=62, debounce_time=0,
    )
    return res.get(event) if res and event in res else None


def set_phrase(native_text, target_text):
    st.session_state.src_text = native_text
    st.session_state.target_text = target_text
    st.session_state.feedback = None


def step(n, title):
    st.markdown(f"<div class='step'><b>{n}</b><span>{title}</span></div>", unsafe_allow_html=True)

# ───────────────────────── SIDEBAR ─────────────────────────
with st.sidebar:
    st.markdown("<h3>Ajustes</h3>", unsafe_allow_html=True)
    native = st.selectbox("Tu idioma", NATIVE_OPTIONS)
    target = st.selectbox("Idioma que practicas", [l for l in LANGS if l != native])
    st.divider()
    st.markdown(
        "**Cómo funciona**\n\n"
        "1. Elige o dicta una frase.\n"
        "2. Escúchala, normal o lenta.\n"
        "3. Repítela en voz alta y mira tu puntaje.\n\n"
        "El micrófono funciona en Chrome o Edge."
    )

N, T = LANGS[native], LANGS[target]

if st.session_state.pair != (native, target):
    st.session_state.pair = (native, target)
    set_phrase("", "")

# ───────────────────────── HERO ─────────────────────────
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown(
        f"<div class='hero'><h1>Habla {target.lower()} en voz alta</h1>"
        f"<p>Escucha una frase, repítela y la app te dice qué palabras te salieron bien.</p></div>",
        unsafe_allow_html=True,
    )
with c2:
    show_lottie(LOTTIE_HEADER, "🗣️", height=130, key="hero")

# ───────────────────────── 1 · FRASE ─────────────────────────
with st.container(key="glass_frase"):
    step(1, "Elige tu frase")
    modo = st.radio("Modo", ["Frase sugerida", "Mi frase"], horizontal=True, label_visibility="collapsed")

    if modo == "Frase sugerida":
        a, b = st.columns(2)
        nivel = a.selectbox("Nivel", list(FRASES))
        tema = b.selectbox("Tema", list(FRASES[nivel]))
        if st.button("🎲  Darme una frase"):
            base = random.choice(FRASES[nivel][tema])
            try:
                with st.spinner("Traduciendo…"):
                    set_phrase(translate(base, "es", N["code"]), translate(base, "es", T["code"]))
            except Exception:
                st.error("No se pudo traducir. Revisa tu conexión y vuelve a intentarlo.")
    else:
        payload = mic_button(f"🎤  Dictar en {native.lower()}", N["speech"], "DICTAR", "dictar")
        if payload and payload.get("ts") != st.session_state.last_dict_ts:
            st.session_state.last_dict_ts = payload["ts"]
            try:
                set_phrase(payload["text"], translate(payload["text"], N["code"], T["code"]))
            except Exception:
                st.error("No se pudo traducir lo que dictaste. Inténtalo de nuevo.")
        escrito = st.text_input("O escríbela", placeholder=f"Escribe una frase en {native.lower()}")
        if st.button("Usar esta frase") and escrito.strip():
            try:
                set_phrase(escrito.strip(), translate(escrito.strip(), N["code"], T["code"]))
            except Exception:
                st.error("No se pudo traducir. Revisa tu conexión y vuelve a intentarlo.")

# ───────────────────────── 2 · ESCUCHA ─────────────────────────
if st.session_state.target_text:
    with st.container(key="glass_escucha"):
        step(2, "Escúchala")
        st.markdown(
            f"<div class='phrase'>{html.escape(st.session_state.target_text)}</div>"
            f"<div class='phrase-src'>{html.escape(st.session_state.src_text)}</div>",
            unsafe_allow_html=True,
        )
        try:
            a, b = st.columns(2)
            with a:
                st.caption("Velocidad normal")
                st.audio(tts_bytes(st.session_state.target_text, T["code"], T["tld"], False), format="audio/mp3")
            with b:
                st.caption("Lento")
                st.audio(tts_bytes(st.session_state.target_text, T["code"], T["tld"], True), format="audio/mp3")
        except Exception:
            st.error("No se pudo generar el audio. Espera un momento y recarga.")

    # ───────────────────── 3 · REPITE ─────────────────────
    with st.container(key="glass_repite"):
        step(3, "Repítela")
        rep = mic_button(f"🎤  Hablar en {target.lower()}", T["speech"], "REPETIR", "repetir")

        if rep and rep.get("ts") != st.session_state.last_rep_ts:
            st.session_state.last_rep_ts = rep["ts"]
            score, chips = compare(st.session_state.target_text, rep["text"], T["code"])
            st.session_state.feedback = {"score": score, "chips": chips, "said": rep["text"]}
            st.session_state.history.append({
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "idioma": target,
                "frase": st.session_state.target_text,
                "dijiste": rep["text"],
                "puntaje": score,
            })
            st.session_state.streak = st.session_state.streak + 1 if score >= 80 else 0
            st.session_state.best_streak = max(st.session_state.best_streak, st.session_state.streak)

        fb = st.session_state.feedback
        if fb:
            s = fb["score"]
            if s >= 90:
                color, msg, lot, emo = "var(--teal)", "Suena muy natural. Prueba otra frase.", LOTTIE_GREAT, "🔥"
            elif s >= 70:
                color, msg, lot, emo = "var(--violet)", "Casi. Fíjate en las palabras en rojo.", LOTTIE_GOOD, "💪"
            elif s >= 40:
                color, msg, lot, emo = "#fbbf24", "Escúchala en lento y vuelve a intentarlo.", LOTTIE_RETRY, "🐢"
            else:
                color, msg, lot, emo = "var(--coral)", "Repite despacio, palabra por palabra.", LOTTIE_RETRY, "🎯"

            f1, f2 = st.columns([3, 1])
            with f1:
                st.markdown(
                    f"<div class='score-wrap'><span class='score' style='color:{color}'>{s}</span>"
                    f"<span class='score-msg'>{msg}</span></div>"
                    f"<div class='chips'>{fb['chips']}</div>"
                    f"<div class='said'>Escuché: “{html.escape(fb['said'])}”</div>",
                    unsafe_allow_html=True,
                )
            with f2:
                show_lottie(lot, emo, height=110, key=f"fb_{st.session_state.last_rep_ts}")
        else:
            st.caption("Presiona el micrófono y di la frase completa.")

# ───────────────────────── PROGRESO ─────────────────────────
hist = st.session_state.history
if hist:
    with st.container(key="glass_progreso"):
        st.markdown("<div class='step'><span>Tu sesión</span></div>", unsafe_allow_html=True)
        df = pd.DataFrame(hist)
        m1, m2, m3 = st.columns(3)
        m1.metric("Intentos", len(df))
        m2.metric("Promedio", f"{df['puntaje'].mean():.0f}")
        m3.metric("Mejor racha", st.session_state.best_streak, help="Intentos seguidos con 80 o más")
        if len(df) > 1:
            st.line_chart(df["puntaje"], height=160)
        a, b = st.columns(2)
        a.download_button(
            "Descargar historial", df.to_csv(index=False).encode("utf-8"),
            file_name="historial_tutor.csv", mime="text/csv",
        )
        if b.button("Reiniciar sesión"):
            for k in ("history", "streak", "best_streak", "feedback"):
                st.session_state[k] = [] if k == "history" else (None if k == "feedback" else 0)
            st.rerun()