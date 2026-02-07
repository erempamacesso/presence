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

# --------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (MODO TOTEM)
# --------------------------------------------------
st.set_page_config(
    page_title="Registro de Presença",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --------------------------------------------------
# CSS – MOBILE / TOTEM
# --------------------------------------------------
st.markdown("""
<style>

/* RESET GERAL */
html, body {
    margin: 0;
    padding: 0;
    height: 100%;
    background: black;
    overflow: hidden;
}

.block-container {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}

/* REMOVE BLOCOS FANTASMAS */
div[data-testid="stVerticalBlock"]:empty {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ESCONDE ELEMENTOS DO STREAMLIT */
header, footer, #MainMenu {
    display: none !important;
}

/* CÂMERA NO TOPO */
div[data-testid="stCameraInput"] {
    width: 100vw !important;
    height: 70vh !important;
    margin: 0 !important;
    padding: 0 !important;
    display: flex;
    justify-content: center;
    align-items: center;
    background: black;
}

div[data-testid="stCameraInput"] > div {
    width: 100% !important;
    height: 100% !important;
}

/* VÍDEO */
div[data-testid="stCameraInput"] video,
div[data-testid="stCameraInput"] img {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
}

/* BOTÃO */
div[data-testid="stCameraInput"] button {
    width: 80% !important;
    height: 60px !important;
    margin: 16px auto 0 auto !important;
    display: block !important;

    background: #D32F2F !important;
    border-radius: 30px !important;
    border: 3px solid white !important;

    color: transparent !important;
    position: relative !important;
    box-shadow: 0 4px 15px rgba(0,0,0,0.6);
}

/* TEXTO DO BOTÃO */
div[data-testid="stCameraInput"] button::after {
    content: "REGISTRAR PRESENÇA";
    color: white;
    font-size: 18px;
    font-weight: bold;
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* FEEDBACK TELA CHEIA */
.overlay-feedback {
    position: fixed;
    inset: 0;
    z-index: 99999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: sans-serif;
    color: white;
}

.bg-verde { background: #2ecc71; }
.bg-amarelo { background: #f1c40f; color: #333; }
.bg-vermelho { background: #e74c3c; }

.status-icon { font-size: 80px; margin-bottom: 20px; }
.status-text { font-size: 32px; font-weight: bold; text-align: center; }

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# BANCO DE DADOS
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
            encs.append(np.array(raw, dtype=np.float64))
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
        return "NOVO"
    else:
        return "DUPLICADO"

# --------------------------------------------------
# ESTADO
# --------------------------------------------------
if "faces" not in st.session_state:
    st.session_state.faces, st.session_state.ids, st.session_state.nomes = carregar_faces()

if "cam_key" not in st.session_state:
    st.session_state.cam_key = 0

# --------------------------------------------------
# INTERFACE
# --------------------------------------------------
img = st.camera_input(
    "Ponto",
    label_visibility="hidden",
    key=f"cam_{st.session_state.cam_key}"
)

# --------------------------------------------------
# PROCESSAMENTO
# --------------------------------------------------
if img:
    bytes_data = img.getvalue()
    frame = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb)
    face_encodings = face_recognition.face_encodings(rgb, face_locations)

    if face_encodings:
        enc = face_encodings[0]
        matches = face_recognition.compare_faces(
            st.session_state.faces,
            enc,
            tolerance=0.5
        )

        if True in matches:
            idx = matches.index(True)
            aluno_id = st.session_state.ids[idx]
            nome = st.session_state.nomes[idx]

            resultado = registrar(aluno_id, nome)

            if resultado == "NOVO":
                st.markdown(f"""
                <div class="overlay-feedback bg-verde">
                    <div class="status-icon">✅</div>
                    <div class="status-text">PRESENÇA REGISTRADA<br>{nome}</div>
                </div>
                """, unsafe_allow_html=True)

            else:
                st.markdown(f"""
                <div class="overlay-feedback bg-amarelo">
                    <div class="status-icon">⚠️</div>
                    <div class="status-text">JÁ REGISTRADO HOJE<br>{nome}</div>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.markdown("""
            <div class="overlay-feedback bg-vermelho">
                <div class="status-icon">❌</div>
                <div class="status-text">NÃO RECONHECIDO</div>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="overlay-feedback bg-vermelho">
            <div class="status-icon">❌</div>
            <div class="status-text">NENHUM ROSTO DETECTADO</div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------
    # RETORNO AUTOMÁTICO
    # -------------------------------
    time.sleep(2)
    st.session_state.cam_key += 1
    st.rerun()
