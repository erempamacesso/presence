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
# CSS OTIMIZADO E RESPONSIVO (CORRIGIDO)
# --------------------------------------------------
st.markdown("""
<style>
    /* RESET BÁSICO */
    html, body, .stApp {
        background-color: #111;
        margin: 0;
        font-family: sans-serif;
    }

    /* REMOVE O PADDING PADRÃO DO STREAMLIT QUE EMPURRA TUDO PRA BAIXO */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important;
    }
    
    header, footer, #MainMenu { display: none !important; }

    /* CENTRALIZA O CONTEÚDO VERTICALMENTE */
    div[data-testid="stVerticalBlock"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 80vh; /* Garante que fique centralizado na tela */
        gap: 20px;
    }

    /* ESTILO DO CONTAINER DA CÂMERA */
    div[data-testid="stCameraInput"] {
        width: 100% !important;
        height: auto !important; /* IMPORTANTE: Deixa a altura automática */
        position: relative !important;
        margin: 0 auto;
    }

    /* ESTILO DO VÍDEO (ARREDONDADO E SEM BORDAS BRANCAS) */
    div[data-testid="stCameraInput"] video {
        border-radius: 20px !important; /* Borda arredondada moderna */
        max-height: 70vh !important; /* Não deixa o vídeo ficar maior que a tela */
        width: 100% !important;
        object-fit: cover !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }

    /* BOTÃO DE AÇÃO (Centralizado SOBRE a parte inferior do vídeo) */
    div[data-testid="stCameraInput"] button {
        width: 80% !important;
        max-width: 300px !important;
        height: 60px !important;
        border-radius: 30px !important;
        background-color: #D32F2F !important;
        border: 2px solid rgba(255,255,255,0.3) !important;
        
        /* Posicionamento absoluto DENTRO do container da câmera */
        position: absolute !important;
        bottom: 20px !important; /* 20px da borda de baixo do vídeo */
        left: 50% !important;
        transform: translateX(-50%) !important;
        
        z-index: 100 !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.4) !important;
        color: transparent !important; /* Esconde o texto original "Take Photo" */
        transition: transform 0.2s, background-color 0.2s;
    }
    
    div[data-testid="stCameraInput"] button:active {
        transform: translateX(-50%) scale(0.95) !important;
        background-color: #B71C1C !important;
    }

    /* TEXTO NOVO DO BOTÃO */
    div[data-testid="stCameraInput"] button::after {
        content: "REGISTRAR PRESENÇA";
        color: white;
        font-size: 16px;
        font-weight: 700;
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* --- FEEDBACK (MANTIVE IGUAL, POIS ESTAVA BOM) --- */
    .hud-badge {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 85%;
        max-width: 400px;
        padding: 25px;
        border-radius: 20px;
        color: white;
        text-align: center;
        z-index: 99999;
        box-shadow: 0 20px 50px rgba(0,0,0,0.9);
        border: 1px solid rgba(255,255,255,0.2);
        backdrop-filter: blur(12px);
        animation: popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    .status-ok { background: rgba(39, 174, 96, 0.95); }
    .status-warn { background: rgba(243, 156, 18, 0.95); }
    .status-err { background: rgba(192, 57, 43, 0.95); }

    .hud-icon { font-size: 50px; display: block; margin-bottom: 10px; }
    .hud-title { font-size: 24px; font-weight: 800; display: block; margin-bottom: 5px; text-transform: uppercase;}
    .hud-sub { font-size: 18px; font-weight: 400; opacity: 0.95; }

    @keyframes popIn {
        0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
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

