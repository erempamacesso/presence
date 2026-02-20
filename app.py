import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import unicodedata
import time
from datetime import datetime, date
from streamlit_option_menu import option_menu
from urllib.parse import quote

# 1. CONFIGURAÇÃO E CONEXÃO
st.set_page_config(page_title="SIGPAM - EREMPAM", layout="wide")

@st.cache_resource
def init_connection():
    load_dotenv()
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_connection()

# 2. SIDEBAR (MENU QUE TINHA SUMIDO)
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>SIGPAM</h2>", unsafe_allow_html=True)
    menu_escolhido = option_menu(
        menu_title=None,
        options=["Frequência", "Reservas", "Fotograma", "Cadastro", "Importação"],
        icons=["clipboard-check", "calendar-check", "camera", "person-plus", "cloud-upload"],
        default_index=1, # Define Reservas como padrão por enquanto
        styles={"nav-link-selected": {"background-color": "#ff4b4b"}}
    )

# 3. LÓGICA DAS TELAS
if menu_escolhido == "Frequência":
    st.title("📊 Relatório de Frequência")
    st.info("Aqui fica o seu código original de frequência.")

elif menu_escolhido == "Reservas":
    st.title("📅 Sistema de Reservas")
    
    # Listas de apoio
    AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]
    ESPACOS = ["Auditório", "Laboratório de Ciências", "Sala de informática", "Biblioteca", "Refeitório"]

    col1, col2 = st.columns(2)
    with col1:
        data_sel = st.date_input("Data da Reserva:", min_value=datetime.today().date())
    with col2:
        aula_sel = st.selectbox("Qual Aula?", AULAS)

    # Consulta ao banco (Usando 'periodo' como no seu banco)
    try:
        res = supabase.table("reservas").select("*").eq("data_reserva", str(data_sel)).eq("periodo", aula_sel).execute()
        reservas_existentes = res.data
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        reservas_existentes = []

    # Formulário de Reserva
    with st.form("form_reserva"):
        prof = st.text_input("Nome do Professor:")
        esp = st.selectbox("Espaço:", ESPACOS)
        obs = st.text_area("Observações:")
        
        if st.form_submit_button("✅ Confirmar Reserva"):
            if prof:
                dados = {
                    "data_reserva": str(data_sel),
                    "periodo": aula_sel,
                    "professor": prof.upper(),
                    "espaco": esp,
                    "observacoes": obs
                }
                try:
                    supabase.table("reservas").insert(dados).execute()
                    st.success("🎉 Reserva realizada!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Digite o nome do professor.")

elif menu_escolhido == "Fotograma":
    st.title("📸 Fotograma")
    st.info("Aqui fica a visualização dos alunos.")

# Repita para as outras abas...
