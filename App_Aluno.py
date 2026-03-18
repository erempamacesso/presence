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
# 1. CONFIGURAÇÕES, IDENTIDADE E ESTILO (TEMA CLARO)
# ==========================================
st.set_page_config(
    page_title="Portal Lardião | Química Pro", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="logo_erempam.png" 
)

# Paleta Light Premium
C_BG_DEEP = "#F0F4F8"      # Cinza Claro Suave (Fundo Total)
C_CARD_BG = "#FFFFFF"     # Branco Puro (Cards)
C_PRIMARY = "#00C896"     # Teal Vibrante (Destaques)
C_SECONDARY = "#FF8000"   # Laranja Vibrante
C_TEXT = "#2D3748"        # Cinza Escuro Quase Preto (Texto Principal)
C_TEXT_MUTED = "#718096"  # Cinza Médio (Subtítulos)
C_BORDER = "#E2E8F0"      # Cinza Claro (Bordas)

# Função para converter imagem
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

# Injeção de CSS Light Premium
st.markdown(f"""
    <style>
        .stApp {{ background-color: {C_BG_DEEP}; color: {C_TEXT}; }}
        [data-testid="stSidebar"], #MainMenu, footer {{display: none;}}
        .main .block-container {{padding-top: 1.5rem;}}

        /* Card de Login */
        .login-card {{
            text-align: center; 
            max-width: 500px; 
            margin: 4rem auto; 
            padding: 45px 35px; 
            border: 1px solid {C_BORDER}; 
            border-radius: 20px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.05);
            background-color: {C_CARD_BG};
        }}

        /* Inputs de Texto */
        .stTextInput>div>div>input {{
            background-color: #F7FAFC !important;
            color: {C_TEXT} !important;
            border-radius: 12px !important;
            border-color: {C_BORDER} !important;
            padding: 14px !important;
            font-size: 16px !important;
        }}
        .stTextInput>div>div>input:focus {{
            border-color: {C_PRIMARY} !important;
            box-shadow: 0 0 0 0.2rem rgba(0,200,150,0.2) !important;
            background-color: #FFFFFF !important;
        }}
        .stTextInput>label {{ color: {C_TEXT} !important; font-weight: bold; font-size: 14px; }}

        /* Botões Primários */
        .stButton>button[kind="primary"] {{
            background-color: {C_PRIMARY}; color: #FFFFFF; border: none;
            border-radius: 12px; height: 3.8em; font-weight: bold; font-size: 17px; width: 100%;
        }}
        .stButton>button[kind="primary"]:hover {{
            background-color: {C_SECONDARY}; color: white; transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255,128,0,0.3);
        }}

        /* Elementos Nativos (Containers) */
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {C_CARD_BG};
            border-radius: 15px;
            border-color: {C_BORDER};
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
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
# ETAPA 1: LOGIN (LOGOS AJUSTÁVEIS E TEMA CLARO)
# ==========================================
if st.session_state.etapa == "login":
    st.markdown(f"""
        <div class="login-card">
            <div style="display: flex; justify-content: space-around; align-items: center; margin-bottom: 40px; padding: 0 10px;">
                <img src="data:image/png;base64,{logo_erempam_b64}" width="160" alt="EREMPAM Logo"/>
                
                <img src="data:image/png;base64,{logo_lardiao_b64}" width="140" alt="Lardião Logo"/>
            </div>
            <h1 style="color: {C_PRIMARY}; font-size: 30px; margin-bottom: 10px; font-weight: bold;">Portal de Avaliações</h1>
            <h2 style="color: {C_SECONDARY}; font-weight: normal; font-size: 21px; margin-bottom: 40px;">do Prof. Lardião</h2>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.9, 1])
    with col2:
        matricula = st.text_input("Sua Matrícula SIGEREMPAM:", placeholder="Digite apenas números...")
        st.markdown("<br>", unsafe_allow_html=True)
        btn_acesso = st.button("ACESSAR SISTEMA", type="primary")
        
        if btn_acesso and matricula:
            with st.spinner("Autenticando..."):
                try:
                    res = db_alunos.table("alunos").select("*").eq("numero_matricula", matricula).execute()
                    if res.data:
                        st.session_state.aluno = res.data[0]
                        st.session_state.etapa = "ante_sala"
                        st.rerun()
                    else:
                        st.error("Matrícula SIGEREMPAM não encontrada.")
                except Exception as e:
                    st.error(f"Erro Crítico de conexão: {e}")

