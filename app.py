import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURAÇÃO GERAL DA PÁGINA (Sempre no topo!)
# ==========================================
st.set_page_config(page_title="EREM PAM - Chamada Escolar", layout="wide", page_icon="🏫")

# ==========================================
# 2. IMPORTAÇÃO DOS MÓDULOS E BANCO
# ==========================================
try:
    from modulos.cenario_dia import exibir_cenario
    from modulos.fotograma_aba import exibir_fotograma
    from modulos.cadastro_aba import exibir_cadastro
    from modulos.reservas_aba import exibir_reservas
    from modulos.atualiza_alunos import exibir_importacao
    from modulos.busca_ativa import exibir_busca_ativa
    from modulos.aee import exibir_painel_aee
except Exception as e:
    st.error(f"🚨 Erro ao carregar os módulos das telas: {e}")
    st.stop()

try:
    URL_SUPABASE = st.secrets["SUPABASE_URL"]
    CHAVE_SUPABASE = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL_SUPABASE, CHAVE_SUPABASE)
except Exception as e:
    st.error(f"🚨 Erro ao conectar no Supabase. Verifique os secrets: {e}")
    st.stop()

# ==========================================
# 3. GERENCIADOR DE ESTADO
# ==========================================
if 'pagina' not in st.session_state:
    st.session_state.pagina = 'cenario'

def mudar_pagina(nome_pagina):
    st.session_state.pagina = nome_pagina
    # O comando de fechar_menu foi desativado temporariamente para garantir a visualização

# ==========================================
# 4. MENU LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    try:
        # Troquei use_column_width por use_container_width (o Streamlit prefere assim agora)
        st.image("logo_erempam.png", use_container_width=True) 
    except:
        st.title("🏫 EREM PAM")
        
    st.divider()
    
    # Botões de Navegação
    st.button("📊 Cenário do Dia", on_click=mudar_pagina, args=('cenario',), use_container_width=True)
    st.button("🔎 Busca Ativa", on_click=mudar_pagina, args=('busca_ativa',), use_container_width=True)
    st.button("📸 Fotograma", on_click=mudar_pagina, args=('fotograma',), use_container_width=True)
    st.button("🧩 AEE & Inclusão", on_click=mudar_pagina, args=('aee',), use_container_width=True)
    st.button("📝 Gestão de Alunos", on_click=mudar_pagina, args=('cadastro',), use_container_width=True)
    st.button("📅 Reservas", on_click=mudar_pagina, args=('reservas',), use_container_width=True)
    
    st.divider()
    
    st.button("📤 Importar Alunos", on_click=mudar_pagina, args=('importacao',), type="primary", use_container_width=True)

# ==========================================
# 5. ROTEAMENTO DE PÁGINAS (O MAESTRO EM AÇÃO)
# ==========================================
if st.session_state.pagina == 'cenario':
    exibir_cenario(supabase)
elif st.session_state.pagina == 'busca_ativa':
    exibir_busca_ativa(supabase)
elif st.session_state.pagina == 'fotograma':
    exibir_fotograma(supabase)
elif st.session_state.pagina == 'aee':
    exibir_painel_aee(supabase)
elif st.session_state.pagina == 'cadastro':
    exibir_cadastro(supabase)
elif st.session_state.pagina == 'reservas':
    LISTA_PROF = ["Prof. Silva", "Profa. Maria", "Prof. Ricardo"]
    AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula"]
    ESPACOS = ["Auditório", "Laboratório", "Biblioteca", "Quadra", "Multimídia"]
    exibir_reservas(supabase, LISTA_PROF, AULAS, ESPACOS, 3, 2, 5)
elif st.session_state.pagina == 'importacao':
    exibir_importacao(supabase)