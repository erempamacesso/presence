import streamlit as st
import face_recognition
import cv2
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import json

# 1. Configuração da Página
st.set_page_config(page_title="Argos Chamada", page_icon="📸")

st.title("📸 Argos - Chamada Inteligente")
st.write("Olhe para a câmera para registrar presença.")

# 2. Conectar ao Banco (Cacheado para não reconectar toda hora)
@st.cache_resource
def init_connection():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_connection()

# 3. Buscar Alunos no Banco (Cacheado para ficar rápido)
@st.cache_data
def carregar_alunos():
    response = supabase.table("alunos").select("*").execute()
    alunos_db = []
    
    for row in response.data:
        try:
            # Converte a string JSON de volta para lista de números
            encoding = json.loads(row['face_encoding'])
            alunos_db.append({
                "nome": row['nome'],
                "turma": row['turma'],
                "encoding": np.array(encoding) # Importante virar numpy array
            })
        except:
            pass
    return alunos_db

alunos = carregar_alunos()
st.success(f"Banco de dados carregado: {len(alunos)} alunos ativos.")

# 4. Interface da Câmera
img_file_buffer = st.camera_input("Tire uma foto para registrar")

if img_file_buffer is not None:
    # Ler a imagem da câmera
    bytes_data = img_file_buffer.getvalue()
    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    
    # Converter para RGB (Streamlit/OpenCV usam padrões diferentes)
    rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
    
    # Detectar rostos na foto tirada
    face_locations = face_recognition.face_locations(rgb_img)
    face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

    if not face_encodings:
        st.warning("⚠️ Nenhum rosto detectado. Tente novamente.")
    else:
        # Para cada rosto encontrado na câmera
        for face_encoding in face_encodings:
            # Compara com TODOS os alunos do banco
            known_encodings = [a["encoding"] for a in alunos]
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)

            best_match_index = np.argmin(face_distances)
            
            if matches[best_match_index]:
                aluno_identificado = alunos[best_match_index]
                nome = aluno_identificado["nome"]
                turma = aluno_identificado["turma"]
                
                st.balloons() # Festa! 🎉
                st.success(f"✅ PRESENÇA CONFIRMADA!")
                st.markdown(f"## 🎓 Aluno: **{nome}**")
                st.markdown(f"### 🏫 Turma: {turma}")
                
                # Aqui futuramente salvaremos a presença no banco "frequencia"
            else:
                st.error("❌ Aluno não reconhecido no sistema.")