# ==========================================
# ETAPA 2: ANTE-SALA (TABELA NATIVA BLINDADA - RESOLVE O CÓDIGO ESTRANHO)
# ==========================================
elif st.session_state.etapa == "ante_sala":
    aluno = st.session_state.aluno
    turma_bruta = str(aluno.get('turma', ''))
    serie_aluno = "1º Ano"
    if "2" in turma_bruta: serie_aluno = "2º Ano"
    elif "3" in turma_bruta: serie_aluno = "3º Ano"

    st.markdown(f"""
        <div style="margin-bottom: 30px;">
            <h1 style="color: {C_TEXT}; margin-bottom: 8px;">👋 Olá, <span style="color: {C_SECONDARY};">{aluno['nome']}</span>!</h1>
            <p style="color: {C_TEXT_MUTED}; font-size: 16px;">Sua série é o <strong>{serie_aluno}</strong>. Confira suas atividades pendentes.</p>
        </div>
    """, unsafe_allow_html=True)

    with st.spinner("Buscando avaliações..."):
        try:
            res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).execute()
            provas_ativas = res_p.data
            
            ids_ativas = [p['id'] for p in provas_ativas]
            ja_fez_dict = {}
            if ids_ativas:
                res_JF = db_provas.table("resultados_provas").select("prova_id").eq("aluno_id", str(aluno['id'])).in_("prova_id", ids_ativas).execute()
                ja_fez_dict = {x['prova_id']: True for x in res_JF.data}

            if provas_ativas:
                # --- CABEÇALHO DA LISTA DE PROVAS ---
                st.markdown(f"### 📋 Lista de Atividades")
                ha_pendentes = False
                
                # --- RENDERIZAÇÃO NATIVA (SEM HTML PARA NÃO QUEBRAR) ---
                for p in provas_ativas:
                    q_sorteio = p.get('qtd_sorteio', p.get('qtd_questoes', 1))
                    valor_total = q_sorteio * p.get('valor_questao', 1.0)
                    dt_limite = datetime.fromisoformat(p['data_limite']).strftime("%d/%m/%Y às %H:%M")
                    foi_feita = ja_fez_dict.get(p['id'], False)
                    
                    if not foi_feita: ha_pendentes = True
                    status_texto = "✅ Concluída" if foi_feita else "🔵 Pendente"
                    status_cor = "green" if foi_feita else "orange"

                    # Cria um "Card" nativo para cada prova
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 1, 1.5])
                        with col1:
                            st.markdown(f"**<span style='color:{C_PRIMARY}; font-size:18px;'>{p['titulo']}</span>**", unsafe_allow_html=True)
                            st.caption(f"Assunto: {p.get('assunto','Química Pro')}")
                        with col2:
                            st.markdown("**Pontos:**")
                            st.write(f"{valor_total:.1f}")
                        with col3:
                            st.markdown("**Status / Limite:**")
                            st.markdown(f":{status_cor}[**{status_texto}**]")
                            st.caption(dt_limite)
                
                # --- BOTÕES PARA INICIAR (ABAIXO DA LISTA) ---
                if ha_pendentes:
                    st.divider()
                    st.markdown("### ✍️ Iniciar Atividade Avaliativa")
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
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    st.header(f"👋 Preparado, {aluno['nome']}?")
    
    with st.container(border=True):
        st.subheader(f"📝 {prova['titulo']}")
        st.write(f"Série: {prova['serie']} | Tempo de Execução: **{prova['tempo_duracao']} minutos**")
        st.markdown(f"""
            **Instruções Importantes:**
            1. Você terá {prova['tempo_duracao']} minutos cronometrados.
            2. Não atualize ou feche o navegador.
            3. Responda todas e clique em 'Enviar' ao final.
        """)
        
        if st.button("INICIAR PROVA AGORA", type="primary", use_container_width=True):
            with st.spinner("Gerando sua avaliação..."):
                st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
                ids = prova.get('questoes_ids', [])
                res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
                pool_questoes = res_q.data
                
                random.seed(str(aluno['id']))
                random.shuffle(pool_questoes)
                n_sorteio = prova.get('qtd_sorteio', len(pool_questoes))
                st.session_state.questoes = pool_questoes[:n_sorteio]
                st.session_state.etapa = "em_prova"
                st.rerun()

