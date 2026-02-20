import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# 1. CONFIGURAÇÃO DA PÁGINA (Aba do Navegador)
# Tenta carregar a logo oficial para a aba, senão usa o padrão
try:
    if os.path.exists("logo_erempam.png"):
        st.set_page_config(
            page_title="SIAGE - Sistema Auxiliar de Gestão Escolar", 
            page_icon="logo_erempam.png", 
            layout="wide"
        )
    else:
        st.set_page_config(
            page_title="SIAGE - Sistema Auxiliar de Gestão Escolar", 
            page_icon="🏫", 
            layout="wide"
        )
except:
    st.set_page_config(page_title="SIAGE", page_icon="🏫", layout="wide")

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

# 4. ESTILIZAÇÃO CSS (BOTOES E LAYOUT)
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 65px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 10px;
    }
    .block-container {
        padding-top: 1.5rem;
    }
    /* Estilo para o título principal */
    .titulo-siage {
        font-size: 42px !important;
        font-weight: 800;
        margin-bottom: 0px;
    }
    .subtitulo-siage {
        font-size: 18px !important;
        color: #555;
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

# Botão de Voltar (Sempre disponível nas páginas internas)
if st.session_state.pagina != 'home':
    if st.button("⬅️ VOLTAR AO MENU PRINCIPAL"):
        mudar_pagina('home')
    st.divider()

# RENDERIZAÇÃO
if st.session_state.pagina == 'home':
    # --- CABEÇALHO COM LOGO E NOME COMPLETO ---
    col_l, col_t = st.columns([1, 3])
    
    with col_l:
        if os.path.exists("logo_erempam.png"):
            st.image("logo_erempam.png", width=150)
        else:
            st.title("🏫")
            
    with col_t:
        st.write("") # Ajuste de altura
        st.markdown('<p class="titulo-siage">SIAGE</p>', unsafe_allow_html=True)
        st.markdown('<p class="subtitulo-siage">Sistema Auxiliar de Gestão Escolar</p>', unsafe_allow_html=True)
    
    st.write("---")
    
    # Grid de Botões Principais
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

# Chamada dos módulos internos
elif st.session_state.pagina == 'cenario_dia':
    exibir_cenario(supabase)

elif st.session_state.pagina == 'reservas':
    LISTA_PROF = ["Prof. Silva", "Profa. Maria", "Prof. Ricardo"]
    AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula"]
    ESPACOS = ["Auditório", "Laboratório", "Biblioteca", "Quadra", "Multimídia"]
    exibir_reservas(supabase, LISTA_PROF, AULAS, ESPACOS, 3, 2, 5)

elif st.session_state.pagina == 'fotograma':
    exibir_fotograma(supabase)

elif st.session_state.pagina == 'cadastro':
    exibir_cadastro(supabase)

elif st.session_state.pagina == 'importacao':
    exibir_importacao(supabase)

