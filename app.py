import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import datetime
import time
import sys
import os
import threading
import subprocess

# ==========================================
# 1. CONFIGURAÇÃO GERAL DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="EREM PAM - Chamada Escolar", layout="wide", page_icon="🏫"
)


# --- GATILHO PARA O BOT TELEGRAM (SIGEREMPAM) ---
@st.cache_resource
def iniciar_bot_telegram():
    """Inicia o bot do Telegram em segundo plano ao abrir o sistema central"""

    def rodar():
        # Prepara as variáveis de ambiente para o subprocesso (essencial no Streamlit Cloud)
        env = os.environ.copy()
        # Injeta as secrets do Streamlit no ambiente para o Bot ler sem depender de contexto Streamlit
        env["TELEGRAM_BOT_TOKEN"] = st.secrets["TELEGRAM_BOT_TOKEN"]
        env["SUPABASE_URL_ALUNOS"] = st.secrets["SUPABASE_URL_ALUNOS"]
        env["SUPABASE_KEY_ALUNOS"] = st.secrets["SUPABASE_KEY_ALUNOS"]

        # Localiza o caminho absoluto do script para evitar erros de diretório no servidor
        caminho_script = os.path.join(os.path.dirname(__file__), "telegram_menu.py")

        # Usa sys.executable para garantir que o Bot use o mesmo interpretador do Streamlit
        subprocess.Popen([sys.executable, caminho_script], env=env)

    thread = threading.Thread(target=rodar, daemon=True)
    thread.start()


iniciar_bot_telegram()

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
    from modulos.atrasos_aba import exibir_atrasos
    from modulos.gestao_feira import exibir_gestao_feira
except Exception as e:
    st.error(f"🚨 Erro ao carregar os módulos das telas: {e}")
    st.stop()

# ==========================================
# 3. CONEXÃO COM O BANCO DE DADOS (SUPABASE)
# ==========================================
try:
    URL_SUPABASE = st.secrets["SUPABASE_URL_ALUNOS"]
    CHAVE_SUPABASE = st.secrets["SUPABASE_KEY_ALUNOS"]
    supabase: Client = create_client(URL_SUPABASE, CHAVE_SUPABASE)
except Exception as e:
    st.error(f"🚨 Erro ao conectar no Supabase: {e}")
    st.stop()

# ==========================================
# 4. GERENCIADOR DE ESTADO E LINKS DIRETOS
# ==========================================

# 1. O SENSOR DE URL: Verifica se alguém clicou em um link direto
if "page" in st.query_params:
    pagina_destino = st.query_params.get("page")

    # Se o link tiver "?page=criar_evento", direciona para a tela correta
    if pagina_destino == "criar_evento":
        st.session_state.pagina = "gestao_feira"

    # Limpa a URL logo em seguida para o usuário poder navegar livremente depois
    st.query_params.clear()

# 2. DEFINIÇÃO PADRÃO: Se não tem link e está abrindo do zero, vai para o 'cenario'
if "pagina" not in st.session_state:
    st.session_state.pagina = "cenario"

if "fechar_menu" not in st.session_state:
    st.session_state.fechar_menu = False


def mudar_pagina(nome_pagina):
    st.session_state.pagina = nome_pagina
    st.session_state.fechar_menu = (
        True  # Liga o gatilho para recolher o menu no celular
    )


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
    st.button(
        "📊 Cenário do Dia",
        on_click=mudar_pagina,
        args=("cenario",),
        use_container_width=True,
    )
    st.button(
        "🔎 Busca Ativa",
        on_click=mudar_pagina,
        args=("busca_ativa",),
        use_container_width=True,
    )
    st.button(
        "📸 Fotograma",
        on_click=mudar_pagina,
        args=("fotograma",),
        use_container_width=True,
    )
    st.button(
        "🧩 AEE & Inclusão",
        on_click=mudar_pagina,
        args=("aee",),
        use_container_width=True,
    )
    st.button(
        "🚨 Ocorrências",
        on_click=mudar_pagina,
        args=("ocorrencias",),
        use_container_width=True,
    )
    st.button(
        "⏰ Atrasos", on_click=mudar_pagina, args=("atrasos",), use_container_width=True
    )
    st.button(
        "📝 Gestão de Alunos",
        on_click=mudar_pagina,
        args=("cadastro",),
        use_container_width=True,
    )
    st.button(
        "📅 Reservas",
        on_click=mudar_pagina,
        args=("reservas",),
        use_container_width=True,
    )

    st.divider()

    # --- ESTILO LARANJA SEM EMOJI (DENTRO DA SIDEBAR) ---
    st.markdown(
        """
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
    """,
        unsafe_allow_html=True,
    )

    # Botão Laranja (agora sincronizado com o CSS)
    st.button(
        "Criar um evento",
        on_click=mudar_pagina,
        args=("gestao_feira",),
        use_container_width=True,
    )

    # Botão de Importação Verde (Primary)
    st.button(
        "📤 Importar e Atualizar Alunos",
        on_click=mudar_pagina,
        args=("importacao",),
        type="primary",
        use_container_width=True,
    )

# ==========================================
# 6. INJEÇÃO DE CÓDIGO PARA CELULAR (Mantido)
# ==========================================
if st.session_state.fechar_menu:
    js_fechar_menu = """
    <script>
        setTimeout(function() {
            var doc = window.parent.document;
            var btn_fechar = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
            if (btn_fechar) btn_fechar.click();
        }, 300);
    </script>
    """
    components.html(js_fechar_menu, width=0, height=0)
    st.session_state.fechar_menu = False

# ==========================================
# ROTEAMENTO DE PÁGINAS (O MAESTRO)
# ==========================================

if st.session_state.pagina == "cenario":
    exibir_cenario(supabase)

elif st.session_state.pagina == "busca_ativa":
    exibir_busca_ativa(
        supabase, supabase
    )  # ✅ CORRIGIDO: Agora passa 2 parâmetros (supabase, supabase_alunos)

elif st.session_state.pagina == "fotograma":
    exibir_fotograma(supabase)

elif st.session_state.pagina == "aee":
    exibir_painel_aee(supabase)

elif st.session_state.pagina == "ocorrencias":
    exibir_ocorrencias(supabase)

elif st.session_state.pagina == "atrasos":
    exibir_atrasos(supabase)

elif st.session_state.pagina == "cadastro":
    exibir_cadastro(supabase)

elif st.session_state.pagina == "reservas":
    # --- FUNÇÃO COM CACHE PARA ECONOMIZAR EGRESS ---
    @st.cache_data(ttl=600)
    def obter_professores_cacheado(_supabase):
        try:
            res = _supabase.table("assinaturas").select("nome").execute()
            return [linha["nome"] for linha in res.data]
        except:
            return ["Erro ao carregar professores"]

    # Execução da busca (agora protegida por cache)
    LISTA_PROF = obter_professores_cacheado(supabase)

    AULAS = [f"{i}ª Aula" for i in range(1, 10)]
    ESPACOS = [
        "Auditório",
        "Laboratório",
        "Biblioteca",
        "Quadra",
        "Multimídia",
        "Sala de Vídeo",
    ]

    exibir_reservas(supabase, LISTA_PROF, AULAS, ESPACOS, 3, 2, 9)

elif st.session_state.pagina == "importacao":
    exibir_importacao(supabase)

elif st.session_state.pagina == "gestao_feira":
    exibir_gestao_feira(supabase)
