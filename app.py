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
# 1. CONFIGURAÇÃO DA PÁGINA
# --------------------------------------------------
st.set_page_config(
    page_title="Registro de Presença",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --------------------------------------------------
# 2. CSS CORRIGIDO (VISUAL TOTEM)
# --------------------------------------------------
st.markdown("""
<style>
    /* RESET TOTAL */
    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }
    
    header, footer, #MainMenu {
        display: none !important;
    }

    /* FUNDO PRETO */
    .stApp {
        background-color: black;
    }

    /* CONTAINER DA CÂMERA */
    div[data-testid="stCameraInput"] {
        width: 100% !important;
        background: black;
        display: flex;
        justify-content: center;
    }

    div[data-testid="stCameraInput"] > div {
        height: 85vh !important; /* Altura da câmera */
        width: 100% !important;
        border-radius: 0 !important;
    }

    div[data-testid="stCameraInput"] video {
        width: 100% !important;
        height: 100% !important;
        object-fit: cover !important; /* Preenche tudo */
    }

    /* BOTÃO FLUTUANTE */
    div[data-testid="stCameraInput"] button {
        width: 60% !important;
        height: 60px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        display: block !important;
        
        /* POSICIONA SOBRE A IMAGEM */
        margin-top: -90px !important; 
        position: relative;
        z-index: 999;
        
        background: #D32F2F !important;
        border-radius: 30px !important;
        border: 3px solid white !important;
        color: transparent !important; /* Esconde texto original */
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
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

    /* OVERLAYS DE FEEDBACK (TELA CHEIA) */
    .overlay-feedback {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 99999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: white;
        font-family: sans-serif;
        animation: fadeIn 0.3s ease-in-out;
    }

    .bg-verde { background-color: #2ecc71; }
    .bg-amarelo { background-color: #f1c40f; color: #333; }
    .bg-vermelho { background-color: #e74c3c; }

    .status-icon { font-size: 80px; margin-bottom: 20px; }
    .status-text { font-size: 32px; font-weight: bold; text-align: center; }

    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. CONEXÃO E FUNÇÕES
# --------------------------------------------------
load_dotenv()
try:
    supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
except:
    st.error("Erro de conexão Supabase.")

def carregar_faces():
    try:
        dados = supabase.table("alunos").select("*").execute().data
        encs, ids, nomes = [], [], []
        for a in dados:
            if a.get("face_encoding"):
                try:
                    raw = a["face_encoding"]
                    if isinstance(raw, str): raw = json.loads(raw)
                    encs.append(np.array(raw, dtype=np.float64))
                    ids.append(a["id"])
                    nomes.append(a.get("nome", "Aluno"))
                except: pass
        return encs, ids, nomes
    except: return [], [], []

def registrar(aluno_id, nome):
    tz = pytz.timezone("America/Recife")
    agora = datetime.now(tz)
    inicio = agora.strftime("%Y-%m-%d 00:00:00")
    try:
        check = supabase.table("presenca").select("*").eq("aluno_id", aluno_id).gte("data_hora", inicio).execute()
        if not check.data:
            supabase.table("presenca").insert({
                "aluno_id": aluno_id, "nome_aluno": nome, "data_hora": agora.strftime("%Y-%m-%d %H:%M:%S")
            }).execute()
            return "NOVO"
        return "DUPLICADO"
    except: return "ERRO"

# --------------------------------------------------
# 4. LÓGICA PRINCIPAL
# --------------------------------------------------
if "faces" not in st.session_state:
    st.session_state.faces, st.session_state.ids, st.session_state.nomes = carregar_faces()

if "cam_key" not in st.session_state:
    st.session_state.cam_key = 0

# CAMERA INPUT
img = st.camera_input("Ponto", label_visibility="hidden", key=f"cam_{st.session_state.cam_key}")

if img:
    if not st.session_state.faces:
        st.error("Sem alunos cadastrados.")
    else:
        # Processamento
        bytes_data = img.getvalue()
        frame = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb)
        face_encodings = face_recognition.face_encodings(rgb, face_locations)

        if face_encodings:
            enc = face_encodings[0]
            matches = face_recognition.compare_faces(st.session_state.faces, enc, tolerance=0.5)
            
            if True in matches:
                idx = matches.index(True)
                res = registrar(st.session_state.ids[idx], st.session_state.nomes[idx])
                nome = st.session_state.nomes[idx]

                if res == "NOVO":
                    st.markdown(f"""<div class="overlay-feedback bg-verde"><div class="status-icon">✅</div><div class="status-text">PRESENÇA REGISTRADA<br>{nome}</div></div>""", unsafe_allow_html=True)
                    st.balloons()
                elif res == "DUPLICADO":
                    st.markdown(f"""<div class="overlay-feedback bg-amarelo"><div class="status-icon">⚠️</div><div class="status-text">JÁ REGISTRADO<br>{nome}</div></div>""", unsafe_allow_html=True)
                
                time.sleep(2.5)
            else:
                st.markdown("""<div class="overlay-feedback bg-vermelho"><div class="status-icon">❌</div><div class="status-text">NÃO RECONHECIDO</div></div>""", unsafe_allow_html=True)
                time.sleep(2)
        else:
            st.warning("Nenhum rosto detectado.")
            time.sleep(1.5)
            
    st.session_state.cam_key += 1
    st.rerun()
