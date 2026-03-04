import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURAÇÃO GERAL DA PÁGINA
# ==========================================
st.set_page_config(page_title="EREM PAM - Chamada Escolar", layout="wide", page_icon="🏫")

# ==========================================
# 2. IMPORTAÇÃO DOS MÓDULOS (Onde as telas moram)
# ==========================================
from modulos.cenario_dia import exibir_cenario
from modulos.fotograma_aba import exibir_fotograma
from modulos.cadastro_aba import exibir_cadastro
from modulos.reservas_aba import exibir_reservas
from modulos.atualiza_alunos import exibir_importacao
from modulos.busca_ativa import exibir_busca_ativa
from modulos.aee import exibir_painel_aee

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

if 'fechar_menu' not in st.session_state:
    st.session_state.fechar_menu = False

def mudar_pagina(nome_pagina):
    st.session_state.pagina = nome_pagina
    st.session_state.fechar_menu = True # Liga o gatilho para recolher o menu no celular

# ==========================================
# 5. MENU LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    try:
        st.image("logo_erempam.png", use_column_width=True)
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
    
    st.button("📤 Importar e Atualizar Alunos", on_click=mudar_pagina, args=('importacao',), type="primary", use_container_width=True)

# ==========================================
# 6. INJEÇÃO DE CÓDIGO PARA CELULAR (Fecha o Menu)
# ==========================================
if st.session_state.fechar_menu:
    js_fechar_menu = '''
    <script>
        setTimeout(function() {
            var parentDoc = window.parent.document;
            
            // Tenta achar o botão "X" invisível (Close sidebar) do Streamlit no modo mobile
            var botoes = parentDoc.querySelectorAll('button');
            for (var i = 0; i < botoes.length; i++) {
                if (botoes[i].getAttribute('aria-label') === 'Close sidebar') {
                    botoes[i].click();
                    break;
                }
            }

            // Plano B: Dispara o ESC 
            var escEvent = new KeyboardEvent('keydown', {
                key: 'Escape',
                code: 'Escape',
                keyCode: 27,
                which: 27,
                bubbles: true,
                cancelable: true,
                composed: true
            });
            parentDoc.dispatchEvent(escEvent);
            
        }, 150); // Delay milissegundos para garantir a renderização
    </script>
    '''
    components.html(js_fechar_menu, width=0, height=0)
    
    # Desliga o gatilho
    st.session_state.fechar_menu = False

# ==========================================
# 7. ROTEAMENTO DE PÁGINAS (O MAESTRO EM AÇÃO)
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
