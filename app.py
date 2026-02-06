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

# ---------------- CONFIGURAÇÃO DA PÁGINA ----------------
st.set_page_config(
    page_title="Ponto",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------- CSS ESTILO APP (9:16 REAL) ----------------
st.markdown("""
<style>

/* LIMPEZA GERAL */
.block-container {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}
header, footer, #MainMenu {
    display: none !important;
}

/* CONTAINER CENTRAL */
div[data-testid="stCameraInput"] {
    width: 100% !important;
    display: flex;
    justify-content: center;
}

/* FRAME 9:16 */
div[data-testid="stCameraInput"] > div {
    width: 92% !important;
    max-width: 420px !important;
    aspect-ratio: 9 / 16 !important;

    background-color: black;
    border-radius: 22px;
    overflow: hidden;
}

/* VIDEO (DESKTOP) */
div[data-testid="stCameraInput"] video {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
}

/* IMG (MOBILE / FALLBACK) */
div[data-testid="stCameraInput"] img {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
}

/* BOTÃO */
div[data-testid="stCameraInput"] button {
    width: 65% !important;
    margin: 16px auto 20px auto !important;
    display: block !important;
    height: 54px !important;

    border-radius: 27px !important;
    background-color: #FF4B4B !important;
    border: 2px solid white !important;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.4) !important;

    color: transparent !important;
    position: relative !important;
}

/* TEXTO DO BOTÃO */
div[data-testid="stCameraInput"] button::after {
    content: "REGISTRAR PRESENÇA";
    color: white;
    font-size: 15px;
    font-weight: bold;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
}

</style>
""", unsafe_allow_html=True)

# ---------------- CONEXÃO COM O BANCO ----------------
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# ---------------- FUNÇÕES ----------------
def load_known_faces():
    response = supabase.table('alunos').select("*").execute()
    known_encodings, known_ids, known_names = [], [], []

    for aluno in response.data:
        if aluno.get("face_encoding"):
            raw = aluno["face_encoding"]
            if isinstance(raw, str):
                raw = json.loads(raw)
            known_encodings.append(np.array(raw, dtype=np.float64))
            known_ids.append(aluno["id"])
            known_names.append(aluno.get("nome", "Sem Nome"))

    return known_encodings, known_ids, known_names


def registrar_presenca(pessoa_id, nome):
    tz = pytz.timezone("America/Recife")
    agora = datetime.now(tz)
    inicio_dia = agora.strftime("%Y-%m-%d 00:00:00")

    check = supabase.table("presenca") \
        .select("*") \
        .eq("aluno_id", pessoa_id) \
        .gte("data_hora", inicio_dia) \
        .execute()

    if not check.data:
        supabase.table("presenca").insert({
            "aluno_id": pessoa_id,
            "nome_aluno": nome,
            "data_hora": agora.strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        return True, f"✅ PRESENÇA REGISTRADA: {nome}"
    else:
        return False, f"⚠️ {nome} JÁ REGISTRADO"


# ---------------- ESTADO ----------------
if "known_encodings" not in st.session_state:
    st.session_state.known_encodings, st.session_state.known_ids, st.session_state.known_names = load_known_faces()

if "camera_key" not in st.session_state:
    st.session_state.camera_key = 0

# ---------------- CÂMERA ----------------
imagem = st.camera_input(
    "Ponto",
    label_visibility="hidden",
    key=f"cam_{st.session_state.camera_key}"
)

# ---------------- PROCESSAMENTO ----------------
if imagem:
    bytes_data = imagem.getvalue()
    frame = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    faces = face_recognition.face_encodings(rgb)

    if not faces:
        st.warning("Rosto não detectado. Aproxime-se.")
    else:
        encoding = faces[0]
        matches = face_recognition.compare_faces(
            st.session_state.known_encodings,
            encoding,
            tolerance=0.5
        )

        if True in matches:
            idx = matches.index(True)
            ok, msg = registrar_presenca(
                st.session_state.known_ids[idx],
                st.session_state.known_names[idx]
            )

            if ok:
                st.success(msg)
                st.balloons()
            else:
                st.info(msg)
        else:
            st.error("Aluno não cadastrado.")

    time.sleep(2)
    st.session_state.camera_key += 1
    st.rerun()
