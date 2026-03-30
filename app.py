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
# 7. TELA DA FEIRA DE CIÊNCIAS E EVENTOS
# ==========================================
import datetime


def exibir_gestao_feira(supabase_conn):
    st.title("🎪 Gestão de Eventos e Feiras")
    st.markdown("Configure novos eventos e gerencie as linhas de pesquisa dos professores orientadores.")
    
    aba_evento, aba_orientadores = st.tabs([
        "📅 1. Lançar Evento (Edital)", 
        "👨‍🏫 2. Cadastrar Trabalhos (Orientadores)"
    ])
    
    # ==========================================
    # ABA 1: LANÇAR O EVENTO
    # ==========================================
    with aba_evento:
        st.subheader("Configurações Gerais do Evento")
        with st.form("form_novo_evento"):
            nome_evento = st.text_input("Nome do Evento", value="1ª Feira de Matemática e Natureza EREMPAM")
            
            col1, col2 = st.columns(2)
            data_inicio = col1.date_input("Data de Início", datetime.date(2026, 7, 2))
            data_fim = col2.date_input("Data de Fim", datetime.date(2026, 7, 3))
            
            col3, col4 = st.columns(2)
            min_alunos = col3.number_input("Mínimo de Alunos por Grupo", min_value=1, value=4)
            max_alunos = col4.number_input("Máximo de Alunos por Grupo", min_value=1, value=8)
            
            observacoes = st.text_area("Observações (Aparecerá para os alunos no app)", 
                                       value="Atenção: Dia 02/07 exclusivo para turmas de 1º Ano. Dia 03/07 para 2º e 3º Anos.")
            
            salvar_evento = st.form_submit_button("💾 Salvar Evento", type="primary", use_container_width=True)
            
            if salvar_evento:
                # Monta o pacote de dados para o Supabase
                dados_evento = {
                    "nome": nome_evento,
                    "data_inicio": str(data_inicio),
                    "data_fim": str(data_fim),
                    "min_membros": min_alunos,
                    "max_membros": max_alunos,
                    "observacoes": observacoes,
                    "ativo": True
                }
                try:
                    supabase_conn.table("feira_eventos").insert(dados_evento).execute()
                    st.success(f"✅ Evento '{nome_evento}' criado e salvo no banco de dados com sucesso!")
                except Exception as e:
                    st.error(f"🚨 Erro ao salvar o evento: {e}")

    # ==========================================
    # ABA 2: CADASTRAR TRABALHOS
    # ==========================================
    with aba_orientadores:
        st.subheader("Cadastro de Trabalhos / Linhas de Pesquisa")
        st.info("Vincule o trabalho a um evento existente, selecione o professor e descreva o tema.")
        
        # --- 1. BUSCANDO OS EVENTOS JÁ CRIADOS ---
        try:
            res_eventos = supabase_conn.table("feira_eventos").select("id, nome").eq("ativo", True).execute()
            dict_eventos = {item["nome"]: item["id"] for item in res_eventos.data}
            lista_eventos = list(dict_eventos.keys())
        except Exception as e:
            lista_eventos = []
            dict_eventos = {}
            st.warning("Não consegui buscar os eventos. Crie um evento primeiro na aba ao lado.")

        # --- 2. BUSCANDO PROFESSORES DIRETO DO SUPABASE (CORRIGIDO) ---
        try:
            # Busca na tabela certa (professores_matriculas) e coluna certa (professor)
            resposta = supabase_conn.table("professores_matriculas").select("professor").execute()
            # Pega só nomes válidos e organiza em ordem alfabética
            lista_professores = ["Selecione..."] + sorted([linha["professor"] for linha in resposta.data if linha["professor"]])
        except Exception as e:
            st.warning(f"Erro ao carregar a tabela professores_matriculas: {e}")
            lista_professores = ["Selecione..."]
        
        # --- 3. FORMULÁRIO DE TEMAS ---
        with st.form("form_novo_tema"):
            
            if not lista_eventos:
                st.error("Crie um evento na Aba 1 antes de cadastrar temas!")
                evento_selecionado = None
            else:
                evento_selecionado = st.selectbox("Vincular a qual Evento?", lista_eventos)

            professor_selecionado = st.selectbox("Selecione o Orientador", lista_professores)
            titulo_trabalho = st.text_input("Título da Linha de Pesquisa / Trabalho")
            descricao_trabalho = st.text_area("Descrição Breve do que os alunos farão neste tema")
            vagas = st.number_input("Quantos grupos este professor pode orientar neste tema?", min_value=1, value=5)
            
            salvar_tema = st.form_submit_button("➕ Adicionar Linha de Pesquisa", type="primary", use_container_width=True)
            
            if salvar_tema:
                if not evento_selecionado:
                    st.error("Nenhum evento disponível para vincular.")
                elif professor_selecionado == "Selecione...":
                    st.error("Por favor, selecione um orientador.")
                elif not titulo_trabalho:
                    st.error("Digite o título do trabalho.")
                else:
                    dados_tema = {
                        "evento_id": dict_eventos[evento_selecionado],
                        "professor_nome": professor_selecionado,
                        "titulo_trabalho": titulo_trabalho,
                        "descricao": descricao_trabalho,
                        "vagas_grupos": vagas
                    }
                    try:
                        supabase_conn.table("feira_temas").insert(dados_tema).execute()
                        st.success(f"✅ Trabalho '{titulo_trabalho}' vinculado ao professor {professor_selecionado} com sucesso!")
                    except Exception as e:
                        st.error(f"🚨 Erro ao salvar tema: {e} (Você já criou a tabela 'feira_temas' no Supabase?)")

# ==========================================
# 8. ROTEAMENTO DE PÁGINAS (O MAESTRO EM AÇÃO)
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
    # 1. BUSCA PROFESSORES REAIS DA TABELA ASSINATURAS
    try:
        res_prof = supabase.table("assinaturas").select("nome").execute()
        LISTA_PROF = [linha["nome"] for linha in res_prof.data]
        if not LISTA_PROF:
            LISTA_PROF = ["Nenhum professor encontrado"]
    except:
        LISTA_PROF = ["Erro ao carregar professores"]

    # 2. CONFIGURAÇÃO DAS 9 AULAS DA EREM
    AULAS = [f"{i}ª Aula" for i in range(1, 10)] 
    
    # 3. ESPAÇOS DA ESCOLA
    ESPACOS = ["Auditório", "Laboratório", "Biblioteca", "Quadra", "Multimídia", "Sala de Vídeo"]
    
    # 4. CHAMA A FUNÇÃO (Ajustado para 9 aulas)
    # Parâmetros: (conexão, lista_prof, aulas, espaços, colunas_ui, max_reservas_dia, total_aulas)
    exibir_reservas(supabase, LISTA_PROF, AULAS, ESPACOS, 3, 2, 9)
    
elif st.session_state.pagina == 'importacao':
    exibir_importacao(supabase)

elif st.session_state.pagina == 'gestao_feira': # 👈 NOSSO NOVO MÓDULO AQUI!
    exibir_gestao_feira(supabase)