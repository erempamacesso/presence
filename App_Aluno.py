import streamlit as st
from supabase import create_client
import base64
import os

# Importando as telas
from telas_aluno.login import mostrar_tela_login
from telas_aluno.dashboard_aluno import mostrar_tela_dashboard
from telas_aluno.execucao_prova import render_instrucoes, render_prova
from telas_aluno.resultados import render_suspense, render_revisao

# Configurações de Página
st.set_page_config(page_title="Portal do Aluno | EREMPAM", layout="wide", page_icon="logo_erempam.png")

# ==========================================
# CONEXÃO COM OS DOIS PROJETOS (SEGREDO)
# ==========================================
@st.cache_resource
def init_connections():
    try:
        # Projeto 1: SIGEREMPAM (Alunos)
        url_alunos = st.secrets["SUPABASE_URL_ALUNOS"]
        key_alunos = st.secrets["SUPABASE_KEY_ALUNOS"]
        db_alunos = create_client(url_alunos, key_alunos)
        
        # Projeto 2: AVALIADOR (Provas)
        url_provas = st.secrets["SUPABASE_URL_PROVAS"]
        key_provas = st.secrets["SUPABASE_KEY_PROVAS"]
        db_provas = create_client(url_provas, key_provas)
        
        return db_alunos, db_provas
    except KeyError as e:
        st.error(f"❌ Erro: Secret não encontrado - {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro ao conectar aos bancos de dados: {e}")
        st.stop()

# Inicializa os bancos
try:
    db_alunos, db_provas = init_connections()
    if db_alunos is None or db_provas is None:
        st.error("❌ Erro: Bancos de dados não inicializados corretamente")
        st.stop()
except Exception as e:
    st.error(f"❌ Erro crítico na inicialização: {e}")
    st.stop()

# ==========================================
# GESTÃO DE ESTADO
# ==========================================
if 'etapa' not in st.session_state: st.session_state.etapa = "login"
if 'aluno' not in st.session_state: st.session_state.aluno = None

# ==========================================
# ROTEADOR DE TELAS
# ==========================================
if st.session_state.etapa == "login":
    mostrar_tela_login(db_alunos)

elif st.session_state.etapa == "ante_sala":
    if not st.session_state.aluno:
        st.session_state.etapa = "login"
        st.rerun()
    # PASSA OS DOIS BANCOS PARA O DASHBOARD
    mostrar_tela_dashboard(db_alunos, db_provas)

elif st.session_state.etapa == "instrucoes":
    render_instrucoes(db_provas)

elif st.session_state.etapa == "execucao":
    render_prova(db_provas)