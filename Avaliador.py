import streamlit as st
from supabase import create_client
import pandas as pd
import re  # Importação necessária para a função de limpar o texto
import random  # Necessário para embaralhar as questões
from telas_aluno.execucao_lista import exibir_execucao_lista

# --- 1. CONFIGURAÇÃO E CONEXÃO ---
st.set_page_config(page_title="EREMPAM - Avaliação", layout="centered")

URL = st.secrets["SUPABASE_URL_PROVAS"]
KEY = st.secrets["SUPABASE_KEY_PROVAS"]
supabase = create_client(URL, KEY)

# --- CONTROLE DE ESTADO (NAVEGAÇÃO) ---
if "etapa" not in st.session_state:
    st.session_state.etapa = "portal_inicial"

# Se o aluno estiver dentro de um exercício, redireciona para o módulo específico
if st.session_state.etapa == "em_exercicio":
    exibir_execucao_lista(supabase)
    st.stop()

st.title("📝 Portal de Avaliações - EREMPAM")

tab_provas = st.tabs(["📝 Provas Oficiais"])[0]

# ==========================================
# ABA DE PROVAS (LÓGICA ORIGINAL)
# ==========================================
with tab_provas:
    st.subheader("Avaliações Disponíveis")
