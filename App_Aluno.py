import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import time
import re
import random 
import base64
import os

# ==========================================
# 1. CONFIGURAÇÕES, IDENTIDADE E ESTILO (TEMA CLARO PRO)
# ==========================================
# Deve ser a PRIMEIRA coisa do script
st.set_page_config(
    page_title="Portal de Avaliações | Química com Lardião Pro", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="logo_erempam.png" # Usando logo como ícone de aba
)

# Paleta Light Premium Neutra (Para destacar as duas logos)
C_BG_DEEP = "#F0F4F8"      # Cinza Gelo Suave (Fundo Total)
C_CARD_BG = "#FFFFFF"     # Branco Puro (Cards e Containers Nativo)
C_PRIMARY = "#00C896"     # Teal Vibrante (React Glow / Destaques)
C_SECONDARY = "#FF8000"   # Laranja Vibrante (Títulos)
C_TEXT = "#2D3748"        # Cinza Escuro Quase Preto (Texto Principal)
C_TEXT_MUTED = "#718096"  # Cinza Médio (Subtítulos)
C_BORDER = "#E2E8F0"      # Cinza Claro (Bordas)

# Função para converter imagem local em Base64
# NOTA: Garanta que as imagens estão na mesma pasta do script
def get_base64_image(image_path):
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except Exception as e:
            st.error(f"Erro ao ler imagem {image_path}: {e}")
    return ""

# Carrega as logos
logo_erempam_b64 = get_base64_image("logo_erempam.png")
logo_lardiao_b64 = get_base64_image("logo_lardiao.png")

