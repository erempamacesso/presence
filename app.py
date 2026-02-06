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

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Ponto", layout="wide", initial_sidebar_state="collapsed")

# --- CSS AVANÇADO (BOTÃO PERSONALIZADO) ---
st.markdown("""
    <style>
        /* 1. Limpeza Geral */
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        header, footer, #MainMenu {display: none !important;}
        
        /* 2. CÂMERA GRANDE (70% da tela) */
        div[data-testid="stCameraInput"] {
            width: 100% !important;
            position: relative; /* Necessário para o botão flutuar */
        }

       div[data-testid="stCameraInput"] > div {
    background-color: black;
    border-bottom-left-radius: 20px;
    border-bottom-right-radius: 20px;
    overflow: hidden;
        }
        
        div[data-testid="stCameraInput"] video {
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important;
        }

       
        div[data-testid="stCameraInput"] button {
    width: 50% !important;
    margin: 16px auto 20px auto !important;
    display: block !important;
    height: 50px !important;

    position: relative !important;
    z-index: 10 !important;

    border-radius: 25px !important;
    background-color: #FF4B4B !important;
    border: 2px solid white !important;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.4) !important;

    color: transparent !important;
}

        /* ESCREVE O NOVO TEXTO POR CIMA */
        div[data-testid="stCameraInput"] button::after {
            content: "REGISTRAR PRESENÇA";
            color: white !important;
            font-size: 14px !important;
            font-weight: bold !important;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 100%;
        }
        
        /* Centraliza status e mensagens */
        .stStatus {
            margin-top: 10px;
            padding: 10px;
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
                try:
                    raw_encoding = aluno['face_encoding']
                    if isinstance(raw_encoding, str):
                        raw_encoding = json.loads(raw_encoding)
                    
                    encoding = np.array(raw_encoding, dtype=np.float64)
                    known_encodings.append(encoding)
                    known_ids.append(aluno['id'])
                    nome = aluno.get('nome', aluno.get('nome_aluno', 'Sem Nome'))
                    known_names.append(nome)
                except Exception as e:
                    print(f"Erro ao processar rosto: {e}")
                    continue
        return known_encodings, known_ids, known_names
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
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
        return f"✅ PRESENÇA REGISTRADA: {nome_identificado}", True 
    else:
        return f"⚠️ {nome_identificado} JÁ REGISTRADO!", False

# --- TELA PRINCIPAL ---
if 'known_encodings' not in st.session_state:
    st.session_state.known_encodings, st.session_state.known_ids, st.session_state.known_names = load_known_faces()

if 'camera_key' not in st.session_state:
    st.session_state.camera_key = 0

# O label aqui fica hidden, quem manda é o CSS lá em cima
imagem_capturada = st.camera_input("Ponto", label_visibility="hidden", key=f"camera_{st.session_state.camera_key}")

if imagem_capturada:
    if not st.session_state.known_encodings:
        st.error("ERRO: Nenhum aluno carregado.")
    else:
        with st.status("Verificando...", expanded=True) as status:
            try:
                bytes_data = imagem_capturada.getvalue()
                cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
                
                face_locations = face_recognition.face_locations(rgb_img)
                face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

                if not face_encodings:
                    status.update(label="Rosto não encontrado!", state="error", expanded=False)
                    st.warning("Aproxime o rosto.")
                    time.sleep(2)
                    st.session_state.camera_key += 1
                    st.rerun()
                else:
                    face_encoding = face_encodings[0]
                    matches = face_recognition.compare_faces(st.session_state.known_encodings, face_encoding, tolerance=0.5)
                    face_distances = face_recognition.face_distance(st.session_state.known_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    
                    if matches[best_match_index]:
                        nome = st.session_state.known_names[best_match_index]
                        p_id = st.session_state.known_ids[best_match_index]
                        
                        msg, sucesso = registrar_presenca(p_id, nome)
                        
                        status.update(label="Concluído!", state="complete", expanded=False)
                        
                        if "✅" in msg:
                            st.success(msg)
                            st.balloons()
                            st.info("Reiniciando...")
                            time.sleep(2) 
                            st.session_state.camera_key += 1 
                            st.rerun() 
                        else:
                            st.info(msg)
                            time.sleep(2)
                            st.session_state.camera_key += 1
                            st.rerun()
                    else:
                        status.update(label="Não reconhecido", state="error", expanded=False)
                        st.error("Aluno não cadastrado.")
                        time.sleep(2)
                        st.session_state.camera_key += 1
                        st.rerun()
            except Exception as e:
                st.error(f"Erro técnico: {e}")

