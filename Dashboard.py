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
            "Boletim Final SIEPE"
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

if menu == "Análise de Dados":
    st.title("📊 Análise de Dados e Notas")
    
    try:
        res_raw = supabase.table("resultados_provas").select("aluno_id, questao_id, acertou").execute()
        res_alunos_base = supabase_alunos.table("alunos").select("id, turma, nome").execute()
        
        if res_raw.data and res_alunos_base.data:
            df_raw = pd.DataFrame(res_raw.data)
            df_alunos_base = pd.DataFrame(res_alunos_base.data)
            df_raw['aluno_id'] = df_raw['aluno_id'].astype(str)
            df_alunos_base['id'] = df_alunos_base['id'].astype(str)
            
            st.subheader("🎯 Visão Geral")
            col_k1, col_k2 = st.columns(2)
            col_k1.metric("Total de Respostas", len(df_raw))
            col_k2.metric("Alunos Participantes", df_raw['aluno_id'].nunique())
    except Exception as e:
        st.info("Aguardando dados de respostas...")

    st.divider()
    st.subheader("🏆 Desempenho por Aluno e Relatórios")
    
    res_p_modelos = supabase.table("modelos_prova").select("id, titulo, valor_questao, questoes_ids").order("id", desc=True).execute()
    
    if res_p_modelos.data:
        provas_dict = {p['titulo']: p for p in res_p_modelos.data}
        prova_nome = st.selectbox("Selecione a Prova para detalhar:", list(provas_dict.keys()))
        prova_obj = provas_dict[prova_nome]
        id_prova, valor_q = prova_obj['id'], float(prova_obj.get('valor_questao', 1.0))
        ids_questoes_prova = prova_obj.get('questoes_ids', [])

        res_res = supabase.table("resultados_provas").select("*").eq("prova_id", id_prova).execute()
        
        if res_res.data:
            df_res = pd.DataFrame(res_res.data)
            df_res['aluno_id'] = df_res['aluno_id'].astype(str)
            df_res['pontos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)
            
            df_notas = df_res.groupby('aluno_id').agg(total_acertos=('pontos', 'sum')).reset_index()
            df_notas['nota_final'] = df_notas['total_acertos'] * valor_q
            
            res_al = supabase_alunos.table("alunos").select("id, nome, turma").in_("id", df_notas['aluno_id'].tolist()).execute()
            df_alunos_nomes = pd.DataFrame(res_al.data)
            df_alunos_nomes['id'] = df_alunos_nomes['id'].astype(str)
            
            df_tela = pd.merge(df_alunos_nomes, df_notas, left_on="id", right_on="aluno_id")
            st.dataframe(df_tela[["nome", "turma", "total_acertos", "nota_final"]].sort_values("nome"), use_container_width=True)

            if st.button("📊 Gerar Relatório .XLSX Completo"):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    for turma in sorted(df_tela['turma'].unique()):
                        df_turma = df_tela[df_tela['turma'] == turma].copy()
                        df_turma.to_excel(writer, sheet_name=f"Turma {turma}", index=False)
                st.download_button("📥 Baixar Excel", output.getvalue(), f"Relatorio_{prova_nome}.xlsx")
        else:
            st.info("Sem respostas para esta avaliação.")

elif menu == "Cadastrar Questões":
    st.title("🖊️ Cadastro de Questões")
    # Lógica de cadastro manual e importação JSON...
    # (Mantenha seu código de importação JSON aqui, ele estava funcional)
    st.info("Use o Importador Flash para colagens em massa via IA.")

elif menu == "Biblioteca de Questões":
    if 'editando_id' not in st.session_state: st.session_state.editando_id = None
    
    if st.session_state.editando_id:
        if st.button("⬅️ Voltar"): 
            st.session_state.editando_id = None
            st.rerun()
        # Formulário de edição...
    else:
        st.title("📚 Biblioteca de Questões")
        # Filtros e Tabela de questões...

elif menu == "Gerar Modelo de Prova":
    st.title("📄 Gerar Nova Prova")
    # Lógica de criação de modelos de prova...

elif menu == "Provas Elaboradas":
    st.title("📂 Gerenciamento de Provas")
    # Listagem de provas com botões Editar, Ativar/Desativar e Excluir...

elif menu == "Lista de Matrículas":
    st.title("👥 Listas por Turma (PDF)")
    # Geração de PDF de frequência...

elif menu == "Central de Avisos":
    st.title("📲 Disparador de WhatsApp")
    if not WHATSAPP_LOCAL:
        st.warning("Biblioteca 'pywhatkit' não instalada para disparos.")
    # Lógica de envio em massa...

elif menu == "Diagnósticos IA":
    st.title("🤖 Importar Diagnósticos Pedagógicos")
    # Lógica de colagem do JSON da IA para feedback dos alunos...

elif menu == "Boletim Final SIEPE":
    st.title("🏫 Consolidação de Notas SIEPE")
    # Editor de notas AT1-AT5 e N2...