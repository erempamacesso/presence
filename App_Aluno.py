import streamlit as st
from supabase import create_client

# ==========================================
# CONFIGURAÇÃO DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Portal do Aluno | EREMPAM",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="collapsed"
)

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
# CONEXÃO COM O SUPABASE
# ==========================================
@st.cache_resource
def init_connections():
    try:
        url_alunos = st.secrets["SUPABASE_URL_ALUNOS"]
        key_alunos = st.secrets["SUPABASE_KEY_ALUNOS"]
        url_provas = st.secrets["SUPABASE_URL_PROVAS"]
        key_provas = st.secrets["SUPABASE_KEY_PROVAS"]
        
        db_alunos = create_client(url_alunos, key_alunos)
        db_provas = create_client(url_provas, key_provas)
        return db_alunos, db_provas
    except Exception as e:
        st.error(f"Erro na conexão com o Banco de Dados: {e}")
        return None, None

db_alunos, db_provas = init_connections()

# ==========================================
# ESTADO DA SESSÃO (SESSION STATE)
# ==========================================
if "aluno" not in st.session_state:
    st.session_state.aluno = None
if "etapa" not in st.session_state:
    st.session_state.etapa = "home"
if "prova_config" not in st.session_state:
    st.session_state.prova_config = None
if "menu_active" not in st.session_state:
    st.session_state.menu_active = "home"

# ==========================================
# CSS CUSTOMIZADO (DESIGN ADAPTÁVEL)
# ==========================================
st.markdown("""
    <style>
        /* Esconder Header Original do Streamlit */
        [data-testid="stHeader"] { visibility: hidden; }
        
        /* Ajuste de Margens */
        .block-container {
            padding-top: 2rem !important;
            max-width: 100% !important;
        }

        /* Botões Estilizados */
        div.stButton > button {
            height: 60px !important; 
            border-radius: 10px !important;
            font-size: 16px !important;
            transition: all 0.2s ease;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ROTEAMENTO DE TELAS (O MAESTRO)
# ==========================================

# 1. Se não está logado, mostra tela de Login
if st.session_state.aluno is None:
    mostrar_tela_login(db_alunos)

# 2. Se logado, verifica em qual etapa o aluno está
else:
    # TELA 0: Dashboard (Menu Principal)
    if st.session_state.etapa == "home":
        mostrar_tela_dashboard(db_alunos, db_provas)

    # TELA 1: Instruções antes da Prova
    elif st.session_state.etapa == "instrucoes":
        render_instrucoes(db_provas)

    # TELA 2: Execução da Prova (Onde o cronômetro roda)
    elif st.session_state.etapa == "em_prova":
        render_prova(db_provas)

    # TELA 3: Tela de Transição/Resultado (Parabéns/Nota)
    elif st.session_state.etapa == "resultado_final":
        render_suspense(db_provas)

    # TELA 4: Revisão da Prova (Ver o que errou/acertou)
    elif st.session_state.etapa == "revisao":
        render_revisao(db_provas)