import streamlit as st
import face_recognition
import cv2
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from datetime import datetime
import pytz
import json
import time
import base64

# --------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (MODO KIOSK)
# --------------------------------------------------
st.set_page_config(
    page_title="Registro de Presença",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --------------------------------------------------
# CSS – VISUAL DE TOTEM ESCOLAR
# --------------------------------------------------
st.markdown("""
<style>

/* LIMPEZA TOTAL */
.block-container {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}
header, footer, #MainMenu {
    display: none !important;
}
html, body {
    overflow: hidden !important;
}

/* INSTRUÇÃO */
.instrucao {
    text-align: center;
    font-size: 18px;
    margin: 12px 0;
}

/* CONTAINER DA CAMERA */
div[data-testid="stCameraInput"] {
    display: flex;
    justify-content: center;
}

/* FRAME */
div[data-testid="stCameraInput"] > div {
    width: 94% !important;
    max-width: 420px !important;
    background: #000;
    border-radius: 22px;
    padding: 10px;
    box-shadow: 0 12px 30px rgba(0,0,0,.3);
    position: relative;
}

/* CAMERA */
div[data-testid="stCameraInput"] video,
div[data-testid="stCameraInput"] img {
    width: 100% !important;
    border-radius: 16px;
    object-fit: cover;
}

/* MÁSCARA OVAL */
.mascara {
    position: absolute;
    inset: 10px;
    pointer-events: none;
}
.mascara::before {
    content: "";
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,.55);
}
.mascara::after {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 65%;
    height: 55%;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    background: transparent;
    box-shadow: 0 0 0 9999px rgba(0,0,0,.55);
    border: 3px solid rgba(255,255,255,.6);
}

/* BOTÃO */
div[data-testid="stCameraInput"] button {
    width: 80% !important;
    height: 56px !important;
    margin: 18px auto !important;
    display: block !important;
    background: #D32F2F !important;
    border-radius: 28px !important;
    border: none !important;
    color: transparent !important;
    position: relative;
}
div[data-testid="stCameraInput"] button::after {
    content: "REGISTRAR PRESENÇA";
    color: white;
    font-size: 16px;
    font-weight: bold;
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* SUCESSO */
.sucesso {
    border: 4px solid #2ecc71 !important;
    box-shadow: 0 0 25px #2ecc71 !important;
}

/* TELA VERDE */
.tela-verde {
    position: fixed;
    inset: 0;
    background: #2ecc71;
    color: white;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 26px;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# SOM DE CONFIRMAÇÃO
# --------------------------------------------------
def beep():
    som = base64.b64encode(open("beep.mp3", "rb").read()).decode()
    st.markdown(f"""
    <audio autoplay>
        <source src="data:audio/mp3;base64,{som}" type="audio/mp3">
    </audio>
    """, unsafe_allow_html=True)

# --------------------------------------------------
# BANCO
# --------------------------------------------------
load_dotenv()
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# --------------------------------------------------
# FUNÇÕES
# --------------------------------------------------
def carregar_faces():
    dados = supabase.table("alunos").select("*").execute().data
    encs, ids, nomes = [], [], []
    for a in dados:
        if a.get("face_encoding"):
            raw = a["face_encoding"]
            if isinstance(raw, str):
                raw = json.loads(raw)
            encs.append(np.array(raw))
            ids.append(a["id"])
            nomes.append(a.get("nome", "Aluno"))
    return encs, ids, nomes

def registrar(aluno_id, nome):
    tz = pytz.timezone("America/Recife")
    agora = datetime.now(tz)
    inicio = agora.strftime("%Y-%m-%d 00:00:00")

    check = supabase.table("presenca") \
        .select("*") \
        .eq("aluno_id", aluno_id) \
        .gte("data_hora", inicio) \
        .execute()

    if not check.data:
        supabase.table("presenca").insert({
            "aluno_id": aluno_id,
            "nome_aluno": nome,
            "data_hora": agora.strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        return True
    return False

# --------------------------------------------------
# ESTADO
# --------------------------------------------------
if "faces" not in st.session_state:
    st.session_state.faces, st.session_state.ids, st.session_state.nomes = carregar_faces()

if "key" not in st.session_state:
    st.session_state.key = 0

# --------------------------------------------------
# UI
# --------------------------------------------------
st.markdown('<div class="instrucao">📸 Centralize o rosto<br>👇 Toque em <b>Registrar Presença</b></div>', unsafe_allow_html=True)

img = st.camera_input("Ponto", label_visibility="hidden", key=f"cam_{st.session_state.key}")

st.markdown('<div class="mascara"></div>', unsafe_allow_html=True)

# --------------------------------------------------
# PROCESSAMENTO
# --------------------------------------------------
if img:
    frame = cv2.imdecode(np.frombuffer(img.getvalue(), np.uint8), cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = face_recognition.face_encodings(rgb)

    if faces:
        enc = faces[0]
        matches = face_recognition.compare_faces(st.session_state.faces, enc, tolerance=0.5)

        if True in matches:
            idx = matches.index(True)
            sucesso = registrar(st.session_state.ids[idx], st.session_state.nomes[idx])

            if sucesso:
                beep()
                st.markdown('<div class="tela-verde">✅ PRESENÇA REGISTRADA<br>ACESSO LIBERADO</div>', unsafe_allow_html=True)
                time.sleep(2)
        else:
            st.error("❌ ROSTO NÃO RECONHECIDO")
            time.sleep(2)
    else:
        st.warning("Rosto não detectado")
        time.sleep(2)

    st.session_state.key += 1
    st.rerun()
