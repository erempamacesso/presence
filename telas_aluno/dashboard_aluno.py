import streamlit as st

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # ==========================================
    # CSS: LIGHT MODE (#E0E0E0) E GRID CENTRALIZADO
    # ==========================================
    st.markdown(f"""
        <style>
        /* Fundo geral da tela: Cinza Claro #E0E0E0 */
        [data-testid="stAppViewContainer"] {{
            background-color: #E0E0E0;
            color: #333333;
            font-family: 'Inter', sans-serif;
        }}
        
        [data-testid="stHeader"] {{
            visibility: hidden;
        }}

        /* Header (Matrícula e Nome) */
        .welcome-container {{
            padding: 10px 0 20px 0;
            text-align: center; /* Centralizado */
            margin-bottom: 20px;
        }}
        
        .welcome-title {{
            font-size: 16px;
            font-weight: 800;
            color: #d97706; /* Um laranja escuro/dourado para ler bem no claro */
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .welcome-subtitle {{
            font-size: 12px;
            color: #64748b; /* Cinza médio */
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }}

        /* A MOLDURA (Container Branco centralizado com sombra) */
        .main-frame {{
            background-color: #ffffff; /* Fundo branco para destacar no cinza */
            border: 1px solid #d1d5db;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05); /* Sombra elegante */
            margin: 0 auto 20px auto;
            max-width: 700px; /* Trava o tamanho para ficar no centro */
        }}

        /* Botões Estilo Moderno Claro */
        div[data-testid="stButton"] > button {{
            background-color: #f8fafc !important; /* Cinza super claro no botão */
            color: #334155 !important; /* Letra cinza escuro */
            border: 1px solid #cbd5e1 !important; /* Borda fininha */
            border-radius: 12px !important;
            padding: 15px 5px !important; 
            font-size: 12px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            height: 85px;
            transition: all 0.3s ease !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
        }}

        /* Efeito ao passar o mouse */
        div[data-testid="stButton"] > button:hover {{
            background-color: #ffffff !important;
            border: 1px solid #00b4d8 !important; /* Borda azul ao focar */
            color: #00b4d8 !important;
            transform: translateY(-2px); /* Botão levanta um pouquinho */
            box-shadow: 0 6px 12px rgba(0,0,0,0.08) !important;
        }}

        /* Títulos internos do painel */
        .grid-label {{
            font-size: 18px;
            font-weight: 700;
            color: #1e293b;
            text-align: center;
            margin-bottom: 25px;
            text-transform: uppercase;
        }}

        /* Botão Sair Estilo Link */
        .logout-btn div[data-testid="stButton"] > button {{
            border: none !important;
            background: transparent !important;
            color: #ef4444 !important; /* Vermelho suave */
            font-size: 12px !important;
            box-shadow: none !important;
            height: auto;
            margin-top: 10px;
        }}
        .logout-btn div[data-testid="stButton"] > button:hover {{
            background: transparent !important;
            transform: none;
            text-decoration: underline;
        }}

        @media (max-width: 600px) {{
            div[data-testid="stHorizontalBlock"] {{
                flex-direction: row !important;
                gap: 10px !important;
            }}
            div[data-testid="column"] {{
                width: 50% !important;
                flex: 1 1 48% !important;
                min-width: 48% !important;
            }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- HEADER CENTRALIZADO ---
    matricula = aluno.get("numero_matricula", "0000000")
    st.markdown(f"""
        <div class="welcome-container">
            <p class="welcome-title">[{matricula}] - {aluno["nome"]}</p>
            <p class="welcome-subtitle">{aluno.get("turma", "Estudante")} // EREMPAM</p>
        </div>
    """, unsafe_allow_html=True)

    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    # =========================================================
    # ÁREA CENTRAL (A MOLDURA BRANCA)
    # =========================================================
    st.markdown('<div class="main-frame">', unsafe_allow_html=True)
    
    if st.session_state.menu_active == "home":
        st.markdown('<p class="grid-label">Terminal de Acesso</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Simulados\nAbertos", use_container_width=True):
                st.session_state.menu_active = "provas"; st.rerun()
        with col2:
            if st.button("Atividades\nConcluídas", use_container_width=True):
                st.session_state.menu_active = "historico"; st.rerun()
                
        col3, col4 = st.columns(2)
        with col3:
            if st.button("Painel de\nDesempenho", use_container_width=True):
                st.session_state.menu_active = "notas"; st.rerun()
        with col4:
            st.button("Avisos\nEscolares", disabled=True, use_container_width=True)

        col5, col6 = st.columns(2)
        with col5:
            st.button("Suporte\nTécnico", disabled=True, use_container_width=True)
        with col6:
            st.button("", disabled=True, use_container_width=True)

    # ---------------------------------------------------------
    # TELA SECUNDÁRIA: SIMULADOS ABERTOS
    # ---------------------------------------------------------
    elif st.session_state.menu_active == "provas":
        if st.button("← VOLTAR AO MENU", use_container_width=True): 
            st.session_state.menu_active = "home"; st.rerun()
            
        st.markdown('<p class="grid-label">Simulados Disponíveis</p>', unsafe_allow_html=True)
        
        turma_aluno = str(aluno.get('turma', ''))
        serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"
        
        try:
            res = db_provas.table("modelos_prova").select("*").eq("serie", serie_aluno).eq("ativa", True).execute()
            if res.data:
                for prova in res.data:
                    # Cartão da prova com visual claro
                    st.markdown(f"""
                        <div style="background-color: #f8fafc; border-left: 4px solid #00b4d8; border-radius: 8px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <div style="font-size: 16px; font-weight: 700; color: #1e293b;">{prova.get('titulo')}</div>
                            <div style="font-size: 12px; color: #64748b; margin-top: 5px;">
                                ⏱️ Duração: {prova.get('tempo_duracao', 60)} minutos
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("Acessar Simulado", key=f"p_{prova['id']}", use_container_width=True):
                        st.session_state.prova_config = prova 
                        st.session_state.etapa = "instrucoes" # GATILHO QUE CONSERTAMOS!
                        st.rerun()
            else:
                st.info("Nenhuma atividade disponível para sua série no momento.")
        except Exception as e:
            st.error(f"Erro na conexão com o servidor: {e}")

    # ---------------------------------------------------------
    # OUTRAS TELAS (Apenas espaço reservado para manter a estrutura)
    # ---------------------------------------------------------
    elif st.session_state.menu_active == "historico":
        if st.button("← VOLTAR AO MENU", use_container_width=True): 
            st.session_state.menu_active = "home"; st.rerun()
        st.markdown('<p class="grid-label">Atividades Concluídas</p>', unsafe_allow_html=True)
        st.info("O histórico será exibido aqui.")
        
    elif st.session_state.menu_active == "notas":
        if st.button("← VOLTAR AO MENU", use_container_width=True): 
            st.session_state.menu_active = "home"; st.rerun()
        st.markdown('<p class="grid-label">Painel de Desempenho</p>', unsafe_allow_html=True)
        st.info("O desempenho do aluno será exibido aqui.")

    st.markdown('</div>', unsafe_allow_html=True) # FIM DA MOLDURA BRANCA

    # Botão de Sair fora da moldura e centralizado
    st.markdown('<div class="logout-btn" style="text-align: center;">', unsafe_allow_html=True)
    if st.button("ENCERRAR SESSÃO", use_container_width=True):
        st.session_state.aluno = None
        st.session_state.etapa = "login"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)