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
        .stApp {{ background-color: {C_BG_DEEP}; color: {C_TEXT}; }}
        [data-testid="stSidebar"] {{display: none;}}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        .main .block-container {{padding-top: 1.5rem;}}

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
            matricula = st.text_input("Digite sua matrícula:", label_visibility="collapsed", placeholder="Digite Sua Matrícula")
            st.write("") 
            
            if st.button("ACESSAR SISTEMA PRO", use_container_width=True, type="primary"):
                if matricula:
                    with st.spinner("Buscando dados no servidor..."):
                        try:
                            mat_limpa = str(matricula).strip()
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
# ETAPA 2: ANTE-SALA
# ==========================================
elif st.session_state.etapa == "ante_sala":
    if 'aluno' not in st.session_state or not st.session_state.aluno:
        st.warning("⚠️ Sessão de aluno não encontrada. Voltando ao login em 2 segundos...")
        import time
        time.sleep(2)
        st.session_state.etapa = "login"
        st.rerun()

    aluno = st.session_state.aluno
    turma_bruta = str(aluno.get('turma', ''))
    serie_aluno = "1º Ano"
    if "2" in turma_bruta: serie_aluno = "2º Ano"
    elif "3" in turma_bruta: serie_aluno = "3º Ano"

    st.markdown(f"""
        <div style="margin-bottom: 25px; padding: 15px; background-color: #F8FAFC; border-left: 5px solid #00C896; border-radius: 5px;">
            <h2 style="margin: 0; color: #1E293B;">👋 Olá, <span style="color: #00C896;">{aluno.get('nome', 'Aluno')}</span>!</h2>
            <p style="color: #64748b; font-size: 16px; margin: 5px 0 0 0;">Sua série: <strong>{serie_aluno}</strong> ({turma_bruta})</p>
        </div>
    """, unsafe_allow_html=True)

    with st.spinner("Buscando suas atividades..."):
        try:
            res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).execute()
            provas_ativas = res_p.data
            
            ja_fez_dict = {}
            if provas_ativas:
                ids_ativas = [p['id'] for p in provas_ativas]
                res_JF = db_provas.table("resultados_provas").select("prova_id").eq("aluno_id", str(aluno.get('id', ''))).in_("prova_id", ids_ativas).execute()
                ja_fez_dict = {x['prova_id']: True for x in res_JF.data}

            if provas_ativas:
                st.subheader("📋 Suas Atividades Disponíveis")
                ha_pendentes = False
                
                for p in provas_ativas:
                    q_sorteio = p.get('qtd_sorteio', p.get('qtd_questoes', 1))
                    valor_total = q_sorteio * p.get('valor_questao', 1.0)
                    
                    dt_limite = p.get('data_limite', '')
                    if dt_limite:
                        dt_limite = dt_limite[:16].replace("T", " às ")
                    else:
                        dt_limite = "Sem limite"
                    
                    foi_feita = ja_fez_dict.get(p['id'], False)
                    status_texto = "✅ Concluída" if foi_feita else "🔵 Pendente"
                    status_cor = "green" if foi_feita else "orange"
                    if not foi_feita: ha_pendentes = True

                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1, 1.5])
                        with c1:
                            st.markdown(f"**{p.get('titulo', 'Atividade')}**")
                            st.caption(f"Assunto: {p.get('assunto','Geral')}")
                        with c2:
                            st.markdown(f"**Nota Máx.**\n\n{valor_total:.1f}")
                        with c3:
                            st.markdown(f"**Status**\n\n:{status_cor}[{status_texto}]")
                            st.caption(f"Até: {dt_limite}")

                if ha_pendentes:
                    st.divider()
                    st.markdown("### ✍️ Iniciar Agora")
                    
                    pendentes = [p for p in provas_ativas if not ja_fez_dict.get(p['id'], False)]
                    cols_btn = st.columns(len(pendentes) if pendentes else 1)
                    
                    for idx, p in enumerate(pendentes):
                        with cols_btn[idx]:
                            if st.button(f"🚀 Iniciar {p['titulo']}", key=f"btn_{p['id']}", type="primary", use_container_width=True):
                                st.session_state.prova_config = p
                                st.session_state.etapa = "instrucoes"
                                st.rerun()
            else:
                st.info(f"🎉 Nenhuma atividade ativa encontrada para o {serie_aluno} no momento.")
                
        except Exception as e:
            st.error("Erro interno ao carregar a lista de atividades.")
            st.code(f"Detalhes do Erro: {str(e)}")

