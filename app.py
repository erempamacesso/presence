import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv

# 1. IMPORTAÇÃO DOS MÓDULOS (Certifique-se que os arquivos existem na pasta modulos)
from modulos.frequencia_aba import exibir_frequencia
from modulos.reservas_aba import exibir_reservas
from modulos.fotograma_aba import exibir_fotograma
from modulos.cadastro_aba import exibir_cadastro
from modulos.importacao_aba import exibir_importacao

# 2. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="SIGPAM - EREMPAM", layout="wide", initial_sidebar_state="collapsed")

# 3. CONEXÃO COM O BANCO (SUPABASE)
@st.cache_resource
def init_connection():
    load_dotenv()
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_connection()

# --- DADOS MESTRES (Para o módulo de Reservas) ---
LISTA_PROFESSORES = ["ALEXANDRO", "AUGUSTO", "BRUNO LARDIÃO", "CAMILA", "CATARINA", "CELSO GOMES", "CLEBSON", "EDINEI NOVAIS", "EDVÂNIA", "GABRIEL", "GELSON", "HUGO", "IGOR", "JACKSON", "JAMES", "JÉSSICA VITORINO", "LILIAN JORDÃO", "LYLIAN CABRAL", "PATRICIA", "PEDRO", "RAFAEL", "ROBERTA", "SÉRGIO", "SEVERINO", "TYAGO", "VIVIANE"]
AULAS_OPCOES = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]
ESPACOS_TOTAIS = ["Auditório", "Laboratório de Ciências", "Laboratório de Informática", "Biblioteca", "Refeitório", "Quadra", "Nenhum (Só Equipamento)"]

# --- CONTROLE DE NAVEGAÇÃO ---
if 'pagina' not in st.session_state:
    st.session_state.pagina = 'home'

def mudar_pagina(nome_pagina):
    st.session_state.pagina = nome_pagina
    st.rerun()

# ==================================================
# 🏠 TELA INICIAL: MENU DE BOTÕES GRANDES
# ==================================================
if st.session_state.pagina == 'home':
    st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>SIGPAM - EREMPAM</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Gestão Integrada Escolar | 2026</p>", unsafe_allow_html=True)
    st.divider()

    # Layout de Botões (2 colunas para ficar grande no celular)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 FREQUÊNCIA DIÁRIA", use_container_width=True, height=150):
            mudar_pagina('frequencia')
            
        if st.button("📸 FOTOGRAMA (MAPA)", use_container_width=True, height=150):
            mudar_pagina('fotograma')

    with col2:
        if st.button("📅 RESERVAS", use_container_width=True, height=150):
            mudar_pagina('reservas')
            
        if st.button("👤 GESTÃO/CADASTRO", use_container_width=True, height=150):
            mudar_pagina('cadastro')
    
    st.divider()
    # Botão de Importação isolado na parte inferior
    if st.button("📤 IMPORTAÇÃO (ANUAL)", use_container_width=True):
        mudar_pagina('importacao')

# ==================================================
# 🔄 LÓGICA DE NAVEGAÇÃO (CHAMADA DOS MÓDULOS)
# ==================================================

# 1. FREQUÊNCIA
elif st.session_state.pagina == 'frequencia':
    if st.button("⬅️ Voltar ao Início"): mudar_pagina('home')
    exibir_frequencia(supabase)

# 2. RESERVAS
elif st.session_state.pagina == 'reservas':
    if st.button("⬅️ Voltar ao Início"): mudar_pagina('home')
    # Passa as variáveis mestre para o módulo
    exibir_reservas(supabase, LISTA_PROFESSORES, AULAS_OPCOES, ESPACOS_TOTAIS, 5, 3, 2)

# 3. FOTOGRAMA
elif st.session_state.pagina == 'fotograma':
    if st.button("⬅️ Voltar ao Início"): mudar_pagina('home')
    exibir_fotograma(supabase)

# 4. CADASTRO / GESTÃO
elif st.session_state.pagina == 'cadastro':
    if st.button("⬅️ Voltar ao Início"): mudar_pagina('home')
    exibir_cadastro(supabase)

# 5. IMPORTAÇÃO
elif st.session_state.pagina == 'importacao':
    if st.button("⬅️ Voltar ao Início"): mudar_pagina('home')
    exibir_importacao(supabase)
