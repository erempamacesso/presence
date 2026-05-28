import streamlit as st
import sys
import os
from supabase import create_client

# ==========================================
# 1. CONFIGURAÇÃO DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Portal do Aluno | EREMPAM",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="collapsed",
)

# ==========================================
# 2. IMPORTAÇÕES (AJUSTADAS PARA A RAIZ)
# ==========================================
# Adiciona o diretório raiz ao sys.path para garantir a localização dos módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Importações explícitas apontando para a pasta de telas do aluno
    from telas_aluno.login import mostrar_tela_login
    from telas_aluno.dashboard_aluno import mostrar_tela_dashboard
    from telas_aluno.execucao_prova import render_instrucoes, render_prova
    from telas_aluno.resultados import render_suspense, render_revisao
    from telas_aluno.execucao_lista import exibir_execucao_lista
except ImportError as e:
    st.error(
        f"❌ Erro crítico de importação: {e}. Verifique se a pasta 'telas_aluno' e o arquivo '__init__.py' existem."
    )
    st.stop()


# ==========================================
# 3. CONEXÃO COM O SUPABASE
# ==========================================
@st.cache_resource
def init_connections():
    try:
        db_alunos = create_client(
            st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"]
        )
        db_provas = create_client(
            st.secrets["SUPABASE_URL_PROVAS"], st.secrets["SUPABASE_KEY_PROVAS"]
        )
        return db_alunos, db_provas
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return None, None


db_alunos, db_provas = init_connections()

# ==========================================
# 4. ESTADO DA SESSÃO (SESSION STATE)
# ==========================================
if "aluno" not in st.session_state:
    st.session_state.aluno = None
if "etapa" not in st.session_state:
    st.session_state.etapa = "home"
if "prova_config" not in st.session_state:
    st.session_state.prova_config = None

# ==========================================
# 5. ROTEAMENTO DE TELAS (O CORAÇÃO)
# ==========================================

# CASO A: ALUNO NÃO LOGADO
if st.session_state.aluno is None:
    mostrar_tela_login(db_alunos)

# CASO B: ALUNO LOGADO
else:
    etapa = st.session_state.etapa

    if etapa == "home":
        mostrar_tela_dashboard(db_alunos, db_provas)

    elif etapa == "instrucoes":
        render_instrucoes(db_provas)

    elif etapa == "em_prova":
        render_prova(db_provas)

    elif etapa == "em_exercicio":
        exibir_execucao_lista(db_provas)

    elif etapa == "resultado_final":
        # Passamos as 4 cores que a função exige para parar o erro de TypeError
        render_suspense("#00b4d8", "#6c757d", "#0077b6", "#1e293b")

    elif etapa == "revisao":
        render_revisao(db_provas)

    # SEGURANÇA: Se a etapa sumir ou for inválida, volta para a home
    else:
        st.session_state.etapa = "home"
        st.rerun()

# CSS para esconder o header e limpar o visual
st.markdown(
    """<style>[data-testid="stHeader"] {visibility: hidden;}</style>""",
    unsafe_allow_html=True,
)
