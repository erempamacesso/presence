import streamlit as st
from supabase import create_client

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
# CSS MOBILE: ULTRA MINIMALISTA (Estilo iOS)
# ==========================================
st.markdown("""
    <style>
        /* Esconde Sidebar */
        [data-testid="collapsedControl"], [data-testid="stSidebar"] { display: none !important; }
        
        /* Margens super enxutas */
        .block-container {
            padding: 1.5rem 1rem !important;
            max-width: 100% !important;
        }

        /* BOTÕES EM FORMATO DE LISTA (iOS Style) */
        div.stButton > button {
            height: 55px !important; /* Bem finos */
            border-radius: 8px !important;
            font-size: 15px !important;
            font-weight: 400 !important;
            border: 1px solid #E5E7EB !important; /* Borda quase invisível */
            background-color: transparent !important;
            color: #1F2937 !important;
            display: flex !important;
            justify-content: flex-start !important; /* Alinhado à esquerda */
            padding-left: 20px !important;
            box-shadow: none !important;
            transition: background 0.2s ease;
        }
        
        div.stButton > button:hover {
            background-color: #F3F4F6 !important;
            border-color: #D1D5DB !important;
        }

        /* Texto do Cabeçalho Super Clean */
        .header-nome {
            font-size: 22px !important;
            font-weight: 500 !important;
            color: #111827;
            margin-bottom: 2px !important;
        }
        .header-turma {
            font-size: 13px !important;
            color: #6B7280;
            margin-bottom: 30px !important;
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
    try:
        url_alunos = st.secrets["SUPABASE_URL_ALUNOS"]
        key_alunos = st.secrets["SUPABASE_KEY_ALUNOS"]
        url_provas = st.secrets["SUPABASE_URL_PROVAS"]
        key_provas = st.secrets["SUPABASE_KEY_PROVAS"]
        return create_client(url_alunos, key_alunos), create_client(url_provas, key_provas)
    except Exception as e:
        st.error(f"❌ Erro ao conectar: {str(e)}")
        st.stop()

db_alunos, db_provas = init_connections()

# ==========================================
# INICIALIZAÇÃO DO SESSION STATE
# ==========================================
if 'etapa' not in st.session_state:
    st.session_state.etapa = "login"

if 'aluno' not in st.session_state:
    st.session_state.aluno = None

# ==========================================
# ROTEADOR DE TELAS (MÁQUINA DE ESTADOS)
# ==========================================
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