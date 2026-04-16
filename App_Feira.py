import streamlit as st
from supabase import create_client

# ==========================================
# CONFIGURAÇÃO DE PÁGINA (DEVE SER O PRIMEIRO COMANDO)
# ==========================================
st.set_page_config(
    page_title="Inscrição Eventos | EREMPAM",
    layout="wide",
    page_icon="🎪",
    initial_sidebar_state="collapsed"
)

# ==========================================
# IMPORTAÇÕES DAS TELAS
# ==========================================
try:
    from telas_aluno.login import mostrar_tela_login
    from telas_aluno.inscricao_feira import mostrar_tela_inscricao_feira 
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

        db_alunos = create_client(url_alunos, key_alunos)
        db_provas = create_client(url_provas, key_provas)
        return db_alunos, db_provas
    except Exception as e:
        st.error("🚨 Erro ao carregar as credenciais do banco de dados. Verifique os Secrets.")
        st.stop()

db_alunos, db_provas = init_connections()

# ==========================================
# ESTADO DA SESSÃO (MÁQUINA DE ESTADOS)
# ==========================================
if "etapa" not in st.session_state:
    st.session_state.etapa = "login"

if "aluno" not in st.session_state:
    st.session_state.aluno = None

# ==========================================
# ROTEAMENTO DAS TELAS DO APP DA FEIRA
# ==========================================
if st.session_state.etapa == "login":
    # Reaproveitamos a mesma tela de login que você já tem!
    mostrar_tela_login(db_alunos)
    
    # Se ele logar, ao invés de ir pro dashboard, vai direto pra feira:
    if st.session_state.etapa == "ante_sala":
        st.session_state.etapa = "inscricao_feira"
        st.rerun()

elif st.session_state.etapa == "inscricao_feira":
    # Chama a tela da feira. O db_provas é onde estão as tabelas da feira.
    mostrar_tela_inscricao_feira(db_provas)