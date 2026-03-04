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
from modulos.busca_ativa import exibir_busca_ativa
# 👇 A NOVA PEÇA PARA O AEE
from modulos.aee import exibir_painel_aee

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
    st.button("🔎 Busca Ativa", on_click=mudar_pagina, args=('busca_ativa',), use_container_width=True)
    st.button("📸 Fotograma", on_click=mudar_pagina, args=('fotograma',), use_container_width=True)
    
    # 👇 O NOVO BOTÃO DA INCLUSÃO
    st.button("🧩 AEE & Inclusão", on_click=mudar_pagina, args=('aee',), use_container_width=True)
    
    st.button("📝 Gestão de Alunos", on_click=mudar_pagina, args=('cadastro',), use_container_width=True)
    st.button("📅 Reservas", on_click=mudar_pagina, args=('reservas',), use_container_width=True)
    
    st.divider()
    
    st.button("📤 Importar e Atualizar Alunos", on_click=mudar_pagi# ==========================================
# 6. INJEÇÃO DE CÓDIGO PARA CELULAR (Fecha o Menu)
# ==========================================
if st.session_state.fechar_menu:
    js_fechar_menu = '''
    <script>
        setTimeout(function() {
            var parentDoc = window.parent.document;
            
            // Tenta achar o botão de recolher (X) do modo mobile e "clicar" nele
            var botoesSidebar = parentDoc.querySelectorAll('section[data-testid="stSidebar"] button');
            if (botoesSidebar && botoesSidebar.length > 0) {
                // O botão de fechar geralmente é o primeiro botão renderizado no header do sidebar
                botoesSidebar[0].click();
            }

            // Plano B: Dispara o ESC com todas as propriedades de evento real
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
            
        }, 150); // Delay milissegundos para garantir que o React do Streamlit atualizou
    </script>
    '''
    components.html(js_fechar_menu, width=0, height=0)
    
    # Desliga o gatilho para não ficar rodando toda hora
    st.session_state.fechar_menu = Falsena, args=('importacao',), type="primary", use_container_width=True)


