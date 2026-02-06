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
# CONFIGURAÇÃO DA PÁGINA (MODO KIOSK)
# --------------------------------------------------
st.set_page_config(
    page_title="Registro de Presença",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --------------------------------------------------
# CSS – VISUAL LIMPO E FUNCIONAL
# --------------------------------------------------
st.markdown("""
<style>

/* 1. LIMPEZA TOTAL DA TELA */
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

/* 2. AREA DA CÂMERA */
div[data-testid="stCameraInput"] {
    width: 100% !important;
    display: flex;
    justify-content: center;
    background-color: black; /* Fundo preto pra ficar bonito */
}

div[data-testid="stCameraInput"] > div {
    height: 85vh !important; /* Altura bem grande */
    width: 100% !important;
    border-radius: 0px !important;
    background: transparent !important;
    box-shadow: none !important;
}

div[data-testid="stCameraInput"] video {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important; /* Ocupa a tela toda sem bordas pretas */
}

/* 3. BOTÃO FLUTUANTE */
div[data-testid="stCameraInput"] button {
    width: 60% !important; /* Tamanho controlado */
    height: 60px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    display: block !important;
    
    /* POSICIONAMENTO FIXO NA PARTE INFERIOR */
    margin-top: -90px !important; /* Puxa pra cima do vídeo */
    position: relative;
    z-index: 999;
    
    background: #D32F2F !important; /* Vermelho forte */
    border-radius: 30px !important;
    border: 3px solid white !important; /* Borda branca pra destacar */
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
    text-transform: uppercase;
}

/* 4. MENSAGENS DE STATUS (TELA CHEIA) */
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

.bg-verde { background-color: #2ecc71; } /* Sucesso */
.bg-amarelo { background-color: #f1c40f; color: #333; } /* Já registrado */
.bg-vermelho { background-color: #e74c3c; } /* Erro */

.status-icon { font-size: 80px; margin-bottom: 20px; }
.status-text { font-size: 32px; font-weight: bold; text-align: center; }

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# BANCO DE DADOS
# --------------------------------------------------
load_dotenv()
try:
    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
except:
    st.error("Erro ao conectar no Supabase. Verifique as chaves.")

# --------------------------------------------------
# FUNÇÕES
# --------------------------------------------------
def carregar_faces():
    try:
        dados = supabase.table("alunos").select("*").execute().data
        encs, ids, nomes = [], [], []
        for a in dados:
            if a.get("face_encoding"):
                try:
                    raw = a["face_encoding"]
                    if isinstance(raw, str):
                        raw = json.loads(raw)
                    # Força float64 para evitar erro do Numpy
                    encs.append(np.array(raw, dtype=np.float64))
                    ids.append(a["id"])
                    nomes.append(a.get("nome", "Aluno"))
                except:
                    pass
        return encs, ids, nomes
    except:
        return [], [], []

def registrar(aluno_id, nome):
    tz = pytz.timezone("America/Recife")
    agora = datetime.now(tz)
    inicio = agora.strftime("%Y-%m-%d 00:00:00")

    try:
        # Verifica se já bateu ponto HOJE
        check = supabase.table("presenca") \
            .select("*") \
            .eq("aluno_id", aluno_id) \
            .gte("data_hora", inicio) \
            .execute()

        if not check.data:
            # SE NÃO TEM REGISTRO HOJE, INSERE
            supabase.table("presenca").insert({
                "aluno_id": aluno_id,
                "nome_aluno": nome,
                "data_hora": agora.strftime("%Y-%m-%d %H:%M:%S")
            }).execute()
            return "NOVO" # Novo registro
        else:
            return "DUPLICADO" # Já estava lá
    except:
        return "ERRO"

# --------------------------------------------------
# ESTADO E INICIALIZAÇÃO
# --------------------------------------------------
if "faces" not in st.session_state:
    with st.spinner("Carregando sistema..."):
        st.session_state.faces, st.session_state.ids, st.session_state.nomes = carregar_faces()

# Controle de chave da câmera para resetar
if "cam_key" not in st.session_state:
    st.session_state.cam_key = 0

# --------------------------------------------------
# UI PRINCIPAL
# --------------------------------------------------
# Câmera com chave dinâmica
img = st.camera_input("Ponto", label_visibility="hidden", key=f"cam_{st.session_state.cam_key}")

# --------------------------------------------------
# PROCESSAMENTO
# --------------------------------------------------
if img:
    if not st.session_state.faces:
        st.error("Nenhum aluno cadastrado no sistema.")
    else:
        # Decodifica imagem
        bytes_data = img.getvalue()
        frame = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Procura rostos
        face_locations = face_recognition.face_locations(rgb)
        face_encodings = face_recognition.face_encodings(rgb, face_locations)

        if face_encodings:
            enc = face_encodings[0]
            matches = face_recognition.compare_faces(st.session_state.faces, enc, tolerance=0.5)
            
            if True in matches:
                # ACHOU ALGUÉM CONHECIDO
                first_match_index = matches.index(True)
                p_id = st.session_state.ids[first_match_index]
                p_nome = st.session_state.nomes[first_match_index]

                # Tenta registrar no banco
                resultado = registrar(p_id, p_nome)

                if resultado == "NOVO":
                    # TELA VERDE (Sucesso)
                    st.markdown(f"""
                    <div class="overlay-feedback bg-verde">
                        <div class="status-icon">✅</div>
                        <div class="status-text">PRESENÇA REGISTRADA<br>{p_nome}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
                    time.sleep(2.5) # Tempo para ler
                    
                elif resultado == "DUPLICADO":
                    # TELA AMARELA (Aviso)
                    st.markdown(f"""
                    <div class="overlay-feedback bg-amarelo">
                        <div class="status-icon">⚠️</div>
                        <div class="status-text">JÁ REGISTRADO HOJE<br>{p_nome}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    time.sleep(2.5)
                
                else:
                    st.error("Erro de conexão com banco.")
                    time.sleep(2)

            else:
                # ROSTO DESCONHECIDO
                st.markdown("""
                <div class="overlay-feedback bg-vermelho">
                    <div class="status-icon">❌</div>
                    <div class="status-text">NÃO RECONHECIDO<br>Tente Novamente</div>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(2)
        else:
            # NÃO ACHOU NENHUM ROSTO NA FOTO
            st.warning("Nenhum rosto detectado. Centralize melhor.")
            time.sleep(1.5)

    # RESET DA CÂMERA (Novo aluno)
    st.session_state.cam_key += 1
    st.rerun()
