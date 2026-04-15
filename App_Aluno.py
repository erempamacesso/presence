import streamlit as st
from supabase import create_client
import os
import sys

# ==========================================
# CONFIGURAÇÃO DE PÁGINA (SIDEBAR REMOVIDA)
# ==========================================
st.set_page_config(
    page_title="Portal do Aluno | EREMPAM",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="collapsed" # Começa fechado
)

# --- CSS PARA BOTÕES GRANDES E ESCONDER SIDEBAR ---
st.markdown("""
    <style>
        /* Esconde o botão de abrir a sidebar e a própria sidebar */
        [data-testid="stSidebarNav"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
        
        /* Estilização dos Botões Grandes (Dashboard) */
        div.stButton > button {
            width: 100%;
            height: 100px;
            border-radius: 15px;
            font-size: 20px !important;
            font-weight: bold;
            margin-bottom: 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background-color: #f0f2f6;
            border: 2px solid #e0e0e0;
            transition: all 0.3s ease;
        }
        
        div.stButton > button:hover {
            border-color: #ff4b4b;
            color: #ff4b4b;
            transform: scale(1.02);
        }

        /* Ajuste para o texto dentro do botão */
        div.stButton > button p {
            font-size: 20px !important;
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
# CONEXÃO SUPABASE (MESMA LÓGICA ATUAL)
# ==========================================
@st.cache_resource
def init_connections():
    try:
        url_alunos = st.secrets["SIGEREMPAM_URL"]
        key_alunos = st.secrets["SIGEREMPAM_KEY"]
        url_provas = st.secrets["AVALIADOR_URL"]
        key_provas = st.secrets["AVALIADOR_KEY"]
        return create_client(url_alunos, key_alunos), create_client(url_provas, key_provas)
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None, None

db_alunos, db_provas = init_connections()

# ==========================================
# LÓGICA DE NAVEGAÇÃO POR BOTÕES (HUB)
# ==========================================
if "etapa" not in st.session_state:
    st.session_state.etapa = "login"

if "aluno" not in st.session_state:
    st.session_state.aluno = None

try:
    # 1. TELA DE LOGIN
    if st.session_state.etapa == "login":
        mostrar_tela_login(db_alunos)
    
    # 2. HUB PRINCIPAL (BOTÕES GRANDES)
    elif st.session_state.etapa == "dashboard":
        if not st.session_state.aluno:
            st.session_state.etapa = "login"
            st.rerun()
            
        st.markdown(f"### Olá, {st.session_state.aluno['nome']}! 👋")
        st.write("O que você deseja fazer hoje?")
        
        # Grid de Botões Grandes (2 colunas para mobile/desktop)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📝\nSimulados\nDisponíveis", key="btn_provas"):
                st.session_state.sub_etapa = "provas"
                # Aqui você pode redirecionar para a função específica
            
        with col2:
            if st.button("📊\nMeu\nDesempenho", key="btn_notas"):
                st.session_state.sub_etapa = "notas"

        with col1:
            if st.button("✅\nAtividades\nConcluídas", key="btn_concluidas"):
                st.session_state.sub_etapa = "concluidas"

        with col2:
            if st.button("🚪\nSair do\nPortal", key="btn_logout"):
                st.session_state.aluno = None
                st.session_state.etapa = "login"
                st.rerun()

        # Renderiza a tela baseada no botão clicado (Sub-etapas)
        sub = st.session_state.get("sub_etapa", "provas")
        st.divider()
        
        # Chama as funções que já criamos antes
        mostrar_tela_dashboard(db_alunos, db_provas) # Você pode ajustar para mostrar só a aba certa

    # 3. EXECUÇÃO DE PROVA
    elif st.session_state.etapa == "instrucoes":
        render_instrucoes()
    elif st.session_state.etapa == "prova":
        render_prova(db_provas)
    elif st.session_state.etapa == "suspense":
        render_suspense()
    elif st.session_state.etapa == "revisao":
        render_revisao(db_provas)

except Exception as e:
    st.error(f"❌ Erro: {str(e)}")
    if st.button("🔄 Voltar para Início"):
        st.session_state.etapa = "login"
        st.rerun()