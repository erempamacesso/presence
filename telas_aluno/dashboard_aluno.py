import streamlit as st

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # =========================================================
    # BLOCO 1: ESTILIZAÇÃO (CSS)
    # Foco: Bordas visíveis nos botões e visual Mobile
    # =========================================================
    st.markdown("""
        <style>
        /* Fundo da Página */
        [data-testid="stAppViewContainer"] {
            background-color: #E0E0E0 !important;
            font-family: 'Segoe UI', sans-serif;
        }
        
        [data-testid="stHeader"] {
            visibility: hidden;
        }

        /* Centralizador Mobile */
        .mobile-wrapper {
            max-width: 420px;
            margin: 0 auto;
            padding: 10px;
        }

        /* Linhas de Limite da Área de Comandos */
        .area-comandos {
            border-top: 1px solid #888888;
            border-bottom: 1px solid #888888;
            padding: 20px 0;
            margin: 15px 0;
        }

        /* ============================================
           WRAPPER DE BORDA PARA BOTÕES
           (Solução alternativa quando CSS direto não funciona)
           ============================================ */
        .button-border {
            border: 2px solid #555555 !important;
            border-radius: 12px !important;
            padding: 0 !important;
            display: inline-block !important;
            width: 100% !important;
            overflow: hidden !important;
        }

        .button-border > div {
            margin: 0 !important;
            padding: 0 !important;
        }

        .button-border button {
            border: none !important;
            border-radius: 10px !important;
        }

        .button-border:hover {
            border-color: #000000 !important;
            box-shadow: 0 0 0 2px rgba(0,0,0,0.1) !important;
        }

        /* ============================================
           ESTILO DOS BOTÕES - TÉCNICA AVANÇADA
           ============================================ */
        
        /* Usar outline em vez de border (mais resistente ao Streamlit) */
        button {
            outline: 2px solid #555555 !important;
            outline-offset: 0px !important;
            border: 2px solid #555555 !important;
            border-radius: 12px !important;
            transition: all 0.2s ease !important;
        }

        /* Botão dentro de stButton */
        div[data-testid="stButton"] > button {
            background-color: #9ca3af !important;
            color: #111827 !important;
            outline: 2px solid #555555 !important;
            outline-offset: 0px !important;
            border: 2px solid #555555 !important;
            border-radius: 12px !important;
            height: 65px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            transition: all 0.2s ease !important;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05) !important;
        }

        /* Wrapping adicional para pegar qualquer estrutura */
        [data-testid="stButton"] button {
            outline: 2px solid #555555 !important;
            outline-offset: 0px !important;
            border: 2px solid #555555 !important;
        }

        /* ============================================
           EFEITO HOVER - BORDA FICA MAIS ESCURA
           ============================================ */
        button:hover {
            background-color: #374151 !important;
            color: #FFFFFF !important;
            border-color: #000000 !important;
            outline-color: #000000 !important;
        }

        div[data-testid="stButton"] > button:hover {
            background-color: #374151 !important;
            color: #FFFFFF !important;
            border-color: #000000 !important;
            outline-color: #000000 !important;
        }

        /* ============================================
           ESTADO ATIVO (PRESSIONADO)
           ============================================ */
        button:active {
            border-color: #111827 !important;
            outline-color: #111827 !important;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.2) !important;
        }

        /* ============================================
           ESTADO DESABILITADO
           ============================================ */
        button:disabled {
            background-color: #d1d5db !important;
            color: #9ca3af !important;
            border-color: #9ca3af !important;
            outline-color: #9ca3af !important;
            opacity: 0.6 !important;
        }
        
        /* Ajuste de colunas para ficar lado a lado no celular */
        [data-testid="column"] { width: 48% !important; flex: 1 1 48% !important; }
        [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; gap: 10px !important; }
        </style>
    """, unsafe_allow_html=True)

    # Início do Wrapper
    st.markdown('<div class="mobile-wrapper">', unsafe_allow_html=True)

    # =========================================================
    # BLOCO 2: CABEÇALHO (IDENTIDADE DO ALUNO)
    # =========================================================
    matricula = aluno.get("numero_matricula", "0000000")
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 10px;">
            <div style="color: #d97706; font-weight: 800; font-size: 13px;">ID: {matricula}</div>
            <div style="color: #222; font-weight: 700; font-size: 19px;">{aluno["nome"]}</div>
            <div style="color: #666; font-size: 11px;">{aluno.get("turma", "ESTUDANTE")} • EREMPAM</div>
        </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # BLOCO 3: ÁREA DE COMANDOS (BOTÕES GRID)
    # =========================================================
    st.markdown('<div class="area-comandos">', unsafe_allow_html=True)
    
    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    if st.session_state.menu_active == "home":
        # Linha 1
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="button-border">', unsafe_allow_html=True)
            if st.button("📝\nSimulados", use_container_width=True):
                st.session_state.menu_active = "provas"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="button-border">', unsafe_allow_html=True)
            if st.button("✅\nHistórico", use_container_width=True):
                st.session_state.menu_active = "historico"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # Linha 2
        c3, c4 = st.columns(2)
        with c3:
            st.markdown('<div class="button-border">', unsafe_allow_html=True)
            if st.button("📊\nNotas", use_container_width=True):
                st.session_state.menu_active = "notas"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c4:
            st.markdown('<div class="button-border">', unsafe_allow_html=True)
            st.button("🔔\nAvisos", disabled=True, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Linha 3
        c5, c6 = st.columns(2)
        with c5:
            st.markdown('<div class="button-border">', unsafe_allow_html=True)
            st.button("🛠️\nSuporte", disabled=True, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with c6:
            st.markdown('<div class="button-border">', unsafe_allow_html=True)
            st.button("⚙️\nPerfil", disabled=True, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.menu_active == "provas":
        if st.button("⬅ VOLTAR AO MENU", use_container_width=True):
            st.session_state.menu_active = "home"; st.rerun()
        st.write("---")
        st.info("Buscando simulados disponíveis...")

    st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================
    # BLOCO 4: RODAPÉ
    # =========================================================
    if st.button("🚪 ENCERRAR SESSÃO", use_container_width=True):
        st.session_state.aluno = None
        st.session_state.etapa = "login"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)