import streamlit as st
from telas_aluno.desempenho import mostrar_tela_desempenho

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # ==========================================
    # CSS: OTIMIZADO PARA MOBILE (2 COLUNAS)
    # ==========================================
    st.markdown(f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background: radial-gradient(circle at top right, #1c2541, #0b132b);
            color: #ffffff;
            font-family: 'Inter', sans-serif;
        }}
        
        [data-testid="stHeader"] {{
            visibility: hidden;
        }}

        /* Header Ajustado (Fiel ao rascunho) */
        .welcome-container {{
            padding: 10px 0 20px 0;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 25px;
        }}
        
        .welcome-title {{
            font-size: 13px; /* Fonte menor para caber o nome todo */
            font-weight: 700;
            color: #facc15; /* Amarelo ouro pedido no rascunho */
            margin: 0;
            text-transform: uppercase;
            line-height: 1.4;
        }}
        
        .welcome-subtitle {{
            font-size: 11px;
            color: #ffffff; 
            opacity: 0.8;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        /* Botões em Grade 2x3 (Bordas Arredondadas) */
        div[data-testid="stButton"] > button {{
            background-color: transparent !important;
            color: #ffffff !important;
            border: 2px solid #ffffff !important;
            border-radius: 12px !important; /* Borda arredondada como no desenho */
            padding: 15px 5px !important; 
            font-size: 11px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            transition: all 0.3s ease !important;
            width: 100%;
            height: 80px; /* Altura fixa dos botões */
        }}

        div[data-testid="stButton"] > button:hover {{
            background-color: rgba(255, 255, 255, 0.1) !important;
        }}

        /* Botão Vazio (Placeholder) */
        .botao-vazio div[data-testid="stButton"] > button {{
            border: 2px solid rgba(255, 255, 255, 0.3) !important; /* Borda mais apagada */
            color: transparent !important;
        }}

        /* Botão Encerrar Sessão (Apenas Texto) */
        .logout-btn div[data-testid="stButton"] > button {{
            border: none !important;
            background: transparent !important;
            color: #ffffff !important;
            font-size: 13px !important;
            margin-top: 30px;
            height: auto;
            letter-spacing: 2px !important;
        }}

        .logout-btn div[data-testid="stButton"] > button:hover {{
            color: #ff4b4b !important;
        }}

        /* Label da Seção */
        .grid-label {{
            font-size: 11px;
            text-transform: uppercase;
            color: #5d6d81;
            letter-spacing: 2px;
            margin-bottom: 15px;
        }}

        /* TRUQUE MÁGICO PARA O CELULAR: Força 2 colunas reais lado a lado */
        @media (max-width: 600px) {{
            div[data-testid="stHorizontalBlock"] {{
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                gap: 10px !important;
            }}
            div[data-testid="column"] {{
                width: 50% !important;
                flex: 1 1 calc(50% - 5px) !important;
                min-width: calc(50% - 5px) !important;
            }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- HEADER CONFORME RASCUNHO ---
    matricula_aluno = aluno.get("numero_matricula", "0000000")
    st.markdown(f"""
        <div class="welcome-container">
            <p class="welcome-title">[{matricula_aluno}] - {aluno["nome"]}</p>
            <p class="welcome-subtitle">{aluno.get("turma", "Estudante")} // EREMPAM</p>
        </div>
    """, unsafe_allow_html=True)

    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    # ---------------------------------------------------------
    # MENU PRINCIPAL (GRADE 2 COLUNAS)
    # ---------------------------------------------------------
    if st.session_state.menu_active == "home":
        st.markdown('<p class="grid-label">Terminal de Acesso</p>', unsafe_allow_html=True)
        
        # LINHA 1
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Simulados\nAbertos", use_container_width=True):
                st.session_state.menu_active = "provas"
                st.rerun()
        with col2:
            if st.button("Atividades\nConcluídas", use_container_width=True):
                st.session_state.menu_active = "historico"
                st.rerun()
                
        # LINHA 2
        col3, col4 = st.columns(2)
        with col3:
            if st.button("Painel de\nDesempenho", use_container_width=True):
                st.session_state.menu_active = "notas"
                st.rerun()
        with col4:
            st.button("Avisos\nEscolares", disabled=True, use_container_width=True)

        # LINHA 3
        col5, col6 = st.columns(2)
        with col5:
            st.button("Suporte\nTécnico", disabled=True, use_container_width=True)
        with col6:
            # Botão "vazio" desenhado no rascunho
            st.markdown('<div class="botao-vazio">', unsafe_allow_html=True)
            st.button("Vazio", disabled=True, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # BOTÃO SAIR (ISOLADO EMBAIXO)
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("ENCERRAR SESSÃO", use_container_width=True):
            st.session_state.aluno = None
            st.session_state.etapa = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # TELAS SECUNDÁRIAS (PROVAS / NOTAS)
    # ---------------------------------------------------------
    elif st.session_state.menu_active == "provas":
        if st.button("← VOLTAR", use_container_width=True): 
            st.session_state.menu_active = "home"
            st.rerun()
        st.markdown('<p class="grid-label">Simulados Disponíveis</p>', unsafe_allow_html=True)
        
        # Lógica de busca de provas (mantida do seu código original)
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
            st.error("Erro na conexão com o servidor.")

    elif st.session_state.menu_active == "notas":
        if st.button("← VOLTAR", use_container_width=True): 
            st.session_state.menu_active = "home"
            st.rerun()
        mostrar_tela_desempenho(db_alunos, db_provas)
        
    elif st.session_state.menu_active == "historico":
        if st.button("← VOLTAR", use_container_width=True): 
            st.session_state.menu_active = "home"
            st.rerun()
        st.markdown('<p class="grid-label">Atividades Realizadas</p>', unsafe_allow_html=True)
        st.info("Aqui entrará a lista das provas já concluídas pelo aluno.")