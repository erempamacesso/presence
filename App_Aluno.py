import streamlit as st
from supabase import create_client
import os
import sys

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
# CONFIGURAÇÃO DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Portal do Aluno | EREMPAM",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="collapsed"
)

# ==========================================
# CONEXÃO COM OS DOIS PROJETOS SUPABASE
# ==========================================
@st.cache_resource
def init_connections():
    """
    Inicializa as conexões com os dois projetos Supabase.
    
    Projeto 1: SIGEREMPAM (Alunos e Chamada)
    Projeto 2: AVALIADOR (Questões e Provas)
    """
    try:
        # Validar se secrets estão carregados
        try:
            url_alunos = st.secrets["SUPABASE_URL_ALUNOS"]
            key_alunos = st.secrets["SUPABASE_KEY_ALUNOS"]
            url_provas = st.secrets["SUPABASE_URL_PROVAS"]
            key_provas = st.secrets["SUPABASE_KEY_PROVAS"]
        except KeyError as e:
            st.error(f"❌ Secret não configurado: {e}")
            st.info("📋 Verifique se todos os secrets estão no `.streamlit/secrets.toml`")
            st.stop()
        
        # Projeto 1: SIGEREMPAM (Alunos)
        db_alunos = create_client(url_alunos, key_alunos)
        
        # Projeto 2: AVALIADOR (Provas)
        db_provas = create_client(url_provas, key_provas)
        
        return db_alunos, db_provas
        
    except Exception as e:
        st.error(f"❌ Erro ao conectar aos bancos de dados: {str(e)}")
        st.stop()

# Inicializa os bancos de dados
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
        # Tela de Login
        mostrar_tela_login(db_alunos)
    
    elif st.session_state.etapa == "ante_sala":
        # Validar se aluno está autenticado
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
        
        # Dashboard do Aluno (Provas Disponíveis e Desempenho)
        mostrar_tela_dashboard(db_alunos, db_provas)
    
    elif st.session_state.etapa == "instrucoes":
        # Validar se aluno está autenticado
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
        
        # Tela de Instruções da Prova
        render_instrucoes(db_provas)
    
    elif st.session_state.etapa == "execucao":
        # Validar se aluno está autenticado
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
        
        # Execução da Prova
        render_prova(db_provas)
    
    elif st.session_state.etapa == "suspense":
        # Validar se aluno está autenticado
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
        
        # Tela de Suspense (Verificando resposta)
        render_suspense()
    
    elif st.session_state.etapa == "revisao":
        # Validar se aluno está autenticado
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
        
        # Tela de Revisão de Resultados
        render_revisao(db_provas)
    
    else:
        # Estado desconhecido - retornar ao login
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
# RODAPÉ COM INFORMAÇÕES DE DEBUG
# ==========================================
with st.sidebar:
    if st.checkbox("🔧 Mostrar Debug Info"):
        st.write("### Debug Info")
        st.write(f"**Etapa Atual:** {st.session_state.etapa}")
        st.write(f"**Aluno Autenticado:** {st.session_state.aluno is not None}")
        if st.session_state.aluno:
            st.write(f"**Nome:** {st.session_state.aluno.get('nome', 'N/A')}")
            st.write(f"**Matrícula:** {st.session_state.aluno.get('numero_matricula', 'N/A')}")
        st.divider()
        if st.button("🔐 Fazer Logout"):
            st.session_state.etapa = "login"
            st.session_state.aluno = None
            st.rerun()