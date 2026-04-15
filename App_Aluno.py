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
# CSS MOBILE: CLEAN & DISCRETO
# ==========================================
st.markdown("""
    <style>
        /* Esconde Sidebar e controles */
        [data-testid="collapsedControl"], [data-testid="stSidebar"] { display: none !important; }
        
        /* Remove o espaço em branco gigante no topo */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }

        /* BOTÕES DO MENU: Menores e mais elegantes */
        div.stButton > button {
            height: 75px !important; /* Altura reduzida */
            border-radius: 10px !important;
            font-size: 14px !important; /* Fonte menor */
            font-weight: 500 !important;
            border: 1px solid #eeeeee !important;
            background-color: #fcfcfc !important;
            color: #444444 !important;
            transition: all 0.2s ease;
        }
        
        div.stButton > button:hover {
            border-color: #4CAF50 !important;
            background-color: #ffffff !important;
            color: #4CAF50 !important;
        }

        /* Estilo para Títulos Discretos */
        .titulo-clean {
            font-size: 18px !important;
            font-weight: 600 !important;
            color: #333333;
            margin-bottom: 5px !important;
        }
        
        .subtitulo-clean {
            font-size: 14px !important;
            color: #777777;
            margin-bottom: 20px !important;
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