import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import time
import re
import random 

# ==========================================
# 1. CONFIGURAÇÕES, IDENTIDADE E ESTILO (CSS PRO)
# ==========================================
# Deve ser a PRIMEIRA coisa do script
st.set_page_config(
    page_title="Portal de Avaliações | Química com Lardião", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="logo_erempam.png"
)

# Paleta de cores baseada nas logos (Teal/Laranja)
C_PRIMARY = "#00C896" # Teal da logo Lardião
C_SECONDARY = "#FF8000" # Laranja da logo Lardião
C_BG_TABLE = "#f8f9fa"

# Injeção de CSS para customizar Streamlit e HTML
st.markdown(f"""
    <style>
        /* Esconder Sidebar e Menu padrão */
        [data-testid="stSidebar"] {{display: none;}}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        .main .block-container {{padding-top: 2rem;}}

        /* Centralizar login */
        .login-card {{
            text-align: center; 
            max-width: 450px; 
            margin: 5rem auto; 
            padding: 40px; 
            border: 1px solid #ddd; 
            border-radius: 15px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            background-color: white;
        }}

        /* Customizar inputs e botões padrão do Streamlit */
        .stButton>button {{
            border-radius: 8px; height: 3.5em; font-weight: bold; 
            transition: all 0.3s;
        }}
        .stButton>button:hover {{
            background-color: {C_SECONDARY} !important;
            border-color: {C_SECONDARY} !important;
            color: white !important;
            transform: translateY(-2px);
        }}
        .stTextInput>div>div>input {{
            border-radius: 8px !important;
            border-color: #ccc !important;
            padding: 10px !important;
        }}
        .stTextInput>div>div>input:focus {{
            border-color: {C_SECONDARY} !important;
            box-shadow: 0 0 0 0.2rem rgba(255,128,0,0.25) !important;
        }}

        /* Estilo da Tabela Profissional na Ante-sala */
        .pro-table {{
            width: 100%; border-collapse: collapse; 
            margin-top: 20px; font-family: sans-serif;
        }}
        .pro-table thead tr {{
            background-color: {C_PRIMARY}; color: white;
            text-align: left; font-weight: bold;
        }}
        .pro-table th, .pro-table td {{ padding: 15px 20px; border-bottom: 1px solid #eee; }}
        .pro-table tbody tr:nth-of-type(even) {{ background-color: {C_BG_TABLE}; }}
        .pro-table tbody tr:last-of-type {{ border-bottom: 2px solid {C_PRIMARY}; }}

        /* Badges de Status na Tabela */
        .badge-status {{
            padding: 5px 10px; border-radius: 12px; font-weight: bold; font-size: 12px;
        }}
        .status-done {{ background-color: #d4edda; color: #155724; }}
        .status-pending {{ background-color: #fff3cd; color: #856404; }}

        /* Cronômetro sticky */
        .timer-container {{
            position: sticky; top: 0; z-index: 999;
            background-color: white; padding: 10px 0;
            border-bottom: 2px solid #eee;
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
# ETAPA 1: LOGIN ESTILIZADO (FASE 1)
# ==========================================
if st.session_state.etapa == "login":
    # Estrutura HTML do Card de Login centralizado
    st.markdown(f"""
        <div class="login-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
                <img src="app/static/logo_erempam.png" width="90" alt="EREMPAM"/>
                <img src="app/static/logo_quimica.png" width="130" alt="Lardião"/>
            </div>
            <h2 style="color: {C_PRIMARY}; margin-bottom: 10px;">Bem-vindo ao Portal de Avaliações</h2>
            <h3 style="color: {C_SECONDARY}; font-weight: normal; margin-bottom: 30px;">do Prof. Lardião</h3>
        </div>
    """, unsafe_allow_html=True)

    # Inputs Streamlit posicionados logicamente dentro do fluxo, mas estilizados pelo CSS acima
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        matricula = st.text_input("Digite sua Matrícula para Acessar:", placeholder="Ex: 2024123", key="mat_input")
        btn_acesso = st.button("ACESSAR SISTEMA", use_container_width=True, type="primary", key="btn_acesso")
        
        if btn_acesso and matricula:
            with st.spinner("Autenticando na base SIGEREMPAM..."):
                try:
                    res = db_alunos.table("alunos").select("*").eq("numero_matricula", matricula).execute()
                    if res.data:
                        aluno_data = res.data[0]
                        st.session_state.aluno = aluno_data
                        # Mudar de etapa para a ante-sala
                        st.session_state.etapa = "ante_sala"
                        st.rerun()
                    else:
                        st.error("Matrícula não encontrada. Procure a secretaria.")
                except Exception as e:
                    st.error(f"Erro na base de alunos: {e}")

# ==========================================
# ETAPA 2: ANTE-SALA PROFISSIONAL (FASE 2)
# ==========================================
elif st.session_state.etapa == "ante_sala":
    aluno = st.session_state.aluno
    # Lógica de tradução de turma para série
    turma_bruta = aluno.get('turma', '')
    serie_aluno = "1º Ano"
    if "2" in turma_bruta: serie_aluno = "2º Ano"
    elif "3" in turma_bruta: serie_aluno = "3º Ano"

    st.header(f"👋 Olá, {aluno['nome']}! Sua série é o {serie_aluno}.")
    st.markdown("Confira suas atividades disponíveis para execução.")

    # 1. Busca provas ATIVAS para a série
    with st.spinner("Carregando atividades..."):
        try:
            res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).execute()
            provas_ativas = res_p.data
            
            # 2. Busca o que o aluno JÁ FEZ dessas provas
            ids_ativas = [p['id'] for p in provas_ativas]
            ja_fez_dict = {}
            if ids_ativas:
                res_jf = db_provas.table("resultados_provas").select("prova_id, id").eq("aluno_id", str(aluno['id'])).in_("prova_id", ids_ativas).execute()
                ja_fez_dict = {x['prova_id']: True for x in res_jf.data} # Marca as provas feitas

            # 3. CONSTRUÇÃO DA TABELA HTML/CSS
            if provas_ativas:
                # Cabeçalho da tabela
                html_tabela = f"""
                    <table class="pro-table">
                        <thead>
                            <tr>
                                <th>Atividade</th>
                                <th style="text-align:center;">Valor Máx. (Pontos)</th>
                                <th>Data Limite</th>
                                <th style="text-align:center;">Status / Ação</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                # Linhas dinâmicas
                pode_gerar_botoes = False # Controle para o Streamlit
                for p in provas_ativas:
                    # Cálculo de valor (usando qtd_sorteio)
                    total_sorteio = p.get('qtd_sorteio', p.get('qtd_questoes', 1))
                    valor_max = total_sorteio * p.get('valor_questao', 1.0)
                    
                    # Formatação de data
                    data_obj = datetime.fromisoformat(p['data_limite'])
                    data_fmt = data_obj.strftime("%d/%m/%Y às %H:%M")
                    
                    status = ja_fez_dict.get(p['id'], False)
                    pode_gerar_botoes = True if not pode_gerar_botoes else True # Ativa os botões se houver ao menos uma prova

                    html_tabela += f"""
                        <tr>
                            <td><strong>{p['titulo']}</strong><br><span style="color:#666; font-size:12px;">Assunto: {p.get('assunto','Geral')}</span></td>
                            <td style="text-align:center;">{valor_max:.1f}</td>
                            <td>{data_fmt}</td>
                            <td style="text-align:center;">
                                {"✅ Realizada" if status else "🔵 Pendente"}
                            </td>
                        </tr>
                    """
                
                html_tabela += "</tbody></table>"
                st.markdown(html_tabela, unsafe_allow_html=True)
                
                # 4. Gerar Botões Streamlit correspondentes para "Iniciar" (abaixo da tabela)
                if pode_gerar_botoes:
                    st.divider()
                    st.markdown("👇 Selecione qual atividade pendente deseja realizar:")
                    for p in provas_ativas:
                        # Só gera botão para as pendentes
                        if not ja_fez_dict.get(p['id'], False):
                            if st.button(f"🔵 Iniciar: {p['titulo']}", key=f"btn_init_{p['id']}", use_container_width=True):
                                # Define a prova ativa no estado e muda de etapa
                                st.session_state.prova_config = p
                                st.session_state.etapa = "instrucoes"
                                st.rerun()
            else:
                st.info("No momento, não há atividades avaliativas pendentes para você.")
                
        except Exception as e:
            st.error(f"Erro ao carregar ante-sala: {e}")

# ==========================================
# ETAPA 3: INSTRUÇÕES E SORTEIO (FASE 3 - PREPARAÇÃO)
# ==========================================
elif st.session_state.etapa == "instrucoes":
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    st.header(f"👋 Olá, {aluno['nome']}!")
    
    with st.container(border=True):
        st.subheader(f"📝 {prova['titulo']}")
        st.write(f"Série: {prova['serie']} | Tempo: {prova['tempo_duracao']} min")
        
        if st.button("INICIAR PROVA AGORA", type="primary", use_container_width=True, key="btn_start"):
            with st.spinner("Randomizando suas questões..."):
                # 1. Define tempo final
                st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
                
                # 2. Busca o POOL completo de questões
                ids = prova.get('questoes_ids', [])
                res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
                pool_questoes = res_q.data
                
                # 3. Lógica de SORTEIO ESTÁVEL POR ALUNO
                # Usamos o ID do aluno como semente para o sorteio ser fixo para ele (UUID blindado como string)
                random.seed(str(aluno['id']))
                random.shuffle(pool_questoes)
                
                # Quantidade definida no banco no campo 'qtd_sorteio'
                n_sorteio = prova.get('qtd_sorteio', len(pool_questoes))
                questoes_sorteadas = pool_questoes[:n_sorteio]
                
                # Salva o subconjunto no estado
                st.session_state.questoes = questoes_sorteadas
                st.session_state.etapa = "em_prova"
                st.rerun()

# ==========================================
# ETAPA 4: EXECUÇÃO DA PROVA (RANDOMIZAÇÃO DE ALTERNATIVAS - PRO)
# ==========================================
elif st.session_state.etapa == "em_prova":
    import streamlit.components.v1 as components
    
    restante = st.session_state.tempo_final - datetime.now()
    segs = int(restante.total_seconds())
    
    if segs <= 0:
        st.error("⌛ TEMPO ESGOTADO! Suas respostas não foram enviadas.")
        # Lógica de auto-envio poderia entrar aqui
        st.stop()

    # Cabeçalho da Prova
    st.markdown(f"### ✍️ {st.session_state.prova_config['titulo']}")
    
    # Início do Formulário da Prova
    with st.form("form_prova", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questoes):
            st.markdown(f"**QUESTÃO {i+1}**")
            # Renderiza enunciado HTML
            st.markdown(q['enunciado'], unsafe_allow_html=True)
            
            # --- LÓGICA DE ALTERNATIVAS RANDOMIZADAS ---
            opcoes_dict = q.get('alternativas', {}) 
            letras_originais = [letra for letra in ["A", "B", "C", "D", "E"] if opcoes_dict.get(letra)]
            
            ordem_alternativas = letras_originais.copy()
            # Semente única por Questão + Aluno
            random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
            random.shuffle(ordem_alternativas)

            # Nova função SUPER limpadora (Tira HTML e sujeiras)
            def limpar_texto_alternativa(texto_cru):
                # 1. Remove qualquer tag HTML que venha do editor de texto do banco
                texto_sem_html = re.sub(r'<[^>]+>', '', str(texto_cru))
                # 2. Remove o padrão "A)", "B-", "C." se houver
                texto_limpo = re.sub(r'^\s*[A-Ea-e]\s*[\)\.\-]\s*', '', texto_sem_html).strip()
                return texto_limpo

            # Desenha o rádio com alternatives embaralhadas e texto forçado limpo
            escolha = st.radio(
                f"Sua resposta para a Q{i+1}:", 
                options=ordem_alternativas, 
                format_func=lambda x: f"{x}) {limpar_texto_alternativa(opcoes_dict.get(x, ''))}",
                index=None, 
                key=f"q_{q['id']}" 
            )
            
            if escolha:
                # Salva apenas a letra original (ex: 'C')
                st.session_state.respostas[q['id']] = escolha 
            st.divider()
            
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR AVALIAÇÃO", use_container_width=True, type="primary")

    if entregar:
        if len(st.session_state.respostas) < len(st.session_state.questoes):
            st.warning("⚠️ Responda todas as questões antes de finalizar!")
        else:
            with st.spinner("Enviando respostas e calculando nota..."):
                # Cálculo da Nota
                valor_cada = st.session_state.prova_config.get('valor_questao', 1.0)
                acertos_totais = 0
                for q in st.session_state.questoes:
                    if st.session_state.respostas.get(q['id']) == q['resposta_correta']:
                        acertos_totais += 1
                
                # Prepara dados para inserção no banco
                lista_resultados = []
                for q in st.session_state.questoes:
                    resposta_dada = st.session_state.respostas.get(q['id'])
                    acertou = (resposta_dada == q['resposta_correta'])
                    
                    lista_resultados.append({
                        "aluno_id": str(st.session_state.aluno['id']), 
                        "prova_id": st.session_state.prova_config['id'],
                        "questao_id": q['id'],
                        "resposta_aluno": resposta_dada,
                        "acertou": acertou,
                        "acertos": acertos_totais # Score total na prova
                    })
                
                try:
                    # Envia tudo de uma vez
                    db_provas.table("resultados_provas").insert(lista_resultados).execute()
                    # Muda para a etapa de resultado final
                    st.session_state.etapa = "resultado_final"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro Crítico ao salvar resultado: {e}")

# ==========================================
# ETAPA 5: RESULTADO E MISTÉRIO DO PROFESSOR (FASE 3 - PREPARAÇÃO)
# ==========================================
elif st.session_state.etapa == "resultado_final":
    aluno = st.session_state.aluno
    # Coleta total de acertos baseados no envio anterior (Erro de digitação res_JF corrigido!)
    res_JF = db_provas.table("resultados_provas").select("acertos").eq("aluno_id", str(aluno['id'])).eq("prova_id", st.session_state.prova_config['id']).limit(1).execute()
    total_acertos = res_JF.data[0]['acertos'] if res_JF.data else 0
    total_sorteio = len(st.session_state.questoes) # Quantas questões ele fez

    st.success("🎉 Avaliação enviada com sucesso!")
    
    with st.container(border=True):
        st.markdown(f"## Sua Nota na {st.session_state.prova_config['titulo']}")
        c1, c2 = st.columns(2)
        
        with c1:
            st.metric("Acertos", f"{total_acertos} / {total_sorteio}")
        
        with c2:
            st.metric("Nota Final", f"{total_acertos * st.session_state.prova_config.get('valor_questao', 1.0):.1f}")

    st.divider()

    # --- PLACEHOLDERS FASE 3 (IA + RANKING) ---
    colR1, colR2 = st.columns(2)
    
    with colR1:
        st.markdown("### 🌎 Ranking Gamificado")
        st.info("⌛ Em breve, você verá sua posição na turma e entre todos os terceiros!")
        
    with colR2:
        st.markdown("### 🧠 Feedback do Professor Lardião")
        st.warning("Aguarde! O Professor Lardião está analisando seu desempenho para te dar uma dica de mestre personalizada em instantes...")

    st.divider()
    if st.button("⬅️ Voltar para o Portal", type="secondary"):
        # Limpa o estado e volta pro login
        st.session_state.clear()
        st.rerun()