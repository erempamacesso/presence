import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Importação dos módulos (Certifique-se que os nomes dos arquivos na pasta /modulos estão corretos)
from modulos.cenario_dia import exibir_cenario
from modulos.reservas_aba import exibir_reservas
from modulos.fotograma_aba import exibir_fotograma
from modulos.cadastro_aba import exibir_cadastro
from modulos.importacao_aba import exibir_importacao

# Configurações de Segurança e Conexão
load_dotenv()
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Configuração da Página para Celular e Desktop
st.set_page_config(page_title="SIGPAM - Gestão Escolar", page_icon="📊", layout="wide")

# Estilização CSS para botões grandes e organizados
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 60px;
        border-radius: 10px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Lógica de Navegação
if 'pagina' not in st.session_state:
    st.session_state.pagina = 'home'

def mudar_pagina(nome):
    st.session_state.pagina = nome
    st.rerun()

# --- INTERFACE PRINCIPAL ---

# Botão de Voltar (Sempre visível exceto na Home)
if st.session_state.pagina != 'home':
    if st.button("⬅️ Voltar para o Menu Principal"):
        mudar_pagina('home')

# Renderização das Páginas
if st.session_state.pagina == 'home':
    st.title("🏫 SIGPAM - Sistema de Gestão")
    st.subheader("Painel de Controle do Diretor")
    
    # Grid de Botões Principais
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 CENÁRIO DO DIA", help="Censo em tempo real e termômetro de faltas"):
            mudar_pagina('cenario_dia')
            
        if st.button("📸 FOTOGRAMA", help="Visualizar mapa de sala com fotos"):
            mudar_pagina('fotograma')

        if st.button("📅 RESERVAS", help="Agendamentos de espaços e equipamentos"):
            mudar_pagina('reservas')

    with col2:
        if st.button("👤 GESTÃO DE ALUNOS", help="Cadastro e upload de fotos individuais"):
            mudar_pagina('cadastro')
            
        if st.button("📤 IMPORTAR DADOS", help="Subir lista de alunos via CSV/Excel"):
            mudar_pagina('importacao')

elif st.session_state.pagina == 'cenario_dia':
    exibir_cenario(supabase)

elif st.session_state.pagina == 'reservas':
    # Passando os parâmetros necessários para o módulo de reservas
    LISTA_PROFESSORES = ["Prof. Silva", "Profa. Maria", "Prof. Ricardo"] # Pode vir do banco depois
    AULAS_OPCOES = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula"]
    ESPACOS = ["Auditório", "Laboratório", "Biblioteca", "Quadra", "Sala Multimídia"]
    exibir_reservas(supabase, LISTA_PROFESSORES, AULAS_OPCOES, ESPACOS, 3, 2, 5)

elif st.session_state.pagina == 'fotograma':
    exibir_fotograma(supabase)

elif st.session_state.pagina == 'cadastro':
    exibir_cadastro(supabase)

elif st.session_state.pagina == 'importacao':
    exibir_importacao(supabase)