# ==========================================
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
# ETAPA 4: EXECUÇÃO DA PROVA (COM FUNDO BRANCO VIP)
# ==========================================
elif st.session_state.etapa == "em_prova":
    # MÁGICA AQUI: Força o fundo branco especificamente para o Simulado
    st.markdown("""
        <style>
            .stApp {
                background-color: #FFFFFF !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    import streamlit.components.v1 as components
    
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

    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
            <h2 style="color: {C_TEXT}; font-size: 24px;">✍️ {st.session_state.prova_config['titulo']}</h2>
            <p style="color: {C_TEXT_MUTED}; font-size: 14px;">Aluno: {st.session_state.aluno['nome']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_prova", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questoes):
            with st.container(border=True):
                st.markdown(f"**<span style='color: {C_PRIMARY}; font-size: 18px; display: block; margin-bottom: 15px;'>QUESTÃO {i+1}</span>**", unsafe_allow_html=True)
                st.markdown(q['enunciado'], unsafe_allow_html=True)
                
                opcoes_dict = q.get('alternativas', {}) 
                letras_originais = [l for l in ["A", "B", "C", "D", "E"] if opcoes_dict.get(l)]
                
                random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
                ordem = letras_originais.copy()
                random.shuffle(ordem)

                def limpar_alternativa(texto_cru):
                    t_sem_html = re.sub(r'<[^>]+>', '', str(texto_cru)) 
                    t_limpo = re.sub(r'^\s*[A-Ea-e]\s*[\)\.\-]\s*', '', t_sem_html).strip() 
                    return t_limpo

                st.markdown(f"<strong style='font-size:15px; color:{C_TEXT}'>Selecione a alternativa correta:</strong>", unsafe_allow_html=True)
                escolha = st.radio(
                    f"Radio_Q{i+1}", 
                    options=ordem, 
                    # Agora ele pega APENAS o texto limpo da alternativa 👇
                    format_func=lambda x: f"{limpar_alternativa(opcoes_dict.get(x, ''))}",
                    index=None, 
                    key=f"q_{q['id']}", 
                    label_visibility="collapsed" 
                )
                
                if escolha:
                    st.session_state.respostas[q['id']] = escolha 
                st.markdown("<br>", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR AVALIAÇÃO PRO", type="primary", use_container_width=True)

    if entregar:
        if len(st.session_state.respostas) < len(st.session_state.questoes):
            st.warning("⚠️ Atenção! Você precisa responder todas as questões Pro antes de enviar.")
        else:
            with st.spinner("Processando suas respostas e calculando nota Pro..."):
                valor_cada = st.session_state.prova_config.get('valor_questao', 1.0)
                acertos = 0
                for q in st.session_state.questoes:
                    if st.session_state.respostas.get(q['id']) == q['resposta_correta']:
                        acertos += 1
                
                lista_resultados = []
                for q in st.session_state.questoes:
                    resp_aluno = st.session_state.respostas.get(q['id'])
                    lista_resultados.append({
                        "aluno_id": str(st.session_state.aluno['id']), 
                        "prova_id": st.session_state.prova_config['id'],
                        "questao_id": q['id'],
                        "resposta_aluno": resp_aluno,
                        "acertou": (resp_aluno == q['resposta_correta']),
                        "acertos": acertos 
                    })
                
                try:
                    db_provas.table("resultados_provas").insert(lista_resultados).execute()
                    st.session_state.etapa = "resultado_final"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro Crítico ao salvar resultado no banco de dados Pro: {e}")

# ==========================================
# ETAPA 5: RESULTADO E MISTÉRIO DO PROFESSOR
# ==========================================
elif st.session_state.etapa == "resultado_final":
    aluno = st.session_state.aluno
    res_JF = db_provas.table("resultados_provas").select("acertos").eq("aluno_id", str(aluno['id'])).eq("prova_id", st.session_state.prova_config['id']).limit(1).execute()
    total_acertos = res_JF.data[0]['acertos'] if res_JF.data else 0
    total_questoes = len(st.session_state.questoes)

    st.balloons() 
    st.markdown(f"""
        <div style="text-align: center; margin-top: 3rem;">
            <h1 style="color: {C_PRIMARY}; font-size: 40px; font-weight: bold;">🎉 Avaliação Concluída!</h1>
            <p style="color: {C_TEXT_MUTED}; font-size: 18px; margin-top: 10px;">Parabéns, {aluno['nome']}. Suas respostas foram enviadas e processadas Pro.</p>
        </div>
    """, unsafe_allow_html=True)
    
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
        st.session_state.clear() 
        st.rerun()