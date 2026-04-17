import streamlit as st
from supabase import create_client

# ==========================================
# CONFIGURAÇÃO DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Ecossistema EREMPAM",
    layout="wide",
    page_icon="🌍",
    initial_sidebar_state="collapsed"
)

# ==========================================
# IMPORTAÇÕES DAS TELAS (Nova Pasta!)
# ==========================================
try:
    from telas_app_aluno.login import mostrar_tela_login
    from telas_app_aluno.ante_sala import mostrar_ante_sala
    from telas_app_aluno.inscricao_aluno import mostrar_tela_inscricao_feira 
except ImportError as e:
    st.error(f"❌ Erro ao importar módulos: {e}")
    st.stop()

# ==========================================
# CONEXÃO SUPABASE
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
        st.error("🚨 Erro ao carregar as credenciais.")
        st.stop()

db_alunos, db_provas = init_connections()

# ==========================================
# ESTADO DA SESSÃO
# ==========================================
if "etapa" not in st.session_state:
    st.session_state.etapa = "login"

if "aluno" not in st.session_state:
    st.session_state.aluno = None

# ==========================================
# ROTEAMENTO (O GPS DO APP)
# ==========================================
if st.session_state.etapa == "login":
    mostrar_tela_login(db_alunos) # Usa o banco de alunos para validar matrícula/nascimento
    
elif st.session_state.etapa == "ante_sala":
    mostrar_ante_sala() # O HUB Central (Ecossistema)
    
elif st.session_state.etapa == "inscricao_aluno":
    mostrar_tela_inscricao_feira(db_provas) # Usa o banco de provas onde estão os Eventos