# ==========================================
# ETAPA 4: EXECUÇÃO DA PROVA 
# ==========================================
elif st.session_state.etapa == "em_prova":
    if not st.session_state.questoes or not st.session_state.tempo_final:
        st.session_state.etapa = "login"
        st.rerun()

    restante = st.session_state.tempo_final - datetime.now()
    segs = int(restante.total_seconds())
    
    if segs <= 0:
        st.error("⌛ TEMPO ESGOTADO!")
        if st.button("Voltar ao Portal", type="secondary"):
            st.session_state.clear()
            st.rerun()
        st.stop()

    st.markdown(f"## ✍️ {st.session_state.prova_config['titulo']}")
    st.caption(f"Aluno: {st.session_state.aluno['nome']}")
    
    with st.form("form_prova", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questoes):
            with st.container(border=True):
                st.markdown(f"**<span style='color: {C_PRIMARY};'>QUESTÃO {i+1}</span>**", unsafe_allow_html=True)
                st.markdown(q['enunciado'], unsafe_allow_html=True)
                
                opcoes_dict = q.get('alternativas', {}) 
                letras_originais = [l for l in ["A", "B", "C", "D", "E"] if opcoes_dict.get(l)]
                
                random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
                ordem = letras_originais.copy()
                random.shuffle(ordem)

                def limpar_alternativa(texto_cru):
                    t_sem_html = re.sub(r'<[^>]+>', '', str(texto_cru))
                    return re.sub(r'^\s*[A-Ea-e]\s*[\)\.\-]\s*', '', t_sem_html).strip()

                escolha = st.radio(
                    f"Radio_Q{i+1}", 
                    options=ordem, 
                    format_func=lambda x: f"{x}) {limpar_alternativa(opcoes_dict.get(x, ''))}",
                    index=None, 
                    key=f"q_{q['id']}"
                )
                if escolha: st.session_state.respostas[q['id']] = escolha 
                
        st.markdown("<br>", unsafe_allow_html=True)
        entregar = st.form_submit_button("✅ FINALIZAR AVALIAÇÃO", type="primary")

    if entregar:
        if len(st.session_state.respostas) < len(st.session_state.questoes):
            st.warning("⚠️ Você precisa responder todas as questões.")
        else:
            with st.spinner("Processando..."):
                acertos = sum(1 for q in st.session_state.questoes if st.session_state.respostas.get(q['id']) == q['resposta_correta'])
                
                lista_resultados = [{
                    "aluno_id": str(st.session_state.aluno['id']), 
                    "prova_id": st.session_state.prova_config['id'],
                    "questao_id": q['id'],
                    "resposta_aluno": st.session_state.respostas.get(q['id']),
                    "acertou": (st.session_state.respostas.get(q['id']) == q['resposta_correta']),
                    "acertos": acertos 
                } for q in st.session_state.questoes]
                
                try:
                    db_provas.table("resultados_provas").insert(lista_resultados).execute()
                    st.session_state.etapa = "resultado_final"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

# ==========================================
# ETAPA 5: RESULTADO
# ==========================================
elif st.session_state.etapa == "resultado_final":
    aluno = st.session_state.aluno
    res_JF = db_provas.table("resultados_provas").select("acertos").eq("aluno_id", str(aluno['id'])).eq("prova_id", st.session_state.prova_config['id']).limit(1).execute()
    total_acertos = res_JF.data[0]['acertos'] if res_JF.data else 0
    total_questoes = len(st.session_state.questoes)

    st.balloons() 
    st.markdown(f"""
        <div style="text-align: center; margin-top: 2rem;">
            <h1 style="color: {C_PRIMARY};">🎉 Avaliação Concluída!</h1>
            <p style="color: {C_TEXT_MUTED}; font-size: 18px;">Parabéns, {aluno['nome']}.</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown(f"<h2 style='text-align: center;'>Sua Nota</h2>", unsafe_allow_html=True)
        nota = total_acertos * st.session_state.prova_config.get('valor_questao', 1.0)
        st.markdown(f"<div style='font-size: 60px; font-weight: bold; color: {C_SECONDARY}; text-align: center;'>{nota:.1f}</div>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center;'>Acertos: <strong>{total_acertos}</strong> / {total_questoes}</p>", unsafe_allow_html=True)

    st.divider()
    if st.button("⬅️ Voltar", type="secondary", use_container_width=True):
        st.session_state.clear()
        st.rerun()