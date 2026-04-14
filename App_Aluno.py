# App_Aluno.py
import streamlit as st
from supabase import create_client
import base64
import os

# Importando os módulos das telas
from telas_aluno.login import mostrar_tela_login
from telas_aluno.dashboard_aluno import mostrar_tela_dashboard
from telas_aluno.execucao_prova import render_instrucoes, render_prova
from telas_aluno.resultados import render_suspense, render_revisao

# ==========================================
# 1. CONFIGURAÇÕES, IDENTIDADE E ESTILO
# ==========================================
st.set_page_config(
    page_title="Portal de Avaliações | Química com Lardião Pro", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="logo_erempam.png" 
)

# Cores da Identidade Visual
C_BG_DEEP = "#F0F4F8"      
C_CARD_BG = "#FFFFFF"     
C_PRIMARY = "#00C896"     
C_SECONDARY = "#FF8000"   
C_TEXT = "#2D3748"        
C_TEXT_MUTED = "#718096"  
C_BORDER = "#E2E8F0"      

def get_base64_image(image_path):
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except:
            return ""
    return ""

logo_lardiao_b64 = get_base64_image("logo_lardiao.png")

# ==========================================
# 2. CONEXÃO COM OS DOIS PROJETOS SUPABASE
# ==========================================
@st.cache_resource
def init_connections():
    # Projeto 1: Chamada Escolar (Notas e Presença)
    url_alunos = st.secrets["supabase_url"]
    key_alunos = st.secrets["supabase_key"]
    db_alunos = create_client(url_alunos, key_alunos)
    
    # Projeto 2: Avaliador (Provas e Simulados)
    url_provas = st.secrets["supabase_url_avaliador"]
    key_provas = st.secrets["supabase_key_avaliador"]
    db_provas = create_client(url_provas, key_provas)
    
    return db_alunos, db_provas

db_alunos, db_provas = init_connections()

# ==========================================
# 3. ESTADO DA SESSÃO (MEMÓRIA)
# ==========================================
for key in ['etapa', 'aluno', 'prova_config', 'tempo_final', 'questoes', 'respostas', 'prova_resultado']:
    if key not in st.session_state: 
        if key == 'etapa':
            st.session_state[key] = "login"
        elif key == 'respostas':
            st.session_state[key] = {}
        else:
            st.session_state[key] = None

# ==========================================
# 4. ROTEADOR DE TELAS
# ==========================================
if st.session_state.etapa == "login":
    mostrar_tela_login(db_alunos, logo_lardiao_b64, C_CARD_BG, C_BORDER, C_PRIMARY, C_TEXT_MUTED)

elif st.session_state.etapa == "ante_sala":
    if 'aluno' not in st.session_state or not st.session_state.aluno:
        st.session_state.etapa = "login"
        st.rerun()
    
    # IMPORTANTE: Passamos os dois bancos para o dashboard
    # db_alunos (para notas) e db_provas (para simulados)
    mostrar_tela_dashboard(db_alunos, db_provas) 

elif st.session_state.etapa == "instrucoes":
    render_instrucoes(db_provas)

elif st.session_state.etapa == "execucao":
    render_prova(db_provas)

elif st.session_state.etapa == "suspense":
    render_suspense()

elif st.session_state.etapa == "revisao":
    render_revisao()

# Estilo Global (CSS)
st.markdown(f"""
    <style>
    .stApp {{ background-color: {C_BG_DEEP}; }}
    [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
    .main .block-container {{ padding-top: 2rem; }}
    </style>
""", unsafe_allow_html=True)