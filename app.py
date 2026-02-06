import streamlit as st
import face_recognition
import cv2
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from datetime import datetime
import pytz 

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Ponto", layout="wide", initial_sidebar_state="collapsed")

# --- CSS: O SEGREDO DO MODO RETRATO ---
st.markdown("""
    <style>
        /* 1. Limpa margens para usar a tela toda */
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        
        /* Remove cabeçalho e rodapé */
        #MainMenu, footer, header {visibility: hidden;}
        
        /* 2. FORÇA O FORMATO VERTICAL (RETRATO) */
        /* Define que o container da câmera deve ter proporção de celular (3:4 ou 9:16) */
        [data-testid="stCameraInput"] {
            width: 100% !important;
            margin: 0 auto !important;
            aspect-ratio: 3/4 !important; /* Aqui define que será mais alto que largo */
            overflow: hidden !important;
            border-radius: 0px !important;
        }

        /* 3. AJUSTA O VÍDEO DENTRO DO RETÂNGULO */
        [data-testid="stCameraInput"] video {
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important; /* ISSO É O IMPORTANTE: Corta as laterais para preencher a altura */
        }
        
        /* 4. BOTÃO MAIOR E FIXO EMBAIXO */
        button {
            width: 90% !important;
            margin-left: 5% !important;
            margin-right: 5% !important;
            height: 60px !important;
            font-size: 18px !important;
            font-weight: bold !important;
            border-radius: 30px !important;
            background-color: #FF4B4B !important;
            color: white !important;
            border: none !important;
            position: fixed !important;
            bottom: 20px !important;
            z-index: 999 !important;
        }
        
        /* Ajuste fino para não sobrepor o botão na câmera se a tela for pequena */
        div.stButton {
            position: fixed;
            bottom: 20px;
            width: 100%;
            display: flex;
            justify-content: center;
        }

    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM O BANCO ---
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# --- FUNÇÕES ---
def load_known_faces():
    try:
        response = supabase.table('alunos').select("*").execute()
        data = response.data
        known_encodings = []
        known_ids = []
        known_names = []
        
        for aluno in data:
            if 'face_encoding' in aluno and aluno['face_encoding']:
                encoding = np.array(aluno['face_encoding'])
                known_encodings.append(encoding)
                known_ids.append(aluno['id'])
                nome = aluno.get('nome', aluno.get('nome_aluno', 'Sem Nome'))
                known_names.append(nome)
        return known_encodings, known_ids, known_names
    except:
        return [], [], []

def registrar_presenca(pessoa_id, nome_identificado):
    fuso_brasil = pytz.timezone('America/Recife') 
    now = datetime.now(fuso_brasil)
    data_hora_formatada = now.strftime("%Y-%m-%d %H:%M:%S")
    inicio_dia = now.strftime("%Y-%m-%d 00:00:00")

    try:
        check = supabase.table('presenca').select("*").eq('aluno_id', pessoa_id).gte('data_hora', inicio_dia).execute()
    except:
        check = None

    if check and not check.data:
        dados = {
            "aluno_id": pessoa_id,
            "nome_aluno": nome_identificado,
            "data_hora": data_hora_formatada
        }
        supabase.table('presenca').insert(dados).execute()
        return f"✅ {nome_identificado}"
    else:
        return f"⚠️ {nome_identificado} (Já registrado)"

# --- TELA PRINCIPAL ---
if 'known_encodings' not in st.session_state:
    st.session_state.known_encodings, st.session_state.known_ids, st.session_state.known_names = load_known_faces()

# Câmera
imagem_capturada = st.camera_input("Ponto", label_visibility="hidden")

if imagem_capturada:
    if not st.session_state.known_encodings:
        st.error("Sem alunos cadastrados.")
    else:
        # Mostra spinner flutuante
        with st.spinner('Verificando...'):
            bytes_data = imagem_capturada.getvalue()
            cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
            rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_img)
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

            if not face_encodings:
                st.toast("Rosto não encontrado.", icon="❌")
            else:
                face_encoding = face_encodings[0]
                matches = face_recognition.compare_faces(st.session_state.known_encodings, face_encoding, tolerance=0.5)
                face_distances = face_recognition.face_distance(st.session_state.known_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index]:
                    nome = st.session_state.known_names[best_match_index]
                    p_id = st.session_state.known_ids[best_match_index]
                    msg = registrar_presenca(p_id, nome)
                    
                    if "✅" in msg:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.info(msg)
                else:
                    st.error("Aluno não reconhecido.")
