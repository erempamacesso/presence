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
    # AGORA BUSCA NA TABELA 'alunos'
    try:
        response = supabase.table('alunos').select("*").execute()
        data = response.data
        known_encodings = []
        known_ids = []
        known_names = []
        
        for aluno in data:
            # Verifica se tem o encoding e se não é nulo
            if 'face_encoding' in aluno and aluno['face_encoding']:
                encoding = np.array(aluno['face_encoding'])
                known_encodings.append(encoding)
                known_ids.append(aluno['id'])
                # Verifica se a coluna é 'nome' ou 'nome_aluno' na tabela de cadastro
                # Tenta 'nome' primeiro, se não tiver, tenta 'nome_aluno'
                nome = aluno.get('nome', aluno.get('nome_aluno', 'Sem Nome'))
                known_names.append(nome)
                
        return known_encodings, known_ids, known_names
    except Exception as e:
        st.error(f"Erro ao carregar alunos: {e}")
        return [], [], []

def registrar_presenca(pessoa_id, nome_identificado):
    # 1. Define o fuso horário (Recife/PE)
    fuso_brasil = pytz.timezone('America/Recife') 
    now = datetime.now(fuso_brasil)
    
    # Formata para salvar no banco (Ex: 2026-02-06 13:45:00)
    data_hora_formatada = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Define o início do dia para evitar duplicidade
    inicio_dia = now.strftime("%Y-%m-%d 00:00:00")

    # 2. Verifica se já bateu ponto HOJE na tabela 'presenca'
    try:
        check = supabase.table('presenca') \
            .select("*") \
            .eq('aluno_id', pessoa_id) \
            .gte('data_hora', inicio_dia) \
            .execute()
    except Exception as e:
        return f"Erro ao verificar presença: {e}"

    if check and not check.data:
        # Prepara os dados EXATAMENTE como sua tabela 'presenca' pede
        dados_para_salvar = {
            "aluno_id": pessoa_id,
            "nome_aluno": nome_identificado,
            "data_hora": data_hora_formatada
        }
        
        # Salva na tabela
        supabase.table('presenca').insert(dados_para_salvar).execute()
        
        return f"✅ Presença Registrada: {nome_identificado}"
    else:
        return f"⚠️ {nome_identificado}, já registrado hoje!"

# --- TELA PRINCIPAL ---

# Carrega rostos (Cache para não ficar lento)
if 'known_encodings' not in st.session_state:
    st.session_state.known_encodings, st.session_state.known_ids, st.session_state.known_names = load_known_faces()

imagem_capturada = st.camera_input("Ponto", label_visibility="hidden")

if imagem_capturada:
    if not st.session_state.known_encodings:
        st.error("Nenhum aluno cadastrado no banco de dados!")
    else:
        with st.spinner('Identificando...'):
            bytes_data = imagem_capturada.getvalue()
            cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
            rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_img)
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

            if not face_encodings:
                st.warning("Rosto não encontrado. Tente melhorar a luz.")
            else:
                face_encoding = face_encodings[0]
                matches = face_recognition.compare_faces(st.session_state.known_encodings, face_encoding, tolerance=0.5)
                face_distances = face_recognition.face_distance(st.session_state.known_encodings, face_encoding)
                
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index]:
                    nome_encontrado = st.session_state.known_names[best_match_index]
                    id_encontrado = st.session_state.known_ids[best_match_index]
                    
                    msg = registrar_presenca(id_encontrado, nome_encontrado)
                    
                    if "✅" in msg:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.info(msg)
                else:
                    st.error("Aluno não reconhecido.")
