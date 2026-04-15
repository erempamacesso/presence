import streamlit as st
from supabase import create_client
import os
import sys

# ==========================================
# CONFIGURAÇÃO DE PÁGINA (DEVE SER O PRIMEIRO COMANDO)
# ==========================================
st.set_page_config(
    page_title="Portal do Aluno | EREMPAM",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="collapsed"
)

# ==========================================
# CSS MOBILE: BOTÕES GRANDES E SEM SIDEBAR
# ==========================================
st.markdown("""
    <style>
        /* Esconde o botão de abrir a sidebar e a própria sidebar */
        [data-testid="stSidebarNav"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}
        section[data-testid="stSidebar"] {display: none !important;}
        
        /* Estilização dos Botões para Mobile (Dashboard) */
        div.stButton > button {
            height: 70px;
            border-radius: 12px;
            font-size: 18px !important;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        div.stButton > button:hover {
            border-color: #ff4b4b;
            color: #ff4b4b;
            transform: scale(1.02);
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# IMPORTAÇÕES DAS TELAS
# ==========================================
try:
    from telas_aluno.login import mostrar_tela_login
    from telas_aluno.dashboard_aluno import mostrar_tela_dashboard
    from telas_aluno.execucao_prova import render_instrucoes, render_prova
    from telas_aluno.resultados import render_suspense, render_revisao
except ImportError as e:
    st.error(f"❌ Erro ao importar módulos: {e}")
    st.stop()

# ==========================================
# CONEXÃO COM OS DOIS PROJETOS SUPABASE
# ==========================================
@st.cache_resource
def init_connections():
    """
    Inicializa as conexões com os dois projetos Supabase.
    """
    try:
        try:
            url_alunos = st.secrets["SUPABASE_URL_ALUNOS"]
            key_alunos = st.secrets["SUPABASE_KEY_ALUNOS"]
            url_provas = st.secrets["SUPABASE_URL_PROVAS"]
            key_provas = st.secrets["SUPABASE_KEY_PROVAS"]
        except KeyError as e:
            st.error(f"❌ Secret não configurado: {e}")
            st.info("📋 Verifique se todos os secrets estão no `.streamlit/secrets.toml`")
            st.stop()
        
        db_alunos = create_client(url_alunos, key_alunos)
        db_provas = create_client(url_provas, key_provas)
        
        return db_alunos, db_provas
        
    except Exception as e:
        st.error(f"❌ Erro ao conectar aos bancos de dados: {str(e)}")
        st.stop()

try:
    db_alunos, db_provas = init_connections()
    if db_alunos is None or db_provas is None:
        st.error("❌ Erro: Bancos de dados não foram inicializados corretamente")
        st.stop()
except Exception as e:
    st.error(f"❌ Erro crítico na inicialização: {str(e)}")
    st.stop()

# ==========================================
# INICIALIZAÇÃO DO SESSION STATE
# ==========================================
if 'etapa' not in st.session_state:
    st.session_state.etapa = "login"

if 'aluno' not in st.session_state:
    st.session_state.aluno = None

if 'prova_config' not in st.session_state:
    st.session_state.prova_config = None

# ==========================================
# ROTEADOR DE TELAS (MÁQUINA DE ESTADOS)
# ==========================================
try:
    if st.session_state.etapa == "login":
        mostrar_tela_login(db_alunos)
    
    elif st.session_state.etapa == "ante_sala":
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
        mostrar_tela_dashboard(db_alunos, db_provas)
    
    elif st.session_state.etapa == "instrucoes":
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
        render_instrucoes(db_provas)
    
    elif st.session_state.etapa == "execucao":
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
        render_prova(db_provas)
    
    elif st.session_state.etapa == "suspense":
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
        render_suspense()
    
    elif st.session_state.etapa == "revisao":
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
        render_revisao(db_provas)
    
    else:
        st.warning(f"⚠️ Estado desconhecido: {st.session_state.etapa}")
        st.session_state.etapa = "login"
        st.rerun()

except Exception as e:
    st.error(f"❌ Erro ao renderizar tela: {str(e)}")
    st.error("💡 Tente fazer login novamente")
    if st.button("🔄 Voltar para Login"):
        st.session_state.etapa = "login"
        st.session_state.aluno = None
        st.rerun()

# ==========================================
# RODAPÉ COM INFORMAÇÕES DE DEBUG (EXPANDER)
# ==========================================
# Trocamos st.sidebar por st.expander para não estragar o layout mobile
st.write("---")
with st.expander("🔧 Mostrar Debug Info (Somente Devs)"):
    st.write(f"**Etapa Atual:** {st.session_state.etapa}")
    st.write(f"**Aluno Autenticado:** {st.session_state.aluno is not None}")
    if st.session_state.aluno:
        st.write(f"**Nome:** {st.session_state.aluno.get('nome', 'N/A')}")
        st.write(f"**Matrícula:** {st.session_state.aluno.get('numero_matricula', 'N/A')}")
    st.divider()
    if st.button("🔐 Forçar Logout"):
        st.session_state.etapa = "login"
        st.session_state.aluno = None
        st.rerun()