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
st.set_page_config(
    page_title="Portal de Avaliações | Química com Lardião Pro", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="logo_erempam.png" 
)

C_BG_DEEP = "#F0F4F8"      
C_CARD_BG = "#FFFFFF"     
C_PRIMARY = "#00C896"     
C_SECONDARY = "#FF8000"   
C_TEXT = "#2D3748"        
C_TEXT_MUTED = "#718096"  
C_BORDER = "#E2E8F0"      

def get_base64_image(image_path):
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except Exception as e:
            st.error(f"Erro ao ler imagem {image_path}: {e}")
    return ""

logo_erempam_b64 = get_base64_image("logo_erempam.png")
logo_lardiao_b64 = get_base64_image("logo_lardiao.png")

st.markdown(f"""
    <style>
        /* 1. BLINDAGEM CONTRA O DARK MODE DO CELULAR */
        .stApp {{ background-color: {C_BG_DEEP} !important; }}
        
        /* Força TODOS os textos normais, marcações e radio buttons a ficarem escuros */
        .stApp p, .stApp span, .stApp label, .stMarkdown p {{
            color: {C_TEXT} !important;
        }}
        
        /* Força especificamente as alternativas (radio) a aparecerem e com bom tamanho */
        div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {{
            color: {C_TEXT} !important;
            font-size: 16px !important;
        }}

        /* 2. OCULTAR ELEMENTOS DO STREAMLIT */
        [data-testid="stSidebar"] {{display: none;}}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        .main .block-container {{padding-top: 1.5rem;}}

        /* 3. ESTILOS DOS CARDS E BOTÕES (Seus estilos originais mantidos) */
        .login-card {{
            text-align: center; max-width: 500px; margin: 4rem auto; 
            padding: 45px 35px; border: 1px solid {C_BORDER}; 
            border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); 
            background-color: {C_CARD_BG};
        }}

        .stTextInput>div>div>input {{
            background-color: #F7FAFC !important; color: {C_TEXT} !important;
            border-radius: 12px !important; border-color: {C_BORDER} !important;
            padding: 14px !important; font-size: 16px !important;
        }}
        .stTextInput>div>div>input:focus {{
            border-color: {C_PRIMARY} !important;
            box-shadow: 0 0 0 0.2rem rgba(0,200,150,0.2) !important;
            background-color: #FFFFFF !important;
        }}
        .stTextInput>label {{ color: {C_TEXT} !important; font-weight: bold; font-size: 14px; }}

        .stButton>button[kind="primary"] {{
            background-color: {C_PRIMARY}; color: #FFFFFF; border: none;
            border-radius: 12px; height: 3.8em; font-weight: bold; font-size: 17px;
            transition: all 0.3s ease; width: 100%;
        }}
        .stButton>button[kind="primary"]:hover {{
            background-color: {C_SECONDARY}; color: white;
            transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,128,0,0.3);
        }}

        .pro-table-container {{
            background-color: {C_CARD_BG}; border-radius: 15px; padding: 20px;
            border: 1px solid {C_BORDER}; margin-top: 20px;
        }}
        .pro-table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; color: {C_TEXT}; }}
        .pro-table thead tr {{ border-bottom: 2px solid {C_PRIMARY}; text-align: left; font-weight: bold; font-size: 14px; }}
        .pro-table th, .pro-table td {{ padding: 18px 15px; }}
        .pro-table tbody tr {{ border-bottom: 1px solid {C_BORDER}; transition: background 0.2s; }}
        .pro-table tbody tr:hover {{ background-color: rgba(0,200,150,0.05); }}

        .badge-status {{ padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; display: inline-block; }}
        .status-done {{ background-color: rgba(40, 167, 69, 0.2); color: #28a745; border: 1px solid #28a745; }}
        .status-pending {{ background-color: rgba(255, 193, 7, 0.2); color: #ffc107; border: 1px solid #ffc107; }}

        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {C_CARD_BG}; border-radius: 15px; border-color: {C_BORDER}; box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        }}
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
        st.error(f"Erro Crítico de Conexão: Verifique st.secrets. Detalhes: {e}")
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
# ETAPA 1: LOGIN 
# ==========================================
if st.session_state.etapa == "login":
    logo_lardiao_b64 = get_base64_image("logo_lardiao.png")

    st.markdown(f"""
        <style>
        .login-card-unificado {{
            background-color: {C_CARD_BG}; max-width: 450px; margin: auto;
            padding: 30px; border-radius: 25px; border: 1px solid {C_BORDER};
            box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center;
        }}
        .title-portal {{ color: {C_PRIMARY}; font-size: 24px; font-weight: 800; margin-top: 15px; font-family: sans-serif; }}
        div[data-baseweb="input"] {{ border-radius: 12px !important; border: 1px solid {C_BORDER} !important; }}
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([0.1, 1, 0.1])
    
    with col2:
        st.markdown(f"""
            <div class="login-card-unificado">
                <img src="data:image/png;base64,{logo_lardiao_b64}" width="135">
                <div class="title-portal">SISTEMA DE ATIVIDADES</div>
                <div style="color: {C_TEXT_MUTED}; margin-bottom: 25px;">do Prof. Lardião</div>
            </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown('<div style="margin-top: -100px; padding: 0 30px 40px 30px;">', unsafe_allow_html=True)
            
            # Limite de 7 caracteres na interface
            matricula = st.text_input("Digite sua matrícula:", label_visibility="collapsed", placeholder="Sua Matrícula (7 números)", max_chars=7)
            st.write("") 
            
            if st.button("ACESSAR SISTEMA PRO", use_container_width=True, type="primary"):
                if matricula:
                    mat_limpa = str(matricula).strip()
                    
                    # Validação de segurança: Exatamente 7 dígitos e apenas números
                    if len(mat_limpa) != 7 or not mat_limpa.isdigit():
                        st.warning("⚠️ Ops! A matrícula deve conter exatamente 7 números.")
                    else:
                        with st.spinner("Buscando dados no servidor..."):
                            try:
                                res = db_alunos.table("alunos").select("*").eq("numero_matricula", mat_limpa).execute()
                                
                                if res.data and len(res.data) > 0:
                                    st.session_state.aluno = res.data[0]
                                    st.session_state.etapa = "ante_sala"
                                    st.rerun() 
                                else:
                                    st.error(f"❌ Matrícula '{mat_limpa}' não encontrada.")
                                    
                            except Exception as e:
                                st.error("Erro ao conectar com o banco de dados das matrículas.")
                                st.code(f"Detalhes do erro: {e}")
                else:
                    st.warning("⚠️ Por favor, digite sua matrícula antes de acessar.")
            
            st.markdown("""
                <br>
                <a href="#" style="color: #94a3b8; text-decoration: none; font-size: 13px;">Dúvidas ou problemas? Clique aqui.</a>
                </div>
            """, unsafe_allow_html=True)

# ==========================================
# ETAPA 2: PORTAL DO ALUNO (ANTE-SALA + PERFIL)
# ==========================================
elif st.session_state.etapa == "ante_sala":
    if 'aluno' not in st.session_state or not st.session_state.aluno:
        st.session_state.etapa = "login"
        st.rerun()

    aluno = st.session_state.aluno
    
    # Cabeçalho de Boas-vindas
    st.markdown(f"""
        <div style="margin-bottom: 20px; padding: 15px; background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E2E8F0;">
            <h2 style="margin: 0; color: #1E293B;">👋 Olá, <span style="color: #00C896;">{aluno.get('nome').split()[0]}</span>!</h2>
            <p style="color: #64748b; margin: 0;">{aluno.get('turma')} | Matrícula: {aluno.get('numero_matricula')}</p>
        </div>
    """, unsafe_allow_html=True)

    # CRIAÇÃO DAS ABAS
    tab_atividades, tab_perfil = st.tabs(["📝 Atividades Disponíveis", "📊 Meu Desempenho & IA"])

    with tab_atividades:
        with st.spinner("Buscando atividades..."):
            # Lógica de busca de provas (mesma que você já tem)
            turma_bruta = str(aluno.get('turma', ''))
            serie_aluno = "1º Ano"
            if "2" in turma_bruta: serie_aluno = "2º Ano"
            elif "3" in turma_bruta: serie_aluno = "3º Ano"

            res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).execute()
            provas_ativas = res_p.data
            
            ja_fez_dict = {}
            if provas_ativas:
                ids_ativas = [p['id'] for p in provas_ativas]
                res_JF = db_provas.table("resultados_provas").select("prova_id").eq("aluno_id", str(aluno.get('id', ''))).in_("prova_id", ids_ativas).execute()
                ja_fez_dict = {x['prova_id']: True for x in res_JF.data}

            if provas_ativas:
                for p in provas_ativas:
                    foi_feita = ja_fez_dict.get(p['id'], False)
                    if not foi_feita:
                        with st.container(border=True):
                            col_t, col_b = st.columns([3, 1])
                            col_t.markdown(f"### {p['titulo']}")
                            col_t.caption(f"📚 Assunto: {p.get('assunto', 'Geral')}")
                            if col_b.button(f"🚀 Iniciar", key=f"start_{p['id']}", type="primary", use_container_width=True):
                                st.session_state.prova_config = p
                                st.session_state.etapa = "instrucoes"
                                st.rerun()
            else:
                st.info("Nenhuma atividade nova para sua série no momento.")

    with tab_perfil:
        st.markdown("### 🏆 Sua Jornada de Aprendizado")
        
        # 1. Busca Histórico Completo
        res_historico = db_provas.table("resultados_provas").select("prova_id, acertou").eq("aluno_id", str(aluno.get('id'))).execute()
        
        if res_historico.data:
            df_hist = pd.DataFrame(res_historico.data)
            total_questoes = len(df_hist)
            total_acertos = df_hist['acertou'].sum()
            precisao = (total_acertos / total_questoes * 100) if total_questoes > 0 else 0

            # Cards de Métricas
            m1, m2, m3 = st.columns(3)
            m1.metric("Provas Feitas", df_hist['prova_id'].nunique())
            m2.metric("Total de Acertos", f"{total_acertos}")
            m3.metric("Precisão Geral", f"{precisao:.1f}%")

            st.divider()

            # 2. ÁREA DO DIAGNÓSTICO IA (O que você pediu!)
            st.markdown("#### 🧙‍♂️ Diagnóstico do Mestre (IA)")
            res_ia = db_provas.table("feedback_ia_alunos").select("*").eq("aluno_id", str(aluno.get('id'))).order("created_at", desc=True).limit(1).execute()
            
            if res_ia.data:
                feedback = res_ia.data[0]
                st.info(f"**Último Feedback:**\n\n{feedback['diagnostico_pedagogico']}")
                st.caption(f"Gerado em: {feedback['created_at'][:10]}")
            else:
                st.warning("A IA ainda está analisando seu perfil. Faça mais atividades para liberar seu diagnóstico!")

            # 3. Lista de Provas Concluídas
            st.markdown("#### 📜 Histórico de Notas")
            # Buscar nomes das provas feitas
            ids_feitas = df_hist['prova_id'].unique().tolist()
            res_nomes_p = db_provas.table("modelos_prova").select("id, titulo, valor_questao, notas_liberadas").in_("id", ids_feitas).execute()
            
            for p_info in res_nomes_p.data:
                acertos_p = sum(1 for r in res_historico.data if r['prova_id'] == p_info['id'] and r['acertou'])
                nota_p = acertos_p * p_info['valor_questao']
                
                with st.expander(f"✅ {p_info['titulo']} - Nota: {nota_p:.1f}"):
                    if p_info['notas_liberadas']:
                        if st.button("🔍 Rever Erros e Gabarito", key=f"rev_{p_info['id']}"):
                            st.session_state.prova_resultado = p_info
                            st.session_state.etapa = "ver_meu_resultado"
                            st.rerun()
                    else:
                        st.caption("🔒 O professor ainda não liberou o gabarito detalhado desta prova.")
        else:
            st.write("Você ainda não realizou nenhuma atividade. Comece sua primeira prova para ver suas estatísticas!")

# ETAPA 3: INSTRUÇÕES E SORTEIO
# ==========================================
elif st.session_state.etapa == "instrucoes":
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    st.header(f"👋 Preparado, {aluno['nome']}?")
    
    with st.container(border=True):
        st.subheader(f"📝 {prova['titulo']}")
        st.write(f"Série: {prova['serie']} | Tempo de Execução: **{prova['tempo_duracao']} minutos**")
        
        st.markdown(f"""
            **Instruções Importantes Pro:**
            1. Você terá estatisticamente {prova['tempo_duracao']} minutos para concluir após clicar no botão abaixo.
            2. Não atualize ou feche o navegador AVALARDIAO durante a prova, ou seu progresso será perdido.
            3. Responda todas as questões e clique em 'Enviar' ao final.
        """)
        
        if st.button("ESTOU PRONTO, INICIAR PROVA AGORA", type="primary", use_container_width=True, key="btn_start"):
            with st.spinner("Gerando sua avaliação única e randomizada..."):
                st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
                
                ids = prova.get('questoes_ids', [])
                res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
                pool_questoes = res_q.data
                
                random.seed(str(aluno['id']))
                random.shuffle(pool_questoes)
                
                n_sorteio = prova.get('qtd_sorteio', len(pool_questoes))
                questoes_sorteadas = pool_questoes[:n_sorteio]
                
                st.session_state.questoes = questoes_sorteadas
                st.session_state.etapa = "em_prova"
                st.rerun()

# ==========================================
# ETAPA 4: EXECUÇÃO DA PROVA (VERSÃO TURBO)
# ==========================================
elif st.session_state.etapa == "em_prova":
    # 1. CSS para manter o cronômetro fixo e visível
    st.markdown(f"""
        <style>
            .stApp {{ background-color: #FFFFFF !important; }}
            .timer-container {{
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                background-color: white;
                padding: 15px;
                border-radius: 15px;
                border: 2px solid {C_PRIMARY};
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                text-align: center;
                min-width: 120px;
            }}
        </style>
    """, unsafe_allow_html=True)

    # 2. FUNÇÃO DO CRONÔMETRO ISOLADA (O SEGREDO!)
    @st.fragment(run_every="1s")
    def render_cronometro():
        restante = st.session_state.tempo_final - datetime.now()
        segs = int(restante.total_seconds())
        
        if segs <= 0:
            st.error("⌛ TEMPO ESGOTADO!")
            st.stop()
        
        mins, secs = divmod(segs, 60)
        cor = "#FF4B4B" if segs < 300 else C_PRIMARY
        
        st.markdown(f"""
            <div class="timer-container">
                <div style="font-size: 12px; color: #666; font-weight: bold;">TEMPO</div>
                <div style="font-size: 24px; color: {cor}; font-weight: 800; font-family: monospace;">
                    {mins:02d}:{secs:02d}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Chamar o cronômetro (ele vai rodar em paralelo sem travar os cliques)
    render_cronometro()

    # 3. CABEÇALHO DA PROVA
    st.markdown(f"## ✍️ {st.session_state.prova_config['titulo']}")
    st.caption(f"Aluno: {st.session_state.aluno['nome']} | Boa sorte, Bença!")

 # 4. FORMULÁRIO DE QUESTÕES
    with st.form("form_prova", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questoes):
            with st.container(border=True):
                # Usamos st.markdown com unsafe_allow_html=True para o enunciado
                # Assim, negritos e fórmulas que você fez no editor aparecem certo!
                st.markdown(f"### 📝 QUESTÃO {i+1}")
                st.markdown(f"<div style='font-size:1.1rem;'>{q['enunciado']}</div>", unsafe_allow_html=True)
                
                opcoes_dict = q.get('alternativas', {})
                letras_originais = [l for l in ["A", "B", "C", "D", "E"] if opcoes_dict.get(l)]
                
                # Semente para manter a ordem fixa
                random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
                ordem = letras_originais.copy()
                random.shuffle(ordem)

                # Função para limpar as tags <p> das alternativas (st.radio não aceita HTML)
                def limpar_txt(t):
                    return re.sub(r'<[^>]+>', '', str(t)).strip()

                # Exibição das alternativas
                escolha = st.radio(
                    f"Assinale a alternativa correta para a questão {i+1}:",
                    options=ordem,
                    format_func=lambda x: f"({x}) {limpar_txt(opcoes_dict.get(x, ''))}",
                    index=None,
                    key=f"radio_q_{q['id']}" 
                )
        
        st.markdown("<br>", unsafe_allow_html=True)
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR PROVA", type="primary", use_container_width=True)

    # 5. LÓGICA DE ENVIO
    if entregar:
        # Coleta as respostas das 'keys' do session_state
        respostas_aluno = {}
        for q in st.session_state.questoes:
            chave = f"radio_q_{q['id']}"
            if chave in st.session_state and st.session_state[chave] is not None:
                respostas_aluno[q['id']] = st.session_state[chave]

        if len(respostas_aluno) < len(st.session_state.questoes):
            st.warning("⚠️ Bença, responda todas as questões antes de enviar!")
        else:
            with st.spinner("Salvando no Pergaminho..."):
                # ... (Aqui entra sua lógica de cálculo de acertos e db_provas.insert)
                # Use o dicionário 'respostas_aluno' para calcular a nota
                acertos = sum(1 for q in st.session_state.questoes if respostas_aluno.get(q['id']) == q['resposta_correta'])
                
                lista_resultados = []
                for q in st.session_state.questoes:
                    lista_resultados.append({
                        "aluno_id": str(st.session_state.aluno['id']),
                        "prova_id": st.session_state.prova_config['id'],
                        "questao_id": q['id'],
                        "resposta_aluno": respostas_aluno.get(q['id']),
                        "acertou": (respostas_aluno.get(q['id']) == q['resposta_correta']),
                        "acertos": acertos
                    })
                
                try:
                    db_provas.table("resultados_provas").insert(lista_resultados).execute()
                    st.session_state.etapa = "resultado_final"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

# ==========================================
# ETAPA 5: RESULTADO E MISTÉRIO DO PROFESSOR
# ==========================================
elif st.session_state.etapa == "resultado_final":
    aluno = st.session_state.aluno

    st.balloons() 
    st.markdown(f"""
        <div style="text-align: center; margin-top: 3rem;">
            <h1 style="color: {C_PRIMARY}; font-size: 40px; font-weight: bold;">🎉 Avaliação Concluída!</h1>
            <p style="color: {C_TEXT_MUTED}; font-size: 18px; margin-top: 10px;">Parabéns, {aluno['nome']}. Suas respostas foram enviadas e salvas com sucesso!</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    # --- A NOVA CAIXA DE MISTÉRIO ---
    with st.container(border=True):
        st.markdown(f"""
            <div style="text-align: center; padding: 20px;">
                <h2 style="color: {C_SECONDARY}; margin-bottom: 15px; font-size: 26px;">🤫 A nota só é liberada depois, viu Bença!</h2>
                <p style="color: {C_TEXT}; font-size: 18px; line-height: 1.6;">
                    Para manter o suspense e evitar <em>spoilers</em> para os colegas que ainda farão a prova, 
                    <strong>sua nota, o gabarito e o feedback personalizado do Mestre Lardião</strong> 
                    só serão liberados após o encerramento do prazo desta atividade.
                </p>
                <p style="color: {C_TEXT_MUTED}; font-size: 16px; margin-top: 15px;">
                    Fique de olho! O portal avisará quando os resultados forem abertos.
                </p>
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    
    if st.button("⬅️ Voltar para o Portal Pro", type="secondary", use_container_width=True):
        st.session_state.clear() 
        st.rerun()

# ==========================================
# ETAPA 6: VER MEU RESULTADO E FEEDBACK DA IA
# ==========================================
elif st.session_state.etapa == "ver_meu_resultado":
    aluno = st.session_state.aluno
    prova = st.session_state.prova_resultado

    # 1. VERIFICAÇÃO DE CADEADO: As notas foram liberadas pelo professor?
    try:
        res_status = db_provas.table("modelos_prova").select("notas_liberadas").eq("id", prova['id']).single().execute()
        notas_liberadas = res_status.data.get('notas_liberadas', False) if res_status.data else False
    except:
        notas_liberadas = False

    if not notas_liberadas:
        # --- TELA DE ESPERA (Cadeado Fechado) ---
        st.subheader(f"✅ Prova Enviada: {prova['titulo']}")
        st.balloons()
        
        st.markdown(f"""
            <div style="background-color: #f0f7ff; border-left: 5px solid #007bff; border-radius: 10px; padding: 25px; margin-top: 20px;">
                <h3 style="color: #0056b3; margin-top: 0;">🧙‍♂️ O Mestre Lardião está analisando...</h3>
                <p style="font-size: 18px; color: #333;">Suas respostas foram salvas com sucesso no pergaminho sagrado!</p>
                <p style="font-size: 16px; color: #666;"><b>O que acontece agora?</b> O professor está revisando os feedbacks da IA. 
                Assim que as notas forem liberadas, você poderá ver seu desempenho detalhado e o diagnóstico pedagógico aqui.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("⬅️ Voltar para Atividades", use_container_width=True):
            st.session_state.etapa = "ante_sala"
            st.rerun()

    else:
        # --- TELA DE RESULTADO (Cadeado Aberto) ---
        st.subheader(f"📊 Desempenho: {prova['titulo']}")
        
        with st.spinner("Carregando sua correção comentada..."):
            try:
                # 1. Busca dados de desempenho e feedback
                res_detalhes = db_provas.table("resultados_provas").select("*").eq("aluno_id", str(aluno['id'])).eq("prova_id", prova['id']).execute()
                
                acertos = sum(1 for r in res_detalhes.data if r.get('acertou') == True)
                valor_cada = prova.get('valor_questao', 1.0)
                nota_final = acertos * valor_cada
                
                res_fb = db_provas.table("feedback_ia_alunos").select("diagnostico_pedagogico").eq("aluno_id", str(aluno['id'])).eq("prova_id", prova['id']).execute()
                feedback = res_fb.data[0]['diagnostico_pedagogico'] if res_fb.data else None

                # 2. Barra de Resumo (Métricas + Mestre)
                col_nota, col_acerto, col_fb = st.columns([1, 1, 3])
                
                with col_nota:
                    st.metric("Sua Nota", f"{nota_final:.1f}")
                with col_acerto:
                    st.metric("Acertos", f"{acertos}")
                with col_fb:
                    if feedback:
                        st.info(f"**🧙‍♂️ Mestre Lardião diz:** {feedback}")
                    else:
                        st.caption("Feedback pedagógico sendo processado.")

                st.divider()

                # 3. Revisão de Questões
                erradas = [r for r in res_detalhes.data if r.get('acertou') == False]
                
                if not erradas:
                    st.success("✨ **Excepcional! Você gabaritou esta avaliação.**")
                else:
                    st.markdown("#### 🔍 Revisão de Pontos Críticos:")
                    
                    q_ids = [r['questao_id'] for r in erradas]
                    res_questoes = db_provas.table("questoes").select("*").in_("id", q_ids).execute()
                    questoes_dict = {q['id']: q for q in res_questoes.data}

                    for erro in erradas:
                        q = questoes_dict.get(erro['questao_id'])
                        if q:
                            # Prepara resumo do título (limpo de HTML)
                            texto_puro = q.get('enunciado', 'Questão sem texto')
                            resumo = (texto_puro[:65] + '...') if len(texto_puro) > 65 else texto_puro
                            
                            with st.expander(f"❌ Erro em: {resumo}", expanded=False):
                                # Mostra enunciado completo (Suporta fórmulas/imagens)
                                st.write(q.get('enunciado', ''), unsafe_allow_html=True)
                                
                                alts = q.get('alternativas') or {}
                                letra_aluno = erro.get('resposta_a') or erro.get('resposta_aluno') or "?"
                                letra_correta = q.get('resposta_correta', '')

                                # Comparação de respostas
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown(f"<span style='color:#d9534f'>❌ **Você marcou:** ({letra_aluno})</span>", unsafe_allow_html=True)
                                with c2:
                                    st.markdown(f"<span style='color:#5cb85c'>✅ **O correto era:** ({letra_correta})</span>", unsafe_allow_html=True)

                                # Tarja de Justificativa com Limpeza de Texto
                                just = q.get('justificativas')
                                if just:
                                    if isinstance(just, dict):
                                        txt_erro = str(just.get(letra_aluno, "")).replace("Diagnóstico: ", "")
                                        txt_certa = str(just.get(letra_correta, "")).replace("Diagnóstico: ", "")
                                        
                                        if txt_erro:
                                            msg = f"<b>Por que a ({letra_aluno}) está incorreta:</b> {txt_erro}<br><br><b>Sobre a correta ({letra_correta}):</b> {txt_certa}"
                                        else:
                                            msg = f"<b>Explicação da correta ({letra_correta}):</b> {txt_certa}"
                                    else:
                                        msg = str(just).replace("Diagnóstico: ", "")
                                    
                                    st.markdown(f"<div style='background-color: #e7f3fe; border-left: 5px solid #2196F3; padding: 15px; border-radius: 5px; color: #0c5460;'>💡 {msg}</div>", unsafe_allow_html=True)

            except Exception as e:
                st.error("Ocorreu um erro ao processar sua correção.")
                st.code(str(e))

        if st.button("⬅️ Voltar para Atividades", use_container_width=True):
            st.session_state.etapa = "ante_sala"
            st.rerun()