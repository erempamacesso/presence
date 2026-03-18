import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import time
import re
import random 
import base64 # Necessário para carregar imagens no HTML
import os

# ==========================================
# 1. CONFIGURAÇÕES, IDENTIDADE E ESTILO (DARK PRO - FASE 1)
# ==========================================
# Configuração de página React-style
st.set_page_config(
    page_title="Portal Lardião | Química Pro", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="logo_erempam.png" # Usando logo como ícone de aba
)

# Paleta Dark Premium Neutra (Para destacar as duas logos)
C_BG_DEEP = "#121419"      # Cinza Carvão Neutro Ultra-Escuro (Fundo Total)
C_CARD_BG = "#1F232B"     # Cinza Chumbo (Card de Login e Tabela)
C_PRIMARY = "#00C896"     # Teal Vibrante (React Glow / Destaques)
C_SECONDARY = "#FF8000"   # Laranja Vibrante (Títulos)
C_TEXT = "#FFFFFF"        # Branco (Texto Geral)
C_BORDER = "#2C323F"      # Cinza de Borda Neutro

# Função para converter imagem local em Base64 (Resolve Visibilidade no HTML)
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

# Injeção de CSS Dark Premium Mobile-Focused
st.markdown(f"""
    <style>
        /* Define fundo escuro neutro para toda a aplicação */
        .stApp {{
            background-color: {C_BG_DEEP};
            color: {C_TEXT};
        }}
        
        /* Esconder menus padrão */
        [data-testid="stSidebar"], #MainMenu, footer {{display: none;}}
        .main .block-container {{padding-top: 1.5rem;}}

        /* Centralizar login e Estilo React-style */
        .login-card {{
            text-align: center; 
            max-width: 500px; /* Levemente maior para mobile */
            margin: 4rem auto; 
            padding: 45px 35px; /* Mais padding para mobile */
            border: 1px solid {C_BORDER}; 
            border-radius: 20px; 
            box-shadow: 0 10px 40px rgba(0,200,150,0.15); /* Neon Glow Teal suave */
            background-color: {C_CARD_BG};
        }}

        /* Customizar inputs Streamlit para o Tema Dark */
        .stTextInput>div>div>input {{
            background-color: #1A1D24 !important; /* Ligeiramente mais escuro que o card */
            color: {C_TEXT} !important;
            border-radius: 12px !important;
            border-color: {C_BORDER} !important;
            padding: 14px !important; /* Maior área de toque mobile */
            font-size: 16px !important;
        }}
        .stTextInput>div>div>input:focus {{
            border-color: {C_PRIMARY} !important;
            box-shadow: 0 0 0 0.3rem rgba(0,200,150,0.2) !important;
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
            color: {C_BG_DEEP};
            border: none;
            border-radius: 12px; height: 3.8em; font-weight: bold; 
            font-size: 17px;
            transition: all 0.3s ease;
            width: 100%;
        }}
        .stButton>button[kind="primary"]:hover {{
            background-color: {C_SECONDARY};
            color: white;
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(255,128,0,0.4);
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

    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO SEGURA
# ==========================================
@st.cache_resource
def init_connections():
    try:
        db_alunos = create_client(st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"])
        db_provas = create_client(st.secrets["SUPABASE_URL_PROVAS"], st.secrets["SUPABASE_KEY_PROVAS"])
        return db_alunos, db_provas
    except Exception as e:
        st.error(f"Erro de Conexão: Verifique st.secrets. Detalhes: {e}")
        st.stop()

db_alunos, db_provas = init_connections()

# ==========================================
# 3. ESTADO DA SESSÃO
# ==========================================
for key in ['etapa', 'aluno', 'prova_config', 'tempo_final', 'questoes', 'respostas']:
    if key not in st.session_state:
        if key == 'etapa': st.session_state[key] = "login"
        elif key == 'respostas': st.session_state[key] = {}
        else: st.session_state[key] = None

# ==========================================
# ETAPA 1: LOGIN DARK ESTILIZADO (RESOLVE PRINT 2 + CORREÇÃO DESIGN)
# ==========================================
if st.session_state.etapa == "login":
    # Estrutura HTML do Card com imagens em Base64 e Proporção Corrigida
    st.markdown(f"""
        <div class="login-card">
            <div style="display: flex; justify-content: space-around; align-items: center; margin-bottom: 40px; padding: 0 10px;">
                <img src="data:image/png;base64,{logo_erempam_b64}" width="115" alt="EREMPAM Logo"/>
                <img src="data:image/png;base64,{logo_lardiao_b64}" width="140" alt="Lardião Logo"/>
            </div>
            <h1 style="color: {C_PRIMARY}; font-size: 30px; margin-bottom: 10px; font-weight: bold;">Portal de Avaliações</h1>
            <h2 style="color: {C_SECONDARY}; font-weight: normal; font-size: 21px; margin-bottom: 40px;">do Prof. Lardião</h2>
        </div>
    """, unsafe_allow_html=True)

    # Inputs posicionados abaixo do card HTML
    col1, col2, col3 = st.columns([1, 1.9, 1])
    with col2:
        matricula = st.text_input("Sua Matrícula SIGEREMPAM:", placeholder="Digite apenas números...")
        # Espaçador
        st.markdown("<br>", unsafe_allow_html=True)
        btn_acesso = st.button("ACESSAR SISTEMA PRO", type="primary")
        
        if btn_acesso and matricula:
            with st.spinner("Autenticando..."):
                try:
                    res = db_alunos.table("alunos").select("*").eq("numero_matricula", matricula).execute()
                    if res.data:
                        aluno_data = res.data[0]
                        st.session_state.aluno = aluno_data
                        st.session_state.etapa = "ante_sala"
                        st.rerun()
                    else:
                        st.error("Matrícula SIGEREMPAM não encontrada. Verifique os números.")
                except Exception as e:
                    st.error(f"Erro Crítico de conexão: {e}")

# ==========================================
# ETAPA 2: ANTE-SALA DARK (RESOLVE PRINT 2 + TEMA DARK)
# ==========================================
elif st.session_state.etapa == "ante_sala":
    aluno = st.session_state.aluno
    turma_bruta = str(aluno.get('turma', ''))
    serie_aluno = "1º Ano"
    if "2" in turma_bruta: serie_aluno = "2º Ano"
    elif "3" in turma_bruta: serie_aluno = "3º Ano"

    # Título com Destaque Vibrante React-style
    st.markdown(f"""
        <div style="margin-bottom: 30px;">
            <h1 style="color: {C_TEXT}; margin-bottom: 8px;">👋 Olá, <span style="color: {C_SECONDARY};">{aluno['nome']}</span>!</h1>
            <p style="color: #AAA; font-size: 16px;">Sua série é o <strong>{serie_aluno}</strong>. Confira suas atividades pendentes.</p>
        </div>
    """, unsafe_allow_html=True)

    with st.spinner("Buscando avaliações disponíveis..."):
        try:
            # 1. Provas Ativas para a série
            res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).execute()
            provas_ativas = res_p.data
            
            # 2. Verificar o que já foi feito (CORREÇÃO res_JF blindada)
            ids_ativas = [p['id'] for p in provas_ativas]
            ja_fez_dict = {}
            if ids_ativas:
                res_JF = db_provas.table("resultados_provas").select("prova_id").eq("aluno_id", str(aluno['id'])).in_("prova_id", ids_ativas).execute()
                ja_fez_dict = {x['prova_id']: True for x in res_JF.data}

            # 3. CONSTRUÇÃO DA TABELA HTML DARK COMPLETA
            if provas_ativas:
                # Cabeçalho React-style
                html_tabela = f"""
                    <div class="pro-table-container">
                    <table class="pro-table">
                        <thead>
                            <tr>
                                <th>Atividade Avaliativa</th>
                                <th style="text-align:center;">Pontos Máx.</th>
                                <th>Disponível Até</th>
                                <th style="text-align:center;">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                ha_pendentes = False
                for p in provas_ativas:
                    # Cálculos baseados na regra de sorteio
                    q_sorteio = p.get('qtd_sorteio', p.get('qtd_questoes', 1))
                    valor_total = q_sorteio * p.get('valor_questao', 1.0)
                    
                    # Data formatada para mobile
                    dt_limite = datetime.fromisoformat(p['data_limite']).strftime("%d/%m/%Y às %H:%M")
                    
                    # Status e Lógica
                    foi_feita = ja_fez_dict.get(p['id'], False)
                    status_html = '<span class="badge-status status-done">✅ Feita</span>' if foi_feita else '<span class="badge-status status-pending">🔵 Pendente</span>'
                    
                    if not foi_feita: ha_pendentes = True

                    html_tabela += f"""
                        <tr>
                            <td>
                                <strong style="color: {C_PRIMARY}; font-size: 16px;">{p['titulo']}</strong><br>
                                <span style="color:#A0A0A0; font-size:12px;">Assunto: {p.get('assunto','Química Pro')}</span>
                            </td>
                            <td style="text-align:center; font-weight: bold; color: {C_TEXT}; font-size: 15px;">{valor_total:.1f}</td>
                            <td style="color: #CCC; font-size: 14px;">{dt_limite}</td>
                            <td style="text-align:center;">{status_html}</td>
                        </tr>
                    """
                
                # FECHAMENTO DA TABELA (Resolve travamento do Print 2)
                html_tabela += "</tbody></table></div>"
                st.markdown(html_tabela, unsafe_allow_html=True)
                
                # 4. Botões Streamlit para iniciar (abaixo da tabela)
                if ha_pendentes:
                    st.divider()
                    st.markdown("### ✍️ Iniciar Atividade Avaliativa")
                    # Cria colunas dinâmicas para os botões de início
                    # Blindagem para evitar erro se houver muitas provas
                    num_btn = len([x for x in provas_ativas if not ja_fez_dict.get(x['id'], False)])
                    cols_btn = st.columns(max(num_btn, 1))
                    
                    idx_col = 0
                    for p in provas_ativas:
                        if not ja_fez_dict.get(p['id'], False):
                            with cols_btn[idx_col]:
                                if st.button(f"Iniciar: {p['titulo']}", key=f"btn_init_{p['id']}", type="primary"):
                                    st.session_state.prova_config = p
                                    st.session_state.etapa = "instrucoes"
                                    st.rerun()
                            idx_col += 1
            else:
                st.success("🎉 Excelente! Você concluiu todas as atividades avaliativas disponíveis.")
                
        except Exception as e:
            st.error(f"Erro ao carregar atividades avaliativas: {e}")

# ==========================================
# ETAPA 3: INSTRUÇÕES E SORTEIO
# ==========================================
elif st.session_state.etapa == "instrucoes":
    # (Mantido como antes, focado na semente estável)
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    st.header(f"👋 Preparado, {aluno['nome']}?")
    
    with st.container(border=True):
        st.subheader(f"📝 {prova['titulo']}")
        st.write(f"Série: {prova['serie']} | Tempo de Execução: **{prova['tempo_duracao']} minutos**")
        
        st.markdown(f"""
            **Instruções Importantes:**
            1. Você terá estatisticamente {prova['tempo_duracao']} minutos para concluir após clicar no botão abaixo.
            2. Não atualize ou feche o navegador durante a prova.
            3. Responda todas as questões e clique em 'Enviar' ao final.
        """)
        
        if st.button("ESTOU PRONTO, INICIAR PROVA AGORA", type="primary", use_container_width=True, key="btn_start"):
            with st.spinner("Gerando sua avaliação única e randomizada..."):
                # Define tempo final
                st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
                
                # Busca POOL de questões
                ids = prova.get('questoes_ids', [])
                res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
                pool_questoes = res_q.data
                
                # SORTEIO ESTÁVEL POR ALUNO
                random.seed(str(aluno['id']))
                random.shuffle(pool_questoes)
                
                # Corta pela quantidade definida no campo 'qtd_sorteio'
                n_sorteio = prova.get('qtd_sorteio', len(pool_questoes))
                st.session_state.questoes = pool_questoes[:n_sorteio]
                
                st.session_state.etapa = "em_prova"
                st.rerun()

# ==========================================
# ETAPA 4: EXECUÇÃO DA PROVA (RANDOMIZAÇÃO DE ALTERNATIVAS - PRO DARK)
# ==========================================
elif st.session_state.etapa == "em_prova":
    import streamlit.components.v1 as components
    
    # Validação de segurança
    if not st.session_state.questoes or not st.session_state.tempo_final:
        st.session_state.etapa = "login"
        st.rerun()

    restante = st.session_state.tempo_final - datetime.now()
    segs = int(restante.total_seconds())
    
    if segs <= 0:
        st.error("⌛ TEMPO ESGOTADO! Infelizmente, suas respostas não foram enviadas a tempo.")
        if st.button("Voltar ao Portal Pro", type="secondary"):
            st.session_state.clear()
            st.rerun()
        st.stop()

    # Cabeçalho da Prova Mobile React-style
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
            <h2 style="color: {C_TEXT}; font-size: 24px;">✍️ {st.session_state.prova_config['titulo']}</h2>
            <p style="color: #AAA; font-size: 14px;">Aluno: {st.session_state.aluno['nome']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Início do Formulário Dark Pro
    with st.form("form_prova", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questoes):
            # Container estilizado para cada questão
            st.markdown(f"""
                <div style="background-color: {C_CARD_BG}; padding: 25px; border-radius: 12px; border: 1px solid {C_BORDER}; margin-bottom: 25px;">
                    <strong style="color: {C_PRIMARY}; font-size: 18px; display: block; margin-bottom: 15px;">QUESTÃO {i+1}</strong>
            """, unsafe_allow_html=True)
            
            # Renderiza enunciado HTML
            st.markdown(q['enunciado'], unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True) # Fecha container
            
            # --- LÓGICA DE ALTERNATIVAS RANDOMIZADAS E LIMPIS ---
            opcoes_dict = q.get('alternativas', {}) 
            letras_originais = [l for l in ["A", "B", "C", "D", "E"] if opcoes_dict.get(l)]
            
            # Semente única por Questão + Aluno
            random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
            ordem = letras_originais.copy()
            random.shuffle(ordem)

            # Nova função SUPER limpadora (Tira HTML e sujeiras)
            def limpar_alternativa(texto_cru):
                t_sem_html = re.sub(r'<[^>]+>', '', str(texto_cru)) # Tira tags HTML
                t_limpo = re.sub(r'^\s*[A-Ea-e]\s*[\)\.\-]\s*', '', t_sem_html).strip() # Tira "A) ", "B. "
                return t_limpo

            # Desenha o rádio button Streamlit
            st.markdown("<strong style='font-size:15px; color:#FFFFFF'>Selecione a alternativa correta:</strong>", unsafe_allow_html=True)
            escolha = st.radio(
                f"Radio_Q{i+1}", # Label escondida
                options=ordem, 
                format_func=lambda x: f"{x}) {limpar_alternativa(opcoes_dict.get(x, ''))}",
                index=None, 
                key=f"q_{q['id']}", # Chave única Supabase
                label_visibility="collapsed" # Esconde label para ficar limpo
            )
            
            if escolha:
                # Salva apenas a letra original (ex: 'C')
                st.session_state.respostas[q['id']] = escolha 
            st.markdown("<br><br>", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        # Botão de envio PRO
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR AVALIAÇÃO PRO", type="primary")

    if entregar:
        if len(st.session_state.respostas) < len(st.session_state.questoes):
            st.warning("⚠️ Atenção! Você precisa responder todas as questões antes de enviar.")
        else:
            with st.spinner("Processando suas respostas e calculando nota..."):
                # Cálculo da Nota baseada no valor individual configurado pelo Professor
                valor_cada = st.session_state.prova_config.get('valor_questao', 1.0)
                acertos = 0
                for q in st.session_state.questoes:
                    if st.session_state.respostas.get(q['id']) == q['resposta_correta']:
                        acertos += 1
                
                # Prepara dados para inserção no banco resultados_provas
                lista_resultados = []
                for q in st.session_state.questoes:
                    resp_aluno = st.session_state.respostas.get(q['id'])
                    lista_resultados.append({
                        "aluno_id": str(st.session_state.aluno['id']), 
                        "prova_id": st.session_state.prova_config['id'],
                        "questao_id": q['id'],
                        "resposta_aluno": resp_aluno,
                        "acertou": (resp_aluno == q['resposta_correta']),
                        "acertos": acertos # Score total na prova
                    })
                
                try:
                    # Envia em lote
                    db_provas.table("resultados_provas").insert(lista_resultados).execute()
                    # Vai para etapa final
                    st.session_state.etapa = "resultado_final"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro Crítico ao salvar resultado no banco de dados: {e}")

# ==========================================
# ETAPA 5: RESULTADO E MISTÉRIO DO PROFESSOR (PREPARAÇÃO IA)
# ==========================================
elif st.session_state.etapa == "resultado_final":
    aluno = st.session_state.aluno
    # Coleta total de acertos baseados no envio anterior
    # CORREÇÃO Blindada do res_JF
    res_JF = db_provas.table("resultados_provas").select("acertos").eq("aluno_id", str(aluno['id'])).eq("prova_id", st.session_state.prova_config['id']).limit(1).execute()
    total_acertos = res_JF.data[0]['acertos'] if res_JF.data else 0
    total_questoes = len(st.session_state.questoes)

    st.balloons() # Celebração React-style
    st.markdown(f"""
        <div style="text-align: center; margin-top: 3.5rem;">
            <h1 style="color: {C_PRIMARY}; font-size: 42px; font-weight: bold;">🎉 Avaliação Concluída!</h1>
            <p style="color: #A0A0A0; font-size: 19px; margin-top: 10px;">Parabéns, {aluno['nome']}. Suas respostas foram enviadas e processadas.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Card de Nota Dark chique
    st.markdown(f"""
        <div style="background-color: {C_CARD_BG}; padding: 35px; border-radius: 20px; border: 2px solid {C_PRIMARY}; max-width: 550px; margin: 2.5rem auto; text-align: center; box-shadow: 0 10px 30px rgba(0,200,150,0.1);">
            <h2 style="color: {C_TEXT}; margin-bottom: 12px; font-size: 24px;">Sua Nota na {st.session_state.prova_config['titulo']}</h2>
            <div style="font-size: 70px; font-weight: bold; color: {C_SECONDARY}; margin: 15px 0;">
                {total_acertos * st.session_state.prova_config.get('valor_questao', 1.0):.1f}
            </div>
            <p style="color: #CCC; font-size: 19px;">Você acertou <strong>{total_acertos}</strong> de <strong>{total_questoes}</strong> questões.</p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- PLACEHOLDERS FASE 3 (IA + RANKING) - VISUAL DARK ---
    colR1, colR2 = st.columns(2)
    
    with colR1:
        st.markdown(f"""
            <div style="background-color: {C_CARD_BG}; padding: 25px; border-radius: 12px; border: 1px solid {C_BORDER}; text-align: center; height: 180px;">
                <h3 style="color: {C_PRIMARY}; font-size: 20px; margin-bottom: 10px;">🌎 Ranking Gamificado</h3>
                <p style="color: #ffc107; font-weight: bold; font-size: 18px; margin: 15px 0;">⌛ CALCULANDO...</p>
                <p style="color: #A0A0A0; font-size: 14px;">O Prof. Lardião está calculando sua posição na turma e entre todos os terceiros!</p>
            </div>
        """, unsafe_allow_html=True)
        
    with colR2:
        st.markdown(f"""
            <div style="background-color: {C_CARD_BG}; padding: 25px; border-radius: 12px; border: 1px solid {C_BORDER}; text-align: center; height: 180px;">
                <h3 style="color: {C_PRIMARY}; font-size: 20px; margin-bottom: 10px;">🧠 Feedback do Mestre</h3>
                <p style="color: #ffc107; font-weight: bold; font-size: 18px; margin: 15px 0;">⌛ AGUARDE!</p>
                <p style="color: #A0A0A0; font-size: 14px;">O Prof. Lardião está analisando seu desempenho para te dar uma dica de mestre personalizada em instantes...</p>
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    if st.button("⬅️ Voltar para o Portal Pro", type="secondary", use_container_width=True):
        st.session_state.clear() # Limpa tudo e volta pro login
        st.rerun()