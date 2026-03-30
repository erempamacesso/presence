import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import datetime
import time

# ==========================================
# 1. CONFIGURAÇÃO GERAL DA PÁGINA
# ==========================================
st.set_page_config(page_title="EREM PAM - Chamada Escolar", layout="wide", page_icon="🏫")

# ==========================================
# 2. IMPORTAÇÃO DOS MÓDULOS (Onde as telas moram)
# ==========================================
try:
    from modulos.cenario_dia import exibir_cenario
    from modulos.fotograma_aba import exibir_fotograma
    from modulos.cadastro_aba import exibir_cadastro
    from modulos.reservas_aba import exibir_reservas
    from modulos.atualiza_alunos import exibir_importacao
    from modulos.busca_ativa import exibir_busca_ativa
    from modulos.aee import exibir_painel_aee
    from modulos.ocorrencias_aba import exibir_ocorrencias
    # Importação do novo módulo da feira
    from modulos.gestao_feira import exibir_gestao_feira 
except Exception as e:
    st.error(f"🚨 Erro ao carregar os módulos das telas: {e}")
    st.stop()


    st.error(f"🚨 Erro ao carregar os módulos das telas: {e}")
    st.stop()

# ==========================================
# 3. CONEXÃO COM O BANCO DE DADOS (SUPABASE)
# ==========================================
try:
    # Aqui está o segredo ajustado: buscando com o _ALUNOS no final!
    URL_SUPABASE = st.secrets["SUPABASE_URL_ALUNOS"]
    CHAVE_SUPABASE = st.secrets["SUPABASE_KEY_ALUNOS"]
    supabase: Client = create_client(URL_SUPABASE, CHAVE_SUPABASE)
except KeyError as e:
    st.error(f"🚨 ALERTA: A chave {e} não foi encontrada no cofre do Streamlit!")
    st.stop()
except Exception as e:
    st.error(f"🚨 Erro ao conectar no Supabase: {e}")
    st.stop()

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
# 5. MENU LATERAL (SIDEBAR) - CORRIGIDO
# ==========================================
with st.sidebar:
    try:
        st.image("logo_erempam.png", use_container_width=True)
    except:
        st.title("🏫 EREM PAM")
        
    st.divider()
    
    # Botões de Navegação Padrão
    st.button("📊 Cenário do Dia", on_click=mudar_pagina, args=('cenario',), use_container_width=True)
    st.button("🔎 Busca Ativa", on_click=mudar_pagina, args=('busca_ativa',), use_container_width=True)
    st.button("📸 Fotograma", on_click=mudar_pagina, args=('fotograma',), use_container_width=True)
    st.button("🧩 AEE & Inclusão", on_click=mudar_pagina, args=('aee',), use_container_width=True)
    st.button("🚨 Ocorrências", on_click=mudar_pagina, args=('ocorrencias',), use_container_width=True)
    st.button("📝 Gestão de Alunos", on_click=mudar_pagina, args=('cadastro',), use_container_width=True)
    st.button("📅 Reservas", on_click=mudar_pagina, args=('reservas',), use_container_width=True)
    
    st.divider()

    # --- ESTILO LARANJA SEM EMOJI (DENTRO DA SIDEBAR) ---
    st.markdown("""
        <style>
        /* Estilo para o texto do botão */
        div[data-testid="stSidebar"] button p:contains("Criar um evento") {
            color: white !important;
            font-weight: bold !important;
        }
        
        /* Estilo para o corpo do botão */
        div[data-testid="stSidebar"] button:has(p:contains("Criar um evento")) {
            background-color: #FF8000 !important;
            border: none !important;
            transition: 0.3s;
        }

        /* Efeito Hover */
        div[data-testid="stSidebar"] button:has(p:contains("Criar um evento")):hover {
            background-color: #e67300 !important;
            transform: scale(1.02);
        }
        </style>
    """, unsafe_allow_html=True)

    # Botão Laranja (agora sincronizado com o CSS)
    st.button("Criar um evento", on_click=mudar_pagina, args=('gestao_feira',), use_container_width=True)
    
    # Botão de Importação Verde (Primary)
    st.button("📤 Importar e Atualizar Alunos", on_click=mudar_pagina, args=('importacao',), type="primary", use_container_width=True)

# ==========================================
# 6. INJEÇÃO DE CÓDIGO PARA CELULAR (Mantido)
# ==========================================
if st.session_state.fechar_menu:
    js_fechar_menu = '''
    <script>
        setTimeout(function() {
            var doc = window.parent.document;
            var btn_fechar = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
            if (btn_fechar) btn_fechar.click();
        }, 300);
    </script>
    '''
    components.html(js_fechar_menu, width=0, height=0)
    st.session_state.fechar_menu = False

# ==========================================
# ROTEAMENTO DE PÁGINAS (O MAESTRO)
# ==========================================

if st.session_state.pagina == 'cenario':
    exibir_cenario(supabase)

elif st.session_state.pagina == 'busca_ativa':
    exibir_busca_ativa(supabase)
    
elif st.session_state.pagina == 'fotograma':
    exibir_fotograma(supabase)

elif st.session_state.pagina == 'aee':
    exibir_painel_aee(supabase)

elif st.session_state.pagina == 'ocorrencias':
    exibir_ocorrencias(supabase)
    
elif st.session_state.pagina == 'cadastro':
    exibir_cadastro(supabase)
    
elif st.session_state.pagina == 'reservas':
    # Lógica de busca de professores para reservas
    try:
        res_prof = supabase.table("assinaturas").select("nome").execute()
        LISTA_PROF = [linha["nome"] for linha in res_prof.data]
    except:
        LISTA_PROF = ["Erro ao carregar professores"]

    AULAS = [f"{i}ª Aula" for i in range(1, 10)] 
    ESPACOS = ["Auditório", "Laboratório", "Biblioteca", "Quadra", "Multimídia", "Sala de Vídeo"]
    exibir_reservas(supabase, LISTA_PROF, AULAS, ESPACOS, 3, 2, 9)
    
elif st.session_state.pagina == 'importacao':
    exibir_importacao(supabase)

elif st.session_state.pagina == 'gestao_feira':
    exibir_gestao_feira(supabase)    