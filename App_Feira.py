import streamlit as st
import os
import sys
from supabase import create_client

# ==========================================
# CONFIGURAÇÃO DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Ecossistema EREMPAM",
    layout="wide",
    page_icon="🌍",
    initial_sidebar_state="collapsed",
)

# Força o reconhecimento do diretório raiz para evitar o erro "No module named 'telas_gestao'"
root_path = os.path.dirname(os.path.abspath(__file__))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# ==========================================
# IMPORTAÇÕES DAS TELAS (Nova Pasta!)
# ==========================================
try:
    from telas_app_aluno.login import mostrar_tela_login
    from telas_app_aluno.ante_sala import mostrar_ante_sala
    from telas_app_aluno.inscricao_aluno import mostrar_inscricao_aluno
    from telas_gestao.visualizacao_equipes import mostrar_painel_organizacao
except ImportError as e:
    st.error(f"❌ Erro ao importar módulos: {e}")
    st.stop()


# ==========================================
# CONEXÃO SUPABASE
# ==========================================
@st.cache_resource
def init_connections():
    try:

        def clean_secret(key):
            # Remove aspas, espaços, quebras de linha e caracteres invisíveis (como \xa0)
            val = str(st.secrets.get(key, "")).strip(" \n\r\t'\"")
            val = val.replace("\xa0", "").replace("\u200b", "")
            return val

        url_alunos = clean_secret("SUPABASE_URL_ALUNOS")
        key_alunos = clean_secret("SUPABASE_KEY_ALUNOS")
        url_provas = clean_secret("SUPABASE_URL_PROVAS")
        key_provas = clean_secret("SUPABASE_KEY_PROVAS")

        # Validação de segurança: se a URL não começar com http, algo está errado nos Secrets
        for label, url in [("Alunos", url_alunos), ("Provas", url_provas)]:
            if url and not url.startswith("http"):
                st.error(f"🚨 A URL do Banco de {label} parece inválida: {url}")
                st.stop()

        db_alunos = create_client(url_alunos, key_alunos)
        db_provas = create_client(url_provas, key_provas)
        return db_alunos, db_provas
    except Exception as e:
        st.error(f"🚨 Falha crítica na conexão: {e}")
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
    mostrar_tela_login(
        db_alunos
    )  # Usa o banco de alunos para validar matrícula/nascimento

elif st.session_state.etapa == "ante_sala":
    mostrar_ante_sala()  # O HUB Central (Ecossistema)

elif st.session_state.etapa == "inscricao_aluno":
    mostrar_inscricao_aluno(db_alunos, db_provas)

elif st.session_state.etapa == "gestao_organizacao":
    mostrar_painel_organizacao(db_alunos, db_provas)
