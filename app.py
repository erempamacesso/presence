import streamlit as st
from supabase import create_client, Client

# ==========================================
# 1. IMPORTAÇÃO DOS MÓDULOS (Onde as telas moram)
# ==========================================
from modulos.cenario_dia import exibir_cenario
from modulos.fotograma_aba import exibir_fotograma
from modulos.cadastro_aba import exibir_cadastro
from modulos.reservas_aba import exibir_reservas
from modulos.atualiza_alunos import exibir_importacao 


# ==========================================
# 2. CONFIGURAÇÃO GERAL DA PÁGINA
# ==========================================
st.set_page_config(page_title="EREM PAM - Chamada Escolar", layout="wide", page_icon="🏫")


# ==========================================
# 3. CONEXÃO COM O BANCO DE DADOS (SUPABASE)
# ==========================================
URL_SUPABASE = st.secrets["SUPABASE_URL"]
CHAVE_SUPABASE = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL_SUPABASE, CHAVE_SUPABASE)


# ==========================================
# 4. GERENCIADOR DE ESTADO (Para lembrar em qual página estamos)
# ==========================================
if 'pagina' not in st.session_state:
    st.session_state.pagina = 'cenario' # Define a página inicial ao abrir o app

def mudar_pagina(nome_pagina):
    st.session_state.pagina = nome_pagina


# ==========================================
# 5. MENU LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    # Usa a logo que vi nos seus arquivos!
    try:
        st.image("logo_erempam.png", use_column_width=True)
    except:
        st.title("🏫 EREM PAM")
        
    st.divider()
    
    # Botões de Navegação
    st.button("📊 Cenário do Dia", on_click=mudar_pagina, args=('cenario',), use_container_width=True)
    st.button("📸 Fotograma", on_click=mudar_pagina, args=('fotograma',), use_container_width=True)
    st.button("📝 Cadastro Manual", on_click=mudar_pagina, args=('cadastro',), use_container_width=True)
    st.button("📅 Reservas", on_click=mudar_pagina, args=('reservas',), use_container_width=True)
    
    st.divider()
    
    # 👇 O NOVO BOTÃO QUE CHAMA A TELA DE ATUALIZAÇÃO COM RELATÓRIO
    st.button("📤 Importar e Atualizar Alunos", on_click=mudar_pagina, args=('importacao',), type="primary", use_container_width=True)


# ==========================================
# 6. ROTEAMENTO DE PÁGINAS (O MAESTRO EM AÇÃO)
# ==========================================
if st.session_state.pagina == 'cenario':
    exibir_cenario(supabase)
    
elif st.session_state.pagina == 'fotograma':
    exibir_fotograma(supabase)
    
elif st.session_state.pagina == 'cadastro':
    exibir_cadastro(supabase)
    
elif st.session_state.pagina == 'reservas':
    # 👉 RESTAURAMOS AQUI OS PARÂMETROS QUE O SEU CÓDIGO ORIGINAL USAVA
    LISTA_PROF = ["Prof. Silva", "Profa. Maria", "Prof. Ricardo"]
    AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula"]
    ESPACOS = ["Auditório", "Laboratório", "Biblioteca", "Quadra", "Multimídia"]
    exibir_reservas(supabase, LISTA_PROF, AULAS, ESPACOS, 3, 2, 5)
    
elif st.session_state.pagina == 'importacao':
    # Quando clicar no botão primário, ele carrega toda a mágica que fizemos no atualiza_alunos.py
    exibir_importacao(supabase)
