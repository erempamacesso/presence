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
# CONFIGURAÇÃO DA PÁGINA
# --------------------------------------------------
st.set_page_config(
    page_title="Ponto Facial",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --------------------------------------------------
# CSS NOVO (BOTÃO EMBAIXO DA CÂMERA - SEM QUEBRAR)
# --------------------------------------------------
st.markdown("""
<style>
    /* 1. FUNDO E RESET GERAL */
    html, body, .stApp {
        background-color: #111;
        margin: 0;
        font-family: sans-serif;
    }

    /* 2. CENTRALIZAR TUDO NA TELA */
    .block-container {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 100vh !important; /* Centraliza verticalmente */
        padding: 20px !important;
        max-width: 100% !important;
    }
    
    header, footer, #MainMenu { display: none !important; }

    /* 3. CONTAINER DA CÂMERA (SEM ALTURA FIXA) */
    div[data-testid="stCameraInput"] {
        width: 100% !important;
        max-width: 450px !important; /* Limite para tablet/pc */
        position: relative !important;
        margin-bottom: 20px !important; /* Espaço extra embaixo */
    }

    /* 4. VÍDEO ARREDONDADO */
    div[data-testid="stCameraInput"] video {
        border-radius: 15px !important;
        border: 2px solid #333 !important;
        width: 100% !important;
        object-fit: cover !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }

    /* 5. BOTÃO (LOGO ABAIXO DO VÍDEO) */
    div[data-testid="stCameraInput"] button {
        width: 100% !important;
        height: 60px !important;
        border-radius: 12px !important;
        background-color: #D32F2F !important;
        border: none !important;
        margin-top: 15px !important; /* Empurra para baixo do vídeo */
        color: transparent !important;
        position: relative !important;
        transition: transform 0.2s;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
    
    div[data-testid="stCameraInput"] button:active {
        transform: scale(0.98) !important;
        background-color: #B71C1C !important;
    }

    /* TEXTO DO BOTÃO */
    div[data-testid="stCameraInput"] button::after {
        content: "REGISTRAR PRESENÇA";
        color: white;
        font-size: 18px;
        font-weight: 700;
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* --- POPUP DE FEEDBACK (MANTIDO) --- */
    .hud-badge {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 85%;
        max-width: 400px;
        padding: 30px 20px;
        border-radius: 20px;
        color: white;
        text-align: center;
        z-index: 99999;
        box-shadow: 0 20px 50px rgba(0,0,0,0.8);
        border: 2px solid rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        background: rgba(20,20,20, 0.95);
        animation: popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    .status-ok { border-top: 5px solid #2ecc71; }
    .status-warn { border-top: 5px solid #f1c40f; }
    .status-err { border-top: 5px solid #e74c3c; }

    .hud-icon { font-size: 50px; display: block; margin-bottom: 15px; }
    .hud-title { font-size: 24px; font-weight: 800; display: block; margin-bottom: 5px; text-transform: uppercase;}
    .hud-sub { font-size: 18px; font-weight: 400; opacity: 0.8; }

    @keyframes popIn {
        0% { opacity: 0; transform: translate(-50%, -50%) scale(0.5); }
        100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# BANCO E CONFIG
# --------------------------------------------------
load_dotenv()
try:
    supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
except:
    st.error("Erro de conexão com Banco de Dados")

# --------------------------------------------------
# LOGICA
# --------------------------------------------------
def carregar_faces():
    try:
        dados = supabase.table("alunos").select("*").execute().data
        encs, ids, nomes = [], [], []
        for a in dados:
            if a.get("face_encoding"):
                try:
                    raw = json.loads(a["face_encoding"]) if isinstance(a["face_encoding"], str) else a["face_encoding"]
                    encs.append(np.array(raw, dtype=np.float64))
                    ids.append(a["id"])
                    nomes.append(a.get("nome", "Aluno"))
                except: pass
        return encs, ids, nomes
    except: return [], [], []

def registrar_ponto(aluno_id, nome):
    tz = pytz.timezone("America/Recife")
    agora = datetime.now(tz)
    inicio_dia = agora.strftime("%Y-%m-%d 00:00:00")

    try:
        # Verifica se já bateu hoje
        check = supabase.table("presenca").select("id").eq("aluno_id", aluno_id).gte("data_hora", inicio_dia).execute()
        
        if check.data:
            return "DUPLICADO" # <--- JÁ REGISTRADO HOJE
        
        # Se não, registra
        supabase.table("presenca").insert({
            "aluno_id": aluno_id,
            "nome_aluno": nome,
            "data_hora": agora.strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        return "SUCESSO"
    except:
        return "ERRO"

# --------------------------------------------------
# ESTADO
# --------------------------------------------------
if "faces" not in st.session_state:
    st.session_state.faces, st.session_state.ids, st.session_state.nomes = carregar_faces()

if "cam_key" not in st.session_state:
    st.session_state.cam_key = 0

# --------------------------------------------------
# INTERFACE PRINCIPAL
# --------------------------------------------------

# O container vazio é onde injetaremos o feedback DEPOIS da foto
feedback_placeholder = st.empty()

# Câmera
img = st.camera_input("Ponto", label_visibility="hidden", key=f"cam_{st.session_state.cam_key}")

# --------------------------------------------------
# PROCESSAMENTO PÓS-CLICK
# --------------------------------------------------
if img:
    # 1. Processa Imagem
    bytes_data = img.getvalue()
    frame = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    face_locations = face_recognition.face_locations(rgb)
    
    # Lógica de decisão
    status_tipo = "erro"
    mensagem_titulo = "NÃO RECONHECIDO"
    mensagem_sub = "Tente aproximar o rosto"
    cor_classe = "status-err" # Vermelho padrão

    if face_locations:
        face_encodings = face_recognition.face_encodings(rgb, face_locations)
        if face_encodings:
            match_results = face_recognition.compare_faces(st.session_state.faces, face_encodings[0], tolerance=0.5)
            
            if True in match_results:
                idx = match_results.index(True)
                p_id = st.session_state.ids[idx]
                p_nome = st.session_state.nomes[idx]
                
                # TENTA REGISTRAR
                resultado = registrar_ponto(p_id, p_nome)
                
                if resultado == "SUCESSO":
                    status_tipo = "sucesso"
                    mensagem_titulo = "ACESSO LIBERADO"
                    mensagem_sub = p_nome
                    cor_classe = "status-ok" # Verde
                    st.balloons()
                    
                elif resultado == "DUPLICADO":
                    status_tipo = "aviso"
                    mensagem_titulo = "JÁ REGISTRADO"
                    mensagem_sub = f"{p_nome}, você já marcou hoje."
                    cor_classe = "status-warn" # Amarelo
            else:
                mensagem_sub = "Cadastro não encontrado."
    else:
        mensagem_titulo = "ROSTO NÃO DETECTADO"
        mensagem_sub = "Centralize seu rosto na câmera"

    # 2. Exibe o Feedback (Badge Flutuante)
    feedback_placeholder.markdown(f"""
    <div class="hud-badge {cor_classe}">
        <div class="hud-icon">
            {'✅' if status_tipo == 'sucesso' else '⚠️' if status_tipo == 'aviso' else '❌'}
        </div>
        <div class="hud-title">{mensagem_titulo}</div>
        <div class="hud-sub">{mensagem_sub}</div>
    </div>
    """, unsafe_allow_html=True)

    # 3. Pausa para leitura e Reset
    time.sleep(2.5) # Tempo suficiente para ler
    st.session_state.cam_key += 1
    st.rerun()
