import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from PIL import Image

# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira coisa!)
# Ele vai tentar carregar seu favicon.ico, se não achar, usa o emoji.
try:
    st.set_page_config(
        page_title="SIGPAM - Gestão Escolar", 
        page_icon="favicon.ico", 
        layout="wide"
    )
except:
    st.set_page_config(page_title="SIGPAM", page_icon="🏫", layout="wide")

# 2. CONEXÃO SUPABASE
load_dotenv()
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 3. IMPORTAÇÃO DOS MÓDULOS
from modulos.cenario_dia import exibir_cenario
from modulos.reservas_aba import exibir_reservas
from modulos.fotograma_aba import exibir_fotograma
from modulos.cadastro_aba import exibir_cadastro
from modulos.importacao_aba import exibir_importacao

# 4. ESTILIZAÇÃO CSS (IDENTIDADE VISUAL)
st.markdown("""
    <style>
    /* Botões do Menu Principal */
    div.stButton > button {
        width: 100%;
        height: 70px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 18px;
        margin-bottom: 15px;
        transition: 0.3s;
    }
    /* Estilo do botão de Voltar */
    [data-testid="stBaseButton-secondary"] {
        height: 40px !important;
        background-color: #f0f2f6;
    }
    </style>
""", unsafe_allow_html=True)

# 5. LÓGICA DE NAVEGAÇÃO
if 'pagina' not in st.session_state:
    st.session_state.pagina = 'home'

def mudar_pagina(nome):
    st.session_state.pagina = nome
    st.rerun()

# --- INTERFACE ---

# Botão de Voltar (Sempre visível exceto na Home)
if st.session_state.pagina != 'home':
    if st.button("⬅️ VOLTAR AO MENU"):
        mudar_pagina('home')
    st.divider()

# RENDERIZAÇÃO
if st.session_state.pagina == 'home':
    # Cabeçalho com Logo
    col_l, col_t = st.columns([1, 4])
    with col_l:
        try:
            # Tenta carregar a logo (favicon ou logo_escola.png)
            st.image("favicon.ico", width=100) 
        except:
            st.write("🏫")
    with col_t:
        st.title("SIGPAM")
        st.subheader("Painel de Controle do Diretor")
    
    st.write("---")
    
    # Grid de Botões (Mobile Friendly)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 CENÁRIO DO DIA"):
            mudar_pagina('cenario_dia')
            
        if st.button("📸 FOTOGRAMA"):
            mudar_pagina('fotograma')

        if st.button("📅 RESERVAS"):
            mudar_pagina('reservas')

    with col2:
        if st.button("👤 GESTÃO DE ALUNOS"):
            mudar_pagina('cadastro')
            
        if st.button("📤 IMPORTAR DADOS"):
            mudar_pagina('importacao')

elif st.session_state.pagina == 'cenario_dia':
    exibir_cenario(supabase)

elif st.session_state.pagina == 'reservas':
    LISTA_PROFESSORES = ["Prof. Silva", "Profa. Maria", "Prof. Ricardo"]
    AULAS_OPCOES = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula"]
    ESPACOS = ["Auditório", "Laboratório", "Biblioteca", "Quadra", "Sala Multimídia"]
    exibir_reservas(supabase, LISTA_PROFESSORES, AULAS_OPCOES, ESPACOS, 3, 2, 5)

elif st.session_state.pagina == 'fotograma':
    exibir_fotograma(supabase)

elif st.session_state.pagina == 'cadastro':
    exibir_cadastro(supabase)

elif st.session_state.pagina == 'importacao':
    exibir_importacao(supabase)
