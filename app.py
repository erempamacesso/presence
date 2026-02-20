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

# --- DADOS MESTRES (INTEGRADOS DO RESERVAS.PY) ---
LISTA_PROFESSORES = [
    "Ana Maria (Matemática)", "Carlos Eduardo (História)", 
    "Fernanda Lima (Português)", "João Silva (Física)", "Maria Souza (Biologia)"
]
AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]
ESPACOS_TOTAIS = ["Auditório", "Laboratório de Ciências", "Laboratório de Informática", "Biblioteca", "Refeitório", "Quadra", "Nenhum (Só Equipamento)"]

# Estoque fixo
TOTAL_DATASHOWS = 5
TOTAL_CAIXAS = 3
TOTAL_MICROFONES = 3

# 2. SIDEBAR MENU
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>SIGPAM</h2>", unsafe_allow_html=True)
    menu_escolhido = option_menu(
        menu_title=None,
        options=["Frequência", "Reservas", "Fotograma", "Cadastro", "Importação"],
        icons=["clipboard-check", "calendar-check", "camera", "person-plus", "cloud-upload"],
        default_index=1,
        styles={"nav-link-selected": {"background-color": "#ff4b4b"}}
    )

# 3. TELAS
if menu_escolhido == "Frequência":
    st.title("📊 Relatório de Frequência")
    st.info("Espaço destinado ao código de frequência original.")

elif menu_escolhido == "Reservas":
    st.title("📅 Sistema de Reservas Integrado")
    
    # ETAPA 1: SELEÇÃO DE DATA E AULA
    col1, col2 = st.columns(2)
    with col1:
        data_sel = st.date_input("Data da Reserva:", min_value=date.today())
    with col2:
        aula_sel = st.selectbox("Qual Aula?", AULAS)

    # BUSCA RESERVAS EXISTENTES PARA EVITAR CONFLITO
    try:
        res = supabase.table("reservas").select("*").eq("data_reserva", str(data_sel)).eq("periodo", aula_sel).execute()
        reservas_dia = res.data
    except:
        reservas_dia = []

    # LÓGICA DE OCUPAÇÃO (DO SEU RESERVAS.PY)
    espacos_ocupados = [r['espaco'] for r in reservas_dia if r.get('espaco') and r['espaco'] != "Nenhum (Só Equipamento)"]
    espacos_disponiveis = [e for e in ESPACOS_TOTAIS if e not in espacos_ocupados]

    # LÓGICA DE INVENTÁRIO
    d_usados = sum(1 for r in reservas_dia if r.get('equipamentos') and "Datashow" in r['equipamentos'])
    c_usadas = sum(1 for r in reservas_dia if r.get('equipamentos') and "Caixa de Som" in r['equipamentos'])
    
    opcoes_equip = []
    if (TOTAL_DATASHOWS - d_usados) > 0: opcoes_equip.append(f"Datashow ({TOTAL_DATASHOWS - d_usados} disponíveis)")
    if (TOTAL_CAIXAS - c_usadas) > 0: opcoes_equip.append(f"Caixa de Som ({TOTAL_CAIXAS - c_usadas} disponíveis)")

    st.divider()

    # ETAPA 2: FORMULÁRIO FINAL
    with st.form("form_integrado"):
        prof_sel = st.selectbox("👩‍🏫 Professor(a):", ["-- Selecione --"] + sorted(LISTA_PROFESSORES))
        esp_sel = st.selectbox("📍 Espaço:", espacos_disponiveis if espacos_disponiveis else ["Lotado"])
        equip_sel = st.multiselect("💻 Equipamentos:", opcoes_equip)
        obs = st.text_area("📝 Observações:")
        
        if st.form_submit_button("✅ Confirmar Reserva Total", use_container_width=True):
            if prof_sel != "-- Selecione --":
                # Limpa nome do equipamento
                e_limpos = [e.split(" (")[0] for e in equip_sel]
                
                dados = {
                    "data_reserva": str(data_sel),
                    "periodo": aula_sel,
                    "professor": prof_sel,
                    "espaco": esp_sel,
                    "equipamentos": ", ".join(e_limpos) if e_limpos else "Nenhum",
                    "observacoes": obs
                }
                
                try:
                    supabase.table("reservas").insert(dados).execute()
                    st.success("🎉 Reserva salva com sucesso!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                except Exception as error:
                    st.error(f"Erro ao salvar: {error}")
            else:
                st.warning("Selecione um professor.")

elif menu_escolhido == "Fotograma":
    st.title("📸 Fotograma")
    st.info("Aqui permanece o código das fotos dos alunos.")
