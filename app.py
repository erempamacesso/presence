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

# --- CSS PARA LIMPAR A TELA (MOBILE FIRST) ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
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

# --- FUNÇÕES ---
def load_known_faces():
    # Cuidado: Aqui busca da tabela de cadastros (presumo que seja 'pessoas' ou 'alunos')
    # Se sua tabela de rostos tiver outro nome, mude aqui embaixo.
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

def registrar_presenca(pessoa_id, nome_identificado):
    # 1. Define o fuso horário (Recife)
    fuso_brasil = pytz.timezone('America/Recife') 
    now = datetime.now(fuso_brasil)
    
    # Formata a data e hora completa (Ex: 2026-02-06 13:45:00)
    data_hora_formatada = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Define o início do dia para evitar duplicidade
    inicio_dia = now.strftime("%Y-%m-%d 00:00:00")

    # 2. Verifica se já bateu ponto HOJE
    # Procura na tabela 'presenca' se existe registro deste aluno com data maior que o início do dia
    try:
        check = supabase.table('presenca') \
            .select("*") \
            .eq('aluno_id', pessoa_id) \
            .gte('data_hora', inicio_dia) \
            .execute()
    except:
        check = None # Se der erro na verificação, segue o jogo

    if check and not check.data:
        # Prepara os dados EXATAMENTE como sua tabela pede
        dados_para_salvar = {
            "aluno_id": pessoa_id,
            "nome_aluno": nome_identificado,
            "data_hora": data_hora_formatada
        }
        
        # Salva na tabela 'presenca'
        supabase.table('presenca').insert(dados_para_salvar).execute()
        
        return f"✅ Presença Registrada: {nome_identificado}"
    else:
        return f"⚠️ {nome_identificado}, você já registrou presença hoje!"

# --- TELA PRINCIPAL ---

# Carrega rostos (Cache)
if 'known_encodings' not in st.session_state:
    st.session_state.known_encodings, st.session_state.known_ids, st.session_state.known_names = load_known_faces()

imagem_capturada = st.camera_input("Ponto", label_visibility="hidden")

if imagem_capturada:
    with st.spinner('Identificando...'):
        bytes_data = imagem_capturada.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_img)
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

        if not face_encodings:
            st.error("Rosto não encontrado. Tente novamente.")
        else:
            face_encoding = face_encodings[0]
            matches = face_recognition.compare_faces(st.session_state.known_encodings, face_encoding, tolerance=0.5)
            face_distances = face_recognition.face_distance(st.session_state.known_encodings, face_encoding)
            
            best_match_index = np.argmin(face_distances)
            
            if matches[best_match_index]:
                nome_encontrado = st.session_state.known_names[best_match_index]
                id_encontrado = st.session_state.known_ids[best_match_index]
                
                # Chama a função nova
                msg = registrar_presenca(id_encontrado, nome_encontrado)
                
                st.success(msg)
                if "Registrada" in msg:
                    st.balloons()
            else:
                st.warning("Aluno não reconhecido.")
