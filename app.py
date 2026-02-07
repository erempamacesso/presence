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
# CSS OTIMIZADO (ESTILO HUD / BADGE)
# --------------------------------------------------
st.markdown("""
<style>
    /* RESET E FUNDO */
    html, body, .stApp {
        background-color: #111; /* Cinza muito escuro é melhor que preto absoluto para contraste */
        margin: 0;
        overflow: hidden;
    }

    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    
    header, footer, #MainMenu { display: none !important; }

    /* CÂMERA FULL HEIGHT */
    div[data-testid="stCameraInput"] {
        width: 100vw !important;
        height: 100vh !important; /* Ocupa tudo */
        display: flex;
        align-items: center;
        justify-content: center;
        background: #000;
    }

    div[data-testid="stCameraInput"] > div {
        height: 100% !important;
        width: 100% !important;
        border-radius: 0 !important;
    }

    div[data-testid="stCameraInput"] video, 
    div[data-testid="stCameraInput"] img {
        object-fit: cover !important; /* Garante preenchimento sem bordas */
    }

    /* BOTÃO DE AÇÃO (Floating Action Button style) */
    div[data-testid="stCameraInput"] button {
        width: 70% !important;
        max-width: 400px !important;
        height: 65px !important;
        border-radius: 35px !important;
        background-color: #D32F2F !important;
        border: 2px solid rgba(255,255,255,0.8) !important;
        position: absolute !important;
        bottom: 50px !important; /* Fixo embaixo */
        left: 50% !important;
        transform: translateX(-50%) !important;
        z-index: 100 !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important;
        color: transparent !important;
        transition: transform 0.2s;
    }
    
    div[data-testid="stCameraInput"] button:active {
        transform: translateX(-50%) scale(0.95) !important;
    }

    div[data-testid="stCameraInput"] button::after {
        content: "REGISTRAR PRESENÇA";
        color: white;
        font-size: 20px;
        font-weight: 700;
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* --- O NOVO FEEDBACK (CARD FLUTUANTE) --- */
    .hud-badge {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 85%;
        max-width: 500px;
        padding: 30px 20px;
        border-radius: 25px;
        color: white;
        text-align: center;
        z-index: 99999;
        box-shadow: 0 20px 50px rgba(0,0,0,0.8);
        border: 4px solid rgba(255,255,255,0.2);
        backdrop-filter: blur(10px); /* Efeito de vidro */
        animation: popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    /* CORES DOS ESTADOS */
    .status-ok { background: rgba(46, 204, 113, 0.9); } /* Verde */
    .status-warn { background: rgba(241, 196, 15, 0.95); color: #222; } /* Amarelo */
    .status-err { background: rgba(231, 76, 60, 0.9); } /* Vermelho */

    .hud-icon { font-size: 60px; display: block; margin-bottom: 10px; }
    .hud-title { font-size: 28px; font-weight: 900; display: block; margin-bottom: 5px; text-transform: uppercase;}
    .hud-sub { font-size: 20px; font-weight: 400; opacity: 0.9; }

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
                    mensagem_titulo = "ACESSO JÁ REGISTRADO" # <--- O QUE VC PEDIU
                    mensagem_sub = f"{p_nome}, você já marcou hoje."
                    cor_classe = "status-warn" # Amarelo
            else:
                mensagem_sub = "Cadastro não encontrado."
    else:
        mensagem_titulo = "ROSTO NÃO DETECTADO"
        mensagem_sub = "Centralize seu rosto na câmera"

    # 2. Exibe o Feedback (Badge Flutuante)
    # Note que usamos o placeholder criado ANTES do camera_input, mas o CSS position fixed joga ele por cima
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
