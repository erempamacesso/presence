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

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Ponto", layout="wide", initial_sidebar_state="collapsed")

# --- CSS ESTILO "TOTEM DE ACADEMIA" (Tela Cheia Vertical) ---
st.markdown("""
    <style>
        /* 1. Limpa margens */
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        
        header, footer, #MainMenu {display: none !important;}
        
        /* 2. CÂMERA GRANDE (70% da tela) */
        div[data-testid="stCameraInput"] {
            width: 100% !important;
        }

        div[data-testid="stCameraInput"] > div {
            height: 70vh !important; /* Altura do container */
            background-color: black;
            border-bottom-left-radius: 20px;
            border-bottom-right-radius: 20px;
            overflow: hidden;
        }
        
        div[data-testid="stCameraInput"] video {
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important; /* Zoom para preencher */
        }

        /* 3. BOTÃO GRANDE */
        button {
            margin-top: 20px !important;
            width: 90% !important;
            margin-left: 5% !important; 
            height: 70px !important;
            border-radius: 35px !important;
            background-color: #FF4B4B !important;
            color: white !important;
            font-size: 24px !important;
            font-weight: bold !important;
            border: none !important;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.2) !important;
        }
        
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
            # Verifica se existe o campo e se não é nulo
            if 'face_encoding' in aluno and aluno['face_encoding']:
                try:
                    raw_encoding = aluno['face_encoding']
                    
                    # Se vier como string (JSON), converte para lista primeiro
                    if isinstance(raw_encoding, str):
                        raw_encoding = json.loads(raw_encoding)
                    
                    # --- A CORREÇÃO MÁGICA ESTÁ AQUI ---
                    # Força ser um array de float64. Isso resolve o erro UFuncNoLoopError
                    encoding = np.array(raw_encoding, dtype=np.float64)
                    
                    known_encodings.append(encoding)
                    known_ids.append(aluno['id'])
                    nome = aluno.get('nome', aluno.get('nome_aluno', 'Sem Nome'))
                    known_names.append(nome)
                except Exception as e:
                    print(f"Erro ao processar rosto do aluno {aluno.get('id')}: {e}")
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
        return f"✅ ACESSO LIBERADO: {nome_identificado}"
    else:
        return f"⚠️ {nome_identificado} JÁ REGISTRADO!"

# --- TELA PRINCIPAL ---
if 'known_encodings' not in st.session_state:
    st.session_state.known_encodings, st.session_state.known_ids, st.session_state.known_names = load_known_faces()

imagem_capturada = st.camera_input("Ponto", label_visibility="hidden")

if imagem_capturada:
    if not st.session_state.known_encodings:
        st.error("ERRO: Nenhum aluno carregado do banco.")
    else:
        with st.status("Identificando...", expanded=True) as status:
            try:
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
                    
                    # A comparação agora deve funcionar pois forçamos float64
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
                        st.error("Aluno não cadastrado.")
            except Exception as e:
                st.error(f"Erro técnico: {e}")
