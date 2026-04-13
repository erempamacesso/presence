# App_Aluno.py
import streamlit as st
from supabase import create_client
import base64
import os

# Importando os módulos que criamos
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
            pass
    return ""

logo_lardiao_b64 = get_base64_image("logo_lardiao.png")

st.markdown(f"""
    <style>
        .stApp {{ background-color: {C_BG_DEEP} !important; }}
        .stApp p, .stApp span, .stApp label, .stMarkdown p {{ color: {C_TEXT} !important; }}
        div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {{ color: {C_TEXT} !important; font-size: 16px !important; }}
        [data-testid="stSidebar"] {{display: none;}} #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}}
        .main .block-container {{padding-top: 1.5rem;}}
        .stTextInput>div>div>input {{ background-color: #F7FAFC !important; color: {C_TEXT} !important; border-radius: 12px !important; border-color: {C_BORDER} !important; padding: 14px !important; font-size: 16px !important; }}
        .stTextInput>div>div>input:focus {{ border-color: {C_PRIMARY} !important; box-shadow: 0 0 0 0.2rem rgba(0,200,150,0.2) !important; background-color: #FFFFFF !important; }}
        .stButton>button[kind="primary"] {{ background-color: {C_PRIMARY}; color: #FFFFFF; border: none; border-radius: 12px; height: 3.8em; font-weight: bold; font-size: 17px; transition: all 0.3s ease; width: 100%; }}
        .stButton>button[kind="primary"]:hover {{ background-color: {C_SECONDARY}; color: white; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,128,0,0.3); }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO SEGURA COM BANCO DE DADOS
# ==========================================
@st.cache_resource
def init_connections():
    db_a = create_client(st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"])
    db_p = create_client(st.secrets["SUPABASE_URL_PROVAS"], st.secrets["SUPABASE_KEY_PROVAS"])
    return db_a, db_p

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
    # Passamos db_provas para buscar as atividades e as notas no dashboard
    mostrar_tela_dashboard(db_provas, db_provas) 

elif st.session_state.etapa == "instrucoes":
    render_instrucoes(db_provas)

elif st.session_state.etapa == "em_prova":
    render_prova(db_provas, C_PRIMARY)

elif st.session_state.etapa == "resultado_final":
    render_suspense(C_PRIMARY, C_TEXT_MUTED, C_SECONDARY, C_TEXT)

elif st.session_state.etapa == "ver_meu_resultado":
    # Aqui estava o errinho! Agora passamos o db_provas para a função
    render_revisao(db_provas)