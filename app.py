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

# --- CSS ESTILO "TOTEM DE ACADEMIA" ---
st.markdown("""
    <style>
        /* 1. Remove todo o espaçamento padrão do Streamlit */
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        
        /* Remove barras superiores e rodapés */
        header, footer, #MainMenu {display: none !important;}
        
        /* 2. CONFIGURAÇÃO DA CÂMERA (O PULO DO GATO) */
        
        /* Força o container da câmera a ter 70% da altura da tela */
        div[data-testid="stCameraInput"] {
            width: 100% !important;
        }

        /* Acessa a div interna que segura o vídeo e estica ela */
        div[data-testid="stCameraInput"] > div {
            height: 70vh !important; /* 70% da Altura da Tela */
            background-color: black; /* Fundo preto se sobrar espaço */
            border-bottom-left-radius: 20px;
            border-bottom-right-radius: 20px;
            overflow: hidden; /* Corta o excesso */
        }
        
        /* Força o vídeo a dar ZOOM para preencher tudo (Object-fit Cover) */
        div[data-testid="stCameraInput"] video {
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important; /* Esse comando faz ocupar a área toda */
        }

        /* 3. BOTÃO DE TIRAR FOTO */
        button {
            margin-top: 20px !important;
            width: 90% !important; /* Quase a largura toda */
            margin-left: 5% !important; 
            height: 70px !important; /* Botão bem alto */
            border-radius: 35px !important; /* Redondinho */
            background-color: #FF4B4B !important;
            color: white !important;
            font-size: 24px !important; /* Letra grande */
            font-weight: bold !important;
            border: none !important;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.2) !important;
        }
        
        /* Centraliza o botão se ele tentar fugir */
        div.stButton {
            text-align: center;
            background-color: white;
            padding-bottom: 20px;
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
        return f"✅ ACESSO LIBERADO: {nome_identificado}"
    else:
        return f"⚠️ {nome_identificado} JÁ REGISTRADO!"

# --- TELA PRINCIPAL ---
if 'known_encodings' not in st.session_state:
    st.session_state.known_encodings, st.session_state.known_ids, st.session_state.known_names = load_known_faces()

# O Widget da câmera
imagem_capturada = st.camera_input("Ponto", label_visibility="hidden")

# Lógica de processamento
if imagem_capturada:
    if not st.session_state.known_encodings:
        st.error("ERRO: Sem base de dados.")
    else:
        # Usa st.status para feedback visual moderno
        with st.status("Processando...", expanded=True) as status:
            bytes_data = imagem_capturada.getvalue()
            cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
            rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_img)
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

            if not face_encodings:
                status.update(label="Rosto não encontrado!", state="error", expanded=False)
                st.warning("Posicione o rosto no centro.")
            else:
                face_encoding = face_encodings[0]
                matches = face_recognition.compare_faces(st.session_state.known_encodings, face_encoding, tolerance=0.5)
                face_distances = face_recognition.face_distance(st.session_state.known_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index]:
                    nome = st.session_state.known_names[best_match_index]
                    p_id = st.session_state.known_ids[best_match_index]
                    
                    msg = registrar_presenca(p_id, nome)
                    
                    status.update(label="Identificado!", state="complete", expanded=False)
                    
                    if "✅" in msg:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.info(msg)
                else:
                    status.update(label="Não reconhecido", state="error", expanded=False)
                    st.error("Aluno não encontrado no sistema.")
