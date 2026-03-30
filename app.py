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
try:
    from modulos.cenario_dia import exibir_cenario
    from modulos.fotograma_aba import exibir_fotograma
    from modulos.cadastro_aba import exibir_cadastro
    from modulos.reservas_aba import exibir_reservas
    from modulos.atualiza_alunos import exibir_importacao
    from modulos.busca_ativa import exibir_busca_ativa
    from modulos.aee import exibir_painel_aee
    from modulos.ocorrencias_aba import exibir_ocorrencias # 👈 NOSSO NOVO MÓDULO AQUI!
except Exception as e:
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
# 5. MENU LATERAL (SIDEBAR) - ATUALIZADO
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

   # --- BOTÃO LARANJA DA FEIRA (Atualizado para o novo nome) ---
    st.markdown("""
        <style>
        /* Mudamos de 'Feira' para 'Cria um evento' para o CSS achar o botão */
        div[data-testid="stSidebar"] button:has(div:contains("Cria um evento")) {
            background-color: #FF8000 !important;
            color: white !important;
            border: none !important;
            font-weight: bold !important;
        }
        div[data-testid="stSidebar"] button:has(div:contains("Cria um evento")):hover {
            background-color: #e67300 !important;
            border: 1px solid white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # O botão com o nome exato que o CSS vai procurar
    st.button("🎪 Cria um evento", on_click=mudar_pagina, args=('gestao_feira',), use_container_width=True)
    
    # Botão de Importação (Abaixo do Laranja)
    st.button("📤 Importar e Atualizar Alunos", on_click=mudar_pagina, args=('importacao',), type="primary", use_container_width=True)

# ==========================================
# 6. INJEÇÃO DE CÓDIGO PARA CELULAR (Fecha o Menu)
# ==========================================
if st.session_state.fechar_menu:
    js_fechar_menu = '''
    <script>
        setTimeout(function() {
            var doc = window.parent.document;
            
            // Estratégia 1: Procura exatamente a tag oficial do botão de fechar do Streamlit
            var btn_fechar = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
            
            if (btn_fechar) {
                btn_fechar.click();
            } else {
                // Estratégia 2: Se a versão for um pouco mais antiga, clica no primeiro botão do cabeçalho
                var botoes_header = doc.querySelectorAll('header button');
                if (botoes_header.length > 0) {
                    botoes_header[0].click();
                }
            }
        }, 300); // Aumentei o delay para 300ms para ter certeza absoluta que a tela carregou
    </script>
    '''
    components.html(js_fechar_menu, width=0, height=0)
    
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

elif st.session_state.pagina == 'ocorrencias': # 👈 NOVA ROTA AQUI!
    exibir_ocorrencias(supabase)
    
elif st.session_state.pagina == 'cadastro':
    exibir_cadastro(supabase)
    
elif st.session_state.pagina == 'reservas':
    LISTA_PROF = ["Prof. Silva", "Profa. Maria", "Prof. Ricardo"]
    AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula"]
    ESPACOS = ["Auditório", "Laboratório", "Biblioteca", "Quadra", "Multimídia"]
    exibir_reservas(supabase, LISTA_PROF, AULAS, ESPACOS, 3, 2, 5)
    
elif st.session_state.pagina == 'importacao':
    exibir_importacao(supabase)