# Injeção de CSS Light Premium Mobile-Focused
st.markdown(f"""
    <style>
        /* Define fundo claro neutro para toda a aplicação */
        .stApp {{
            background-color: {C_BG_DEEP};
            color: {C_TEXT};
        }}
        
        /* Esconder Sidebar e Menu padrão do Streamlit */
        [data-testid="stSidebar"] {{display: none;}}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        .main .block-container {{padding-top: 1.5rem;}}

        /* Centralizar login e Estilo React-style */
        .login-card {{
            text-align: center; 
            max-width: 500px; /* Levemente maior para mobile */
            margin: 4rem auto; 
            padding: 45px 35px; /* Mais padding para mobile */
            border: 1px solid {C_BORDER}; 
            border-radius: 20px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.05); /* Sombra suave no tema claro */
            background-color: {C_CARD_BG};
        }}

        /* Customizar inputs Streamlit para o Tema Light */
        .stTextInput>div>div>input {{
            background-color: #F7FAFC !important; /* Ligeiramente mais escuro que o card */
            color: {C_TEXT} !important;
            border-radius: 12px !important;
            border-color: {C_BORDER} !important;
            padding: 14px !important; /* Maior área de toque mobile */
            font-size: 16px !important;
        }}
        .stTextInput>div>div>input:focus {{
            border-color: {C_PRIMARY} !important;
            box-shadow: 0 0 0 0.2rem rgba(0,200,150,0.2) !important;
            background-color: #FFFFFF !important;
        }}
        
        /* Labels dos inputs em branco */
        .stTextInput>label {{
            color: {C_TEXT} !important;
            font-weight: bold;
            font-size: 14px;
        }}

        /* Botão Primário Lardião Pro */
        .stButton>button[kind="primary"] {{
            background-color: {C_PRIMARY};
            color: #FFFFFF;
            border: none;
            border-radius: 12px; height: 3.8em; font-weight: bold; 
            font-size: 17px;
            transition: all 0.3s ease;
            width: 100%;
        }}
        .stButton>button[kind="primary"]:hover {{
            background-color: {C_SECONDARY};
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255,128,0,0.3);
        }}

        /* Estilo da Tabela Profissional Dark na Ante-sala */
        .pro-table-container {{
            background-color: {C_CARD_BG};
            border-radius: 15px;
            padding: 20px;
            border: 1px solid {C_BORDER};
            margin-top: 20px;
        }}
        .pro-table {{
            width: 100%; border-collapse: collapse; 
            font-family: sans-serif;
            color: {C_TEXT};
        }}
        .pro-table thead tr {{
            border-bottom: 2px solid {C_PRIMARY};
            text-align: left; font-weight: bold;
            font-size: 14px;
        }}
        .pro-table th, .pro-table td {{ padding: 18px 15px; }}
        .pro-table tbody tr {{
            border-bottom: 1px solid {C_BORDER};
            transition: background 0.2s;
        }}
        .pro-table tbody tr:hover {{
            background-color: rgba(0,200,150,0.05); /* Destaque hover na linha */
        }}

        /* Badges de Status na Tabela */
        .badge-status {{
            padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 12px;
            display: inline-block;
        }}
        .status-done {{ background-color: rgba(40, 167, 69, 0.2); color: #28a745; border: 1px solid #28a745; }}
        .status-pending {{ background-color: rgba(255, 193, 7, 0.2); color: #ffc107; border: 1px solid #ffc107; }}

        /* Estilo para garantir que o container nativo do Streamlit siga o tema PRO na Ante-sala */
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {C_CARD_BG};
            border-radius: 15px;
            border-color: {C_BORDER};
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO SEGURA (CADASTRAR NO SECRETS)
# ==========================================
@st.cache_resource
def init_connections():
    try:
        db_alunos = create_client(st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"])
        db_provas = create_client(st.secrets["SUPABASE_URL_PROVAS"], st.secrets["SUPABASE_KEY_PROVAS"])
        return db_alunos, db_provas
    except Exception as e:
        st.error(f"Erro Crítico de Conexão: Verifique st.secrets. Detalhes: {e}")
        st.stop()

db_alunos, db_provas = init_connections()

# ==========================================
# 3. ESTADO DA SESSÃO (PROTETOR DE FLUXO)
# ==========================================
for key in ['etapa', 'aluno', 'prova_config', 'tempo_final', 'questoes', 'respostas']:
    if key not in st.session_state:
        if key == 'etapa': st.session_state[key] = "login"
        elif key == 'respostas': st.session_state[key] = {}
        else: st.session_state[key] = None

# ==========================================
# ETAPA 1: LOGIN (VISUAL CONSOLIDADO PRO)
# ==========================================
if st.session_state.etapa == "login":
    
    # Gerar Base64 da sua logo (Química com Lardião)
    # Certifique-se que o arquivo 'logo_lardiao.png' está na mesma pasta
    logo_lardiao_b64 = get_base64_image("logo_lardiao.png")

    # Injeção de CSS específico para esta tela de Login Pro
    st.markdown(f"""
        <style>
        /* Fundo da página em Cinza Gelo para contrastar */
        .stApp {{
            background-color: {C_BG_DEEP};
        }}
        
        /* Centralizar login e Estilo Card Profissional */
        .login-card {{
            text-align: center; 
            max-width: 480px; 
            margin: 5rem auto; 
            padding: 40px; 
            border: 1px solid {C_BORDER}; 
            border-radius: 20px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.05); /* Sombra suave */
            background-color: {C_CARD_BG}; /* Fundo Branco do Card */
        }}

        /* Customizar Títulos dentro do Card */
        .title-portal {{
            color: {C_PRIMARY}; /* Teal do portal */
            font-size: 28px;
            font-weight: 800;
            margin-top: 25px;
            margin-bottom: 5px;
            text-transform: uppercase;
            font-family: sans-serif;
        }}
        .subtitle-portal {{
            color: {C_TEXT_MUTED}; /* Cinza médio */
            font-size: 16px;
            font-weight: normal;
            margin-bottom: 35px;
            font-family: sans-serif;
        }}

        /* Estilizar o campo de input e botão para ficarem 'abraçados' pelo card */
        .stTextInput>div>div>input {{
            background-color: #F7FAFC !important; /* Ligeiramente cinza */
            border-radius: 10px !important;
        }}
        
        .stButton>button {{
            border-radius: 10px !important;
        }}
        
        /* Link de dúvidas estiloso */
        .help-link {{
            color: {C_TEXT_MUTED};
            font-size: 14px;
            text-decoration: none;
            transition: color 0.3s;
        }}
        .help-link:hover {{
            color: {C_SECONDARY}; /* Laranja no hover */
            text-decoration: underline;
        }}
    </style>
