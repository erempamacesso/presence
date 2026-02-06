import streamlit as st
import face_recognition
import cv2
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from datetime import datetime
import pandas as pd

# --- CONFIGURAÇÃO DA PÁGINA (ISSO AUMENTA A TELA) ---
st.set_page_config(page_title="Ponto", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PARA LIMPAR A TELA (HACK VISUAL) ---
st.markdown("""
    <style>
        /* Remove o espaço em branco gigante do topo */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        /* Esconde o menu 'hamburger' e o rodapé 'Made with Streamlit' */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Tenta forçar a câmera a ocupar largura total */
        div[data-testid="stCameraInput"] {
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM O BANCO ---
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# --- FUNÇÕES (IGUAIS AO ANTERIOR) ---
def load_known_faces():
    response = supabase.table('pessoas').select("*").execute()
    data = response.data
    known_encodings = []
    known_ids = []
    known_names = []
    
    for pessoa in data:
        if pessoa['face_encoding']:
            encoding = np.array(pessoa['face_encoding'])
            known_encodings.append(encoding)
            known_ids.append(pessoa['id'])
            known_names.append(pessoa['nome'])
    return known_encodings, known_ids, known_names

def registrar_presenca(pessoa_id, nome):
    now = datetime.now()
    data_hoje = now.strftime("%Y-%m-%d")
    hora_atual = now.strftime("%H:%M:%S")
    
    # Verifica se já bateu ponto hoje
    check = supabase.table('presencas').select("*").eq('pessoa_id', pessoa_id).eq('data', data_hoje).execute()
    
    if not check.data:
        data = {"pessoa_id": pessoa_id, "data": data_hoje, "hora_entrada": hora_atual}
        supabase.table('presencas').insert(data).execute()
        return f"✅ Bom dia, {nome}! (Entrada: {hora_atual})"
    else:
        # Se quiser registrar saída, seria aqui. Por enquanto só avisa.
        return f"⚠️ {nome}, sua presença já foi registrada hoje."

# --- A INTERFACE DO USUÁRIO ---

# Carrega os dados (cache para não ficar lento)
if 'known_encodings' not in st.session_state:
    st.session_state.known_encodings, st.session_state.known_ids, st.session_state.known_names = load_known_faces()

# 1. A Câmera (Sem label para economizar espaço)
# label_visibility="hidden" esconde o texto "Take a picture"
imagem_capturada = st.camera_input("Ponto", label_visibility="hidden")

if imagem_capturada:
    # Mostra mensagem de "Processando..."
    with st.spinner('Identificando...'):
        bytes_data = imagem_capturada.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_img)
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

        if not face_encodings:
            st.error("Rosto não detectado. Tente aproximar mais ou melhorar a luz.")
        else:
            # Pega o primeiro rosto
            face_encoding = face_encodings[0]
            
            matches = face_recognition.compare_faces(st.session_state.known_encodings, face_encoding, tolerance=0.5)
            face_distances = face_recognition.face_distance(st.session_state.known_encodings, face_encoding)
            
            best_match_index = np.argmin(face_distances)
            
            if matches[best_match_index]:
                nome = st.session_state.known_names[best_match_index]
                p_id = st.session_state.known_ids[best_match_index]
                
                # Registra no banco
                msg = registrar_presenca(p_id, nome)
                
                # Mensagem grande e verde
                st.success(msg)
                st.balloons()
            else:
                st.warning("Rosto não reconhecido no sistema.")
