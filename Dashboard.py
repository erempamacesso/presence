import streamlit as st
from supabase import create_client
from streamlit_quill import st_quill
import plotly.express as px
import pandas as pd
import json
import pytz 
from fpdf import FPDF
import base64
import re
from datetime import datetime
import time
import unicodedata
import io
from streamlit_option_menu import option_menu

# Importando nossas telas modulares
from telas.boletim_siepe import mostrar_tela_boletim
from telas.analise_dados import mostrar_tela_analise
from telas.cadastrar_questoes import mostrar_tela_cadastrar_questoes
from telas.biblioteca_questoes import mostrar_tela_biblioteca
from telas.gerar_modelo_prova import mostrar_tela_gerar_modelo
from telas.provas_elaboradas import mostrar_tela_provas_elaboradas
from telas.lista_matriculas import mostrar_tela_lista_matriculas
from telas.diagnosticos_ia import mostrar_tela_diagnosticos

# --- PROTEÇÃO PARA O WHATSAPP ---
try:
    import pywhatkit as kit
    WHATSAPP_LOCAL = True
except ImportError:
    WHATSAPP_LOCAL = False
              
# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão EREMPAM - Provas", layout="wide")

# --- 2. CONEXÃO COM SUPABASE ---
URL_P = st.secrets["SUPABASE_URL_PROVAS"]
KEY_P = st.secrets["SUPABASE_KEY_PROVAS"]
supabase = create_client(URL_P, KEY_P)

URL_A = st.secrets["SUPABASE_URL_ALUNOS"]
KEY_A = st.secrets["SUPABASE_KEY_ALUNOS"]
supabase_alunos = create_client(URL_A, KEY_A)

# --- FUNÇÃO DE SINCRONIZAÇÃO DE NOTAS ---
def sincronizar_atividades_online(turma_sel, unidade_sel, atividade_id_origem):
    """
    Busca notas na tabela 'resultados' e salva na 'notas_atividades' coluna AT1
    """
    try:
        # 1. Busca os resultados da atividade online
        res = supabase.table("resultados").select("aluno_id, nota").eq("atividade_id", atividade_id_origem).execute()
        
        if not res.data:
            st.warning(f"Nenhum resultado encontrado para a atividade {atividade_id_origem}")
            return

        # 2. Prepara os dados para o Upsert na nova tabela
        dados_upsert = []
        for r in res.data:
            dados_upsert.append({
                "aluno_id": r["aluno_id"],
                "turma": turma_sel,
                "unidade": unidade_sel,
                "at1": float(r["nota"])
            })
        
        # 3. Faz o Upsert (Se o aluno já tiver linha lá, ele só atualiza a AT1)
        supabase.table("notas_atividades").upsert(dados_upsert, on_conflict="aluno_id, unidade").execute()
        st.success(f"✅ {len(dados_upsert)} notas sincronizadas com sucesso para AT1!")
        
    except Exception as e:
        st.error(f"Erro na sincronização: {e}")

# --- 3. SISTEMA DE LOGIN (ESTADO) ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = True # Mudar para False se desejar tela de login real

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito")
    senha = st.text_input("Digite a senha de acesso:", type="password")
    if st.button("Entrar"):
        if senha == st.secrets.get("SENHA_SISTEMA", "123"):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# --- 4. MENU LATERAL ---
with st.sidebar:
    st.title("🎮 Painel do Professor")
    
    menu = option_menu(
        menu_title="Navegação",  
        options=[
            "Análise de Dados", 
            "Cadastrar Questões", 
            "Biblioteca de Questões", 
            "Gerar Modelo de Prova",
            "Provas Elaboradas",
            "Lista de Matrículas",
            "Central de Avisos",
            "Diagnósticos IA",
            "Boletim Siepe"
        ],
        icons=[
            "bar-chart-fill", "pencil-square", "book", "file-earmark-text",
            "folder-check", "people-fill", "bell-fill", "robot", "bank"
        ],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#ff9800", "font-size": "18px"}, 
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px"},
            "nav-link-selected": {"background-color": "#4CAF50"}, 
        }
    )
    st.sidebar.divider()
    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# --- 5. LÓGICA DAS PÁGINAS ---
# Agora sim, totalmente fora da sidebar (encostado na parede esquerda) e começando com 'if'

if menu == "Análise de Dados":
    mostrar_tela_analise(supabase, supabase_alunos)

elif menu == "Cadastrar Questões":
    mostrar_tela_cadastrar_questoes(supabase)

elif menu == "Biblioteca de Questões":
    mostrar_tela_biblioteca(supabase)
    
elif menu == "Gerar Modelo de Prova":
    mostrar_tela_gerar_modelo(supabase)

elif menu == "Provas Elaboradas":
    mostrar_tela_provas_elaboradas(supabase)

elif menu == "Lista de Matrículas":
    mostrar_tela_lista_matriculas(supabase_alunos)

elif menu == "Central de Avisos":
    st.title("📲 Disparador de WhatsApp")
    if not WHATSAPP_LOCAL:
        st.warning("Biblioteca 'pywhatkit' não instalada para disparos.")
    # Lógica de envio em massa...

elif menu == "Diagnósticos IA":
    mostrar_tela_diagnosticos(supabase)

elif menu == "Boletim Final SIEPE":
    mostrar_tela_boletim(supabase, supabase_alunos)