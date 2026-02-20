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

# --- DADOS MESTRES ATUALIZADOS ---
LISTA_PROFESSORES = [
    "ALEXANDRO", "AUGUSTO", "BRUNO LARDIÃO", "CAMILA", "CATARINA", 
    "CELSO GOMES", "CLEBSON", "EDINEI NOVAIS", "EDVÂNIA", "GABRIEL", 
    "GELSON", "HUGO", "IGOR", "JACKSON", "JAMES", "JÉSSICA VITORINO", 
    "LILIAN JORDÃO", "LYLIAN CABRAL", "PATRICIA", "PEDRO", "RAFAEL", 
    "ROBERTA", "SÉRGIO", "SEVERINO", "TYAGO", "VIVIANE"
]

AULAS_OPCOES = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]
ESPACOS_TOTAIS = ["Auditório", "Laboratório de Ciências", "Laboratório de Informática", "Biblioteca", "Refeitório", "Quadra", "Nenhum (Só Equipamento)"]

# Estoque Real
TOTAL_DATASHOWS = 5
TOTAL_CAIXAS = 3
TOTAL_MICROFONES = 2

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
if menu_escolhido == "Reservas":
    st.title("📅 Sistema de Reservas")
    
    # ETAPA 1: DATA E AULAS
    col1, col2 = st.columns([1, 2])
    with col1:
        # Formato de exibição da data ajustado para Brasil
        data_sel = st.date_input("Data da Reserva:", value=date.today(), format="DD/MM/YYYY")
    
    with col2:
        st.write("Selecione as Aulas:")
        col_pills, col_all = st.columns([3, 1])
        with col_all:
            selecionar_tudo = st.checkbox("Dia Inteiro")
        
        with col_pills:
            default_aulas = AULAS_OPCOES if selecionar_tudo else []
            aulas_selecionadas = st.pills(
                "Aulas:", 
                options=AULAS_OPCOES, 
                selection_mode="multi",
                default=default_aulas,
                label_visibility="collapsed"
            )

    # BUSCA RESERVAS PARA CÁLCULO DE DISPONIBILIDADE
    reservas_dia = []
    if aulas_selecionadas:
        try:
            res = supabase.table("reservas").select("*").eq("data_reserva", str(data_sel)).in_("periodo", aulas_selecionadas).execute()
            reservas_dia = res.data
        except:
            pass

    # LÓGICA DE ESPAÇOS E EQUIPAMENTOS
    espacos_ocupados = [r['espaco'] for r in reservas_dia if r.get('espaco') and r['espaco'] != "Nenhum (Só Equipamento)"]
    espacos_disponiveis = [e for e in ESPACOS_TOTAIS if e not in espacos_ocupados]

    # Contagem de Equipamentos
    d_usados = sum(1 for r in reservas_dia if r.get('equipamentos') and "Datashow" in r['equipamentos'])
    c_usadas = sum(1 for r in reservas_dia if r.get('equipamentos') and "Caixa de Som" in r['equipamentos'])
    m_usados = sum(1 for r in reservas_dia if r.get('equipamentos') and "Microfone" in r['equipamentos'])
    
    opcoes_equip = []
    if (TOTAL_DATASHOWS - d_usados) > 0: opcoes_equip.append(f"Datashow ({TOTAL_DATASHOWS - d_usados} disponíveis)")
    if (TOTAL_CAIXAS - c_usadas) > 0: opcoes_equip.append(f"Caixa de Som ({TOTAL_CAIXAS - c_usadas} disponíveis)")
    if (TOTAL_MICROFONES - m_usados) > 0: opcoes_equip.append(f"Microfone ({TOTAL_MICROFONES - m_usados} disponíveis)")

    st.divider()

    # ETAPA 2: FORMULÁRIO
    with st.form("form_reserva"):
        prof_sel = st.selectbox("👩‍🏫 Professor(a):", ["-- Selecione --"] + sorted(LISTA_PROFESSORES))
        
        # Seleção de Espaço
        if not espacos_disponiveis:
            st.error("⚠️ Todos os espaços ocupados nestas aulas!")
            esp_final = "Lotado"
        else:
            esp_final = st.selectbox("📍 Espaço:", espacos_disponiveis)
        
        # Seleção de Equipamentos
        if not opcoes_equip:
            st.warning("💻 Equipamentos: Nenhum disponível")
            equip_sel = []
        else:
            equip_sel = st.multiselect("💻 Equipamentos (Opcional):", opcoes_equip)
            
        obs = st.text_area("📝 Observações:")
        
        if st.form_submit_button("Confirmar Reserva", use_container_width=True):
            if prof_sel != "-- Selecione --" and aulas_selecionadas:
                e_limpos = [e.split(" (")[0] for e in equip_sel]
                
                try:
                    for aula in aulas_selecionadas:
                        dados = {
                            "data_reserva": str(data_sel),
                            "periodo": aula,
                            "professor": prof_sel,
                            "espaco": esp_final,
                            "equipamentos": ", ".join(e_limpos) if e_limpos else "Nenhum",
                            "observacoes": obs
                        }
                        supabase.table("reservas").insert(dados).execute()
                    
                    st.success(f"🎉 Reserva realizada para {len(aulas_selecionadas)} aula(s)!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Certifique-se de selecionar seu nome e as aulas desejadas.")

# Manter as outras telas (Frequência, Fotograma...) conforme o original
else:
    st.title(f"Tela: {menu_escolhido}")
    st.info("O conteúdo desta aba permanece inalterado.")