""", unsafe_allow_html=True)

    # Início da renderização visual do Card Pro
    st.markdown(f"""
        <div class="login-card">
            <div style="display: flex; justify-content: center; align-items: center;">
                <img src="data:image/png;base64,{logo_lardiao_b64}" width="180" alt="Química com Lardião Pro"/>
            </div>
            <div class="title-portal">SISTEMA DE ATIVIDADES</div>
            <div class="subtitle-portal">do Prof. Lardião</div>
        </div>
    """, unsafe_allow_html=True)

    # Inputs posicionados LOGICAMENTE dentro do fluxo do card (centralizados por colunas)
    col1, col2, col3 = st.columns([1, 2.5, 1])
    with col2:
        # Espaçador para dar respiro
        st.write("") 
        matricula = st.text_input("Sua Matrícula SIGEREMPAM:", placeholder="Ex: 2024123", key="mat_input")
        
        # Espaçador antes do botão
        st.write("")
        btn_acesso = st.button("ACESSAR SISTEMA PRO", use_container_width=True, type="primary", key="btn_acesso")
        
        if btn_acesso and matricula:
            with st.spinner("Autenticando..."):
                try:
                    res = db_alunos.table("alunos").select("*").eq("numero_matricula", matricula).execute()
                    if res.data:
                        st.session_state.aluno = res.data[0]
                        st.session_state.etapa = "ante_sala"
                        st.rerun()
                    else:
                        st.error("Matrícula não encontrada nas bases da EREMPAM.")
                except Exception as e:
                    st.error(f"Erro na conexão com a base de alunos: {e}")

        # Espaçador final e Link de Dúvidas
        st.write("")
        st.markdown("""
            <div style="text-align: center; margin-top: 20px;">
                <a href="#" class="help-link">Dúvidas ou problemas? Clique aqui.</a>
            </div>
        """, unsafe_allow_html=True)

# ==========================================
# ETAPA 2: ANTE-SALA (TABELA NATIVA BLINDADA - RESOLVE O PRINT 2)
# ==========================================
elif st.session_state.etapa == "ante_sala":
    aluno = st.session_state.aluno
    # Lógica de tradução de turma para sérieSIGEREMPAM
    turma_bruta = str(aluno.get('turma', ''))
    serie_aluno = "1º Ano"
    if "2" in turma_bruta: serie_aluno = "2º Ano"
    elif "3" in turma_bruta: serie_aluno = "3º Ano"

    # Título com Destaque Vibrante React-style
    st.markdown(f"""
        <div style="margin-bottom: 30px;">
            <h1 style="color: {C_TEXT}; margin-bottom: 8px;">👋 Olá, <span style="color: {C_SECONDARY};">{aluno['nome']}</span>!</h1>
            <p style="color: {C_TEXT_MUTED}; font-size: 16px;">Sua série é o <strong>{serie_aluno}</strong>. Confira suas atividades pendentes.</p>
        </div>
    """, unsafe_allow_html=True)

    with st.spinner("Buscando avaliações disponíveis..."):
        try:
            # 1. Provas Ativas para a série
            res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).execute()
            provas_ativas = res_p.data
            
            # 2. Verificar o que já foi feito (CORREÇÃO res_JF blindada do Pylance)
            ids_ativas = [p['id'] for p in provas_ativas]
            ja_fez_dict = {}
            if ids_ativas:
                res_JF = db_provas.table("resultados_provas").select("prova_id").eq("aluno_id", str(aluno['id'])).in_("prova_id", ids_ativas).execute()
                ja_fez_dict = {x['prova_id']: True for x in res_JF.data}

            # 3. CONSTRUÇÃO DA LISTA DE PROVAS USANDO ELEMENTOS NATIVOS (RESOLVE CÓDIGO ESTRANHO)
            if provas_ativas:
                # Cabeçalho React-style nativo
                st.markdown(f"### 📋 Lista de Atividades")
                ha_pendentes = False
                
                for p in provas_ativas:
                    # Cálculos baseados na regra de sorteio PRO
                    q_sorteio = p.get('qtd_sorteio', p.get('qtd_questoes', 1))
                    valor_total = q_sorteio * p.get('valor_questao', 1.0)
                    
                    # Data formatada para mobile
                    dt_limite = datetime.fromisoformat(p['data_limite']).strftime("%d/%m/%Y às %H:%M")
                    
                    # Status e Lógica
                    foi_feita = ja_fez_dict.get(p['id'], False)
                    status_texto = "✅ Concluída" if foi_feita else "🔵 Pendente"
                    status_cor = "green" if foi_feita else "orange"

                    if not foi_feita: ha_pendentes = True

                    # Container nativo Streamlit que agora segue o tema PRO
                    with st.container(border=True):
                        # Layout PRO nativo em colunas
                        col1, col2, col3 = st.columns([3, 1, 1.5])
                        
                        with col1:
                            st.markdown(f"**<span style='color:{C_PRIMARY}; font-size:18px;'>{p['titulo']}</span>**", unsafe_allow_html=True)
                            st.caption(f"Assunto: {p.get('assunto','Química Pro')}")
                            
                        with col2:
                            st.markdown("**Pontos:**")
                            st.write(f"{valor_total:.1f}")
                            
                        with col3:
                            st.markdown("**Status / Limite:**")
                            # Usa a marcação nativa do Streamlit para cor
                            st.markdown(f":{status_cor}[**{status_texto}**]")
                            st.caption(dt_limite)
                
                # 4. Botões Streamlit nativos para iniciar (abaixo da lista)
                if ha_pendentes:
                    st.divider()
                    st.markdown("### ✍️ Iniciar Atividade Avaliativa")
                    # Cria colunas dinâmicas para os botões de início Pro
                    num_btn = len([x for x in provas_ativas if not ja_fez_dict.get(x['id'], False)])
                    cols_btn = st.columns(max(num_btn, 1))
                    
                    idx_col = 0
                    for p in provas_ativas:
                        if not ja_fez_dict.get(p['id'], False):
                            with cols_btn[idx_col]:
                                if st.button(f"Iniciar {p['titulo']}", key=f"btn_init_{p['id']}", type="primary", use_container_width=True):
                                    st.session_state.prova_config = p
                                    st.session_state.etapa = "instrucoes"
                                    st.rerun()
                            idx_col += 1
            else:
                st.success("🎉 Excelente! Você concluiu todas as atividades avaliativas disponíveis para o {serie_aluno}.")
                
        except Exception as e:
            st.error(f"Erro Crítico ao renderizar ante-sala: {e}")

# ==========================================
# ETAPA 3: INSTRUÇÕES E SORTEIO
# ==========================================
elif st.session_state.etapa == "instrucoes":
    # (Mantido como antes, focado na semente estável Pro por aluno)
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    st.header(f"👋 Preparado, {aluno['nome']}?")
    
    with st.container(border=True):
        st.subheader(f"📝 {prova['titulo']}")
        st.write(f"Série: {prova['serie']} | Tempo de Execução: **{prova['tempo_duracao']} minutos**")
        
        st.markdown(f"""
            **Instruções Importantes Pro:**
            1. Você terá estatisticamente {prova['tempo_duracao']} minutos para concluir após clicar no botão abaixo.
            2. Não atualize ou feche o navegador SIGEREMPAM durante a prova, ou seu progresso será perdido.
            3. Responda todas as questões e clique em 'Enviar' ao final.
        """)
        
        if st.button("ESTOU PRONTO, INICIAR PROVA AGORA", type="primary", use_container_width=True, key="btn_start"):
            with st.spinner("Gerando sua avaliação única e randomizada..."):
                # Define tempo final
                st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
                
                # Busca POOL de questões Supabase
                ids = prova.get('questoes_ids', [])
                res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
                pool_questoes = res_q.data
                
                # SORTEIO ESTÁVEL POR ALUNO
                # Usamos o ID do aluno como semente para o sorteio ser fixo para ele (UUID blindado como string)
                random.seed(str(aluno['id']))
                random.shuffle(pool_questoes)
                
                # Corta pela quantidade definida no campo 'qtd_sorteio' Pro
                n_sorteio = prova.get('qtd_sorteio', len(pool_questoes))
                questoes_sorteadas = pool_questoes[:n_sorteio]
                
                # Salva o subconjunto no estado Pro
                st.session_state.questoes = questoes_sorteadas
                st.session_state.etapa = "em_prova"
                st.rerun()

# ==========================================
# ETAPA 4: EXECUÇÃO DA PROVA (RANDOMIZAÇÃO DE ALTERNATIVAS - PRO LIGHT)
# ==========================================
elif st.session_state.etapa == "em_prova":
    import streamlit.components.v1 as components
    
    # Validação de segurança blindada
    if not st.session_state.questoes or not st.session_state.tempo_final:
        st.session_state.etapa = "login"
        st.rerun()

    restante = st.session_state.tempo_final - datetime.now()
    segs = int(restante.total_seconds())
    
    if segs <= 0:
        st.error("⌛ TEMPO ESGOTADO! Infelizmente, suas respostas não foram enviadas a tempo Pro.")
        if st.button("Voltar ao Portal Pro", type="secondary"):
            st.session_state.clear()
            st.rerun()
        st.stop()

    # Cabeçalho da Prova Mobile React-style
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
            <h2 style="color: {C_TEXT}; font-size: 24px;">✍️ {st.session_state.prova_config['titulo']}</h2>
            <p style="color: {C_TEXT_MUTED}; font-size: 14px;">Aluno: {st.session_state.aluno['nome']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Início do Formulário Dark Pro
    with st.form("form_prova", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questoes):
            # Container nativo Streamlit para cada questão Pro
            with st.container(border=True):
                st.markdown(f"**<span style='color: {C_PRIMARY}; font-size: 18px; display: block; margin-bottom: 15px;'>QUESTÃO {i+1}</span>**", unsafe_allow_html=True)
                
                # Renderiza enunciado HTML Supabase
                st.markdown(q['enunciado'], unsafe_allow_html=True)
                
                # --- LÓGICA DE ALTERNATIVAS RANDOMIZADAS E LIMPAS ---
                opcoes_dict = q.get('alternativas', {}) 
                letras_originais = [l for l in ["A", "B", "C", "D", "E"] if opcoes_dict.get(l)]
                
                # Semente única por Questão + Aluno
                random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
                ordem = letras_originais.copy()
                random.shuffle(ordem)

                # Função SUPER limpadora Pro (Tira HTML e sujeiras SIGEREMPAM)
                def limpar_alternativa(texto_cru):
                    t_sem_html = re.sub(r'<[^>]+>', '', str(texto_cru)) # Tira tags HTML
                    t_limpo = re.sub(r'^\s*[A-Ea-e]\s*[\)\.\-]\s*', '', t_sem_html).strip() # Tira "A) ", "B. "
                    return t_limpo

                # Desenha o rádio button Streamlit nativo embaralhado Pro
                st.markdown(f"<strong style='font-size:15px; color:{C_TEXT}'>Selecione a alternativa correta Pro:</strong>", unsafe_allow_html=True)
                escolha = st.radio(
                    f"Radio_Q{i+1}", # Label escondida
                    options=ordem, 
                    format_func=lambda x: f"{x}) {limpar_alternativa(opcoes_dict.get(x, ''))}",
                    index=None, 
                    key=f"q_{q['id']}", # Chave única Supabase
                    label_visibility="collapsed" # Esconde label para ficar limpo
                )
                
                if escolha:
                    # Salva apenas a letra original Supabase (ex: 'C')
                    st.session_state.respostas[q['id']] = escolha 
                st.markdown("<br>", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        # Botão de envio PRO nativo
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR AVALIAÇÃO PRO", type="primary", use_container_width=True)

    if entregar:
        if len(st.session_state.respostas) < len(st.session_state.questoes):
            st.warning("⚠️ Atenção! Você precisa responder todas as questões Pro antes de enviar.")
        else:
            with st.spinner("Processando suas respostas e calculando nota Pro..."):
                # Cálculo da Nota blindada baseada no valor individual configurado pelo Professor
                valor_cada = st.session_state.prova_config.get('valor_questao', 1.0)
                acertos = 0
                for q in st.session_state.questoes:
                    if st.session_state.respostas.get(q['id']) == q['resposta_correta']:
                        acertos += 1
                
                # Prepara dados para inserção no banco resultados_provas Supabase
                lista_resultados = []
                for q in st.session_state.questoes:
                    resp_aluno = st.session_state.respostas.get(q['id'])
                    lista_resultados.append({
                        "aluno_id": str(st.session_state.aluno['id']), 
                        "prova_id": st.session_state.prova_config['id'],
                        "questao_id": q['id'],
                        "resposta_aluno": resp_aluno,
                        "acertou": (resp_aluno == q['resposta_correta']),
                        "acertos": acertos # Score total na prova Pro
                    })
                
                try:
                    # Envia tudo em lote Supabase Pro
                    db_provas.table("resultados_provas").insert(lista_resultados).execute()
                    # Vai para etapa final Pro
                    st.session_state.etapa = "resultado_final"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro Crítico ao salvar resultado no banco de dados Pro: {e}")

# ==========================================
# ETAPA 5: RESULTADO E MISTÉRIO DO PROFESSOR (PREPARAÇÃO IA)
# ==========================================
elif st.session_state.etapa == "resultado_final":
    aluno = st.session_state.aluno
    # Coleta total de acertos baseados no envio anterior (Erro res_JF corrigido Pro)
    res_JF = db_provas.table("resultados_provas").select("acertos").eq("aluno_id", str(aluno['id'])).eq("prova_id", st.session_state.prova_config['id']).limit(1).execute()
    total_acertos = res_JF.data[0]['acertos'] if res_JF.data else 0
    total_questoes = len(st.session_state.questoes)

    st.balloons() # Celebração React-style Pro
    st.markdown(f"""
        <div style="text-align: center; margin-top: 3rem;">
            <h1 style="color: {C_PRIMARY}; font-size: 40px; font-weight: bold;">🎉 Avaliação Concluída!</h1>
            <p style="color: {C_TEXT_MUTED}; font-size: 18px; margin-top: 10px;">Parabéns, {aluno['nome']}. Suas respostas foram enviadas e processadas Pro.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Container nativo do Streamlit para o Card de Nota Pro chique
    with st.container(border=True):
        st.markdown(f"""
            <div style="text-align: center; padding: 15px;">
                <h2 style="color: {C_TEXT}; margin-bottom: 10px; font-size: 24px;">Sua Nota PRO na {st.session_state.prova_config['titulo']}</h2>
                <div style="font-size: 60px; font-weight: bold; color: {C_SECONDARY}; margin: 10px 0;">
                    {total_acertos * st.session_state.prova_config.get('valor_questao', 1.0):.1f}
                </div>
                <p style="color: {C_TEXT_MUTED}; font-size: 18px;">Você acertou <strong>{total_acertos}</strong> de <strong>{total_questoes}</strong> questões Pro.</p>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- PLACEHOLDERS FASE 3 (IA + RANKING) - VISUAL PRO NATIVO ---
    colR1, colR2 = st.columns(2)
    
    with colR1:
        with st.container(border=True):
            st.markdown(f"""
                <div style="text-align: center;">
                    <h3 style="color: {C_PRIMARY}; font-size: 20px;">🌎 Ranking Gamificado Pro</h3>
                    <p style="color: orange; font-weight: bold; font-size: 16px; margin: 15px 0;">⌛ CALCULANDO...</p>
                    <p style="color: {C_TEXT_MUTED}; font-size: 14px;">O Prof. Lardião está calculando sua posição Pro na turma e entre todos os terceiros!</p>
                </div>
            """, unsafe_allow_html=True)
        
    with colR2:
        with st.container(border=True):
            st.markdown(f"""
                <div style="text-align: center;">
                    <h3 style="color: {C_PRIMARY}; font-size: 20px;">🧠 Feedback do Mestre Pro</h3>
                    <p style="color: orange; font-weight: bold; font-size: 16px; margin: 15px 0;">⌛ AGUARDE!</p>
                    <p style="color: {C_TEXT_MUTED}; font-size: 14px;">O Prof. Lardião está analisando seu desempenho Pro para te dar uma dica de mestre personalizada em instantes...</p>
                </div>
            """, unsafe_allow_html=True)

    st.divider()
    if st.button("⬅️ Voltar para o Portal Pro", type="secondary", use_container_width=True):
        st.session_state.clear() # Limpa tudo e volta pro login blindado
        st.rerun()