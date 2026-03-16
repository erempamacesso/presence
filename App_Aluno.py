import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import time

# ==========================================
# 1. CONFIGURAÇÕES E CSS (REMOVENDO SIDEBAR)
# ==========================================
st.set_page_config(page_title="Portal do Aluno - EREMPAM", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        .main .block-container {padding-top: 2rem;}
        .aviso-box {
            background-color: #fff3cd; 
            padding: 20px; 
            border-radius: 10px; 
            border: 1px solid #ffeeba;
            color: #856404;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO COM O SUPABASE
# ==========================================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL_ALUNOS"]
    key = st.secrets["SUPABASE_KEY_ALUNOS"]
    return create_client(url, key)

supabase: Client = init_connection()

# ==========================================
# 3. CONTROLE DE ESTADO (MEMÓRIA DO APP)
# ==========================================
if 'etapa' not in st.session_state:
    st.session_state.etapa = "login"
if 'aluno' not in st.session_state:
    st.session_state.aluno = None
if 'prova_config' not in st.session_state:
    st.session_state.prova_config = None
if 'tempo_final' not in st.session_state:
    st.session_state.tempo_final = None

# ==========================================
# ETAPA 1: TELA DE LOGIN
# ==========================================
if st.session_state.etapa == "login":
    # Adapte o nome da sua imagem de logo aqui
    st.image("logo_erempam.png", width=120) 
    st.title("Login do Estudante")
    
    matricula = st.text_input("Digite sua Matrícula")
    
    if st.button("ACESSAR PROVA"):
        if matricula:
            try:
                # 1. Busca o aluno no banco
                resposta_aluno = supabase.table("alunos").select("*").eq("numero_matricula", matricula).execute()
                
                if len(resposta_aluno.data) > 0:
                    st.session_state.aluno = resposta_aluno.data[0]
                    
                    # 2. Busca as configurações da prova (tempo e data limite)
                    # Aqui pegamos a primeira prova ativa como exemplo.
                    resposta_prova = supabase.table("modelos_prova").select("*").limit(1).execute()
                    
                    if len(resposta_prova.data) > 0:
                        st.session_state.prova_config = resposta_prova.data[0]
                    else:
                        # Valores padrão caso você não tenha cadastrado a prova ainda
                        st.session_state.prova_config = {"tempo_duracao": 60, "data_limite": "2026-12-31T23:59:00"}
                        
                    st.session_state.etapa = "ante_sala"
                    st.rerun()
                else:
                    st.error("Matrícula não encontrada no sistema.") #
            except Exception as e:
                st.error(f"Erro ao conectar com o banco: {e}")
        else:
            st.warning("Por favor, digite uma matrícula.")

# ==========================================
# 2. CONEXÃO COM OS DOIS PROJETOS SUPABASE
# ==========================================
@st.cache_resource
def init_db_alunos():
    return create_client(st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"])

@st.cache_resource
def init_db_provas():
    return create_client(st.secrets["SUPABASE_URL_PROVAS"], st.secrets["SUPABASE_KEY_PROVAS"])

# Criamos as duas conexões
db_alunos = init_db_alunos()
db_provas = init_db_provas()

# ==========================================
# ETAPA 1: TELA DE LOGIN (Usa db_alunos)
# ==========================================
if st.session_state.etapa == "login":
    # ... (seu código de imagem e título)
    matricula = st.text_input("Digite sua Matrícula")
    
    if st.button("ACESSAR PROVA"):
        if matricula:
            try:
                # 🟢 BUSCA O ALUNO NO PROJETO 1 (SIGEREMPAM)
                res_aluno = db_alunos.table("alunos").select("*").eq("numero_matricula", matricula).execute()
                
                if len(res_aluno.data) > 0:
                    st.session_state.aluno = res_aluno.data[0]
                    
                    # 🟢 BUSCA A PROVA NO PROJETO 2 (AVALIADOR)
                    # Agora usamos db_provas para não dar o erro PGRST205!
                    res_prova = db_provas.table("modelos_prova").select("*").eq("ativa", True).limit(1).execute()
                    
                    if len(res_prova.data) > 0:
                        st.session_state.prova_config = res_prova.data[0]
                        st.session_state.etapa = "ante_sala"
                        st.rerun()
                    else:
                        st.error("Nenhuma prova ativa encontrada no sistema do Avaliador.")
                else:
                    st.error("Matrícula não encontrada.")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")
# ==========================================
# ETAPA 3: TELA DA PROVA + CRONÔMETRO
# ==========================================
elif st.session_state.etapa == "prova":
    aluno = st.session_state.aluno
    
    # CABEÇALHO DINÂMICO
    col_foto, col_info, col_timer = st.columns([1, 4, 2])
    
    with col_foto:
        # Puxa a foto do banco, se não tiver, usa o ícone padrão
        foto_url = aluno.get('foto_url', "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
        st.image(foto_url, width=80)
        
    with col_info:
        st.markdown(f"### **{aluno.get('nome', 'Aluno')}**")
        st.caption(f"📍 {aluno.get('turma', 'Turma')} | Avaliação Online")

    with col_timer:
        # Lógica do tempo
        tempo_restante = st.session_state.tempo_final - datetime.now()
        segundos_totais = int(tempo_restante.total_seconds())
        
        if segundos_totais <= 0:
            st.error("⌛ TEMPO ESGOTADO!")
            st.warning("O sistema enviará suas respostas automaticamente.")
            # st.button("Finalizar Prova") -> Aqui entrará a lógica de forçar o envio
            st.stop() # Trava a tela para o aluno não marcar mais nada
        else:
            mins, secs = divmod(segundos_totais, 60)
            st.metric("⏳ Tempo Restante", f"{mins:02d}:{secs:02d}")
            
    st.divider()
    
    # ----------------------------------------------------
    # AQUI ENTRA O SEU CÓDIGO DE RENDERIZAR AS QUESTÕES
    # st.write("Questão 1: O isooctano é...")
    # ----------------------------------------------------
    st.info("As questões da prova aparecerão aqui...")