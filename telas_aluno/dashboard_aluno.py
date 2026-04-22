import streamlit as st
import time
from telas_aluno.desempenho import mostrar_tela_desempenho

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # ==========================================
    # CSS: MINIMALISTA & FORMAL (SEM EMOJIS)
    # ==========================================
    st.markdown(f"""
        <style>
        /* Fundo Profissional */
        [data-testid="stAppViewContainer"] {{
            background: radial-gradient(circle at top right, #1c2541, #0b132b);
            color: #ffffff;
            font-family: 'Inter', sans-serif;
        }}
        
        [data-testid="stHeader"] {{
            visibility: hidden;
        }}

        /* Welcome Header Minimalista */
        .welcome-container {{
            padding: 40px 0 20px 0;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 30px;
        }}
        
        .welcome-title {{
            font-size: 24px;
            font-weight: 300;
            letter-spacing: 1px;
            color: #ffffff;
            margin: 0;
            text-transform: uppercase;
        }}
        
        .welcome-subtitle {{
            font-size: 13px;
            color: #94a3b8;
            margin-top: 5px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        /* Botões Elegantes e Formais */
        div[data-testid="stButton"] > button {{
            background-color: transparent !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 4px !important; /* Bordas mais retas = mais formal */
            padding: 15px 25px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 2px !important;
            transition: all 0.4s ease !important;
            width: 100%;
            margin-bottom: 10px;
        }}

        div[data-testid="stButton"] > button:hover {{
            background-color: #ffffff !important;
            color: #0b132b !important;
            border: 1px solid #ffffff !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2) !important;
        }}

        /* Ajuste para o botão de Sair (Menor e mais discreto) */
        .logout-btn div[data-testid="stButton"] > button {{
            border: 1px solid rgba(255, 50, 50, 0.3) !important;
            color: rgba(255, 100, 100, 0.8) !important;
            font-size: 11px !important;
            margin-top: 40px;
        }}

        .logout-btn div[data-testid="stButton"] > button:hover {{
            background-color: rgba(255, 50, 50, 0.1) !important;
            color: #ff4b4b !important;
        }}
        
        /* Containers de Conteúdo */
        .section-title {{
            font-size: 12px;
            text-transform: uppercase;
            color: #94a3b8;
            letter-spacing: 3px;
            margin-bottom: 20px;
            font-weight: 600;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- HEADER ---
    st.markdown(f"""
        <div class="welcome-container">
            <h1 class="welcome-title">{aluno["nome"]}</h1>
            <p class="welcome-subtitle">{aluno.get("turma", "Estudante")} | EREMPAM</p>
        </div>
    """, unsafe_allow_html=True)

    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    # ---------------------------------------------------------
    # TELA: MENU PRINCIPAL
    # ---------------------------------------------------------
    if st.session_state.menu_active == "home":
        st.markdown('<p class="section-title">Navegação Principal</p>', unsafe_allow_html=True)
        
        if st.button("Simulados Disponíveis", use_container_width=True):
            st.session_state.menu_active = "provas"
            st.rerun()
            
        if st.button("Atividades Concluídas", use_container_width=True):
            st.session_state.menu_active = "historico"
            st.rerun()
            
        if st.button("Desempenho Acadêmico", use_container_width=True):
            st.session_state.menu_active = "notas"
            st.rerun()

        # Botão de Sair com estilo específico
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Encerrar Sessão", use_container_width=True):
            st.session_state.aluno = None
            st.session_state.etapa = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # TELA: PROVAS
    # ---------------------------------------------------------
    elif st.session_state.menu_active == "provas":
        if st.button("Voltar ao Início", use_container_width=True): 
            st.session_state.menu_active = "home"
            st.rerun()
            
        st.markdown('<p class="section-title">Simulados Disponíveis</p>', unsafe_allow_html=True)
        
        turma_aluno = str(aluno.get('turma', ''))
        serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"

        try:
            res = db_provas.table("modelos_prova").select("*").eq("serie", serie_aluno).eq("ativa", True).execute()
            if res.data:
                for prova in res.data:
                    with st.container():
                        st.markdown(f"""
                            <div style="border-left: 2px solid #00b4d8; padding-left: 20px; margin-bottom: 20px;">
                                <div style="font-size: 16px; font-weight: 500;">{prova.get('titulo')}</div>
                                <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase;">
                                    Duração: {prova.get('tempo_duracao', 60)} min
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("Acessar Simulado", key=f"p_{prova['id']}", use_container_width=True):
                            st.session_state.prova_config = prova
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
            else:
                st.info("Nenhuma atividade disponível para sua série no momento.")
        except Exception as e:
            st.error(f"Erro na conexão com o servidor.")

    # ---------------------------------------------------------
    # TELA: NOTAS
    # ---------------------------------------------------------
    elif st.session_state.menu_active == "notas":
        if st.button("Voltar ao Início", use_container_width=True): 
            st.session_state.menu_active = "home"
            st.rerun()
        mostrar_tela_desempenho(db_alunos, db_provas)