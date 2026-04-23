import streamlit as st

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # =========================================================
    # BLOCO 1: ESTILIZAÇÃO (CSS)
    # Foco: Bordas visíveis nos botões e visual Mobile
    # =========================================================
    st.markdown(f"""
        <style>
        /* Fundo da Página */
        [data-testid="stAppViewContainer"] {{
            background-color: #E0E0E0 !important;
            font-family: 'Segoe UI', sans-serif;
        }}
        
        [data-testid="stHeader"] {{
            visibility: hidden;
        }}

        /* Centralizador Mobile */
        .mobile-wrapper {{
            max-width: 420px;
            margin: 0 auto;
            padding: 10px;
        }}

        /* Linhas de Limite da Área de Comandos */
        .area-comandos {{
            border-top: 1px solid #888888;
            border-bottom: 1px solid #888888;
            padding: 20px 0;
            margin: 15px 0;
        }}

        /* ESTILO DOS BOTÕES COM BORDA DEFINIDA */
        div[data-testid="stButton"] > button {{
            background-color: #9ca3af !important; /* Cor interna do botão */
            color: #111827 !important; 
            
            /* AQUI ESTÁ A LINHA DE DELIMITAÇÃO DO BOTÃO */
            border: 2px solid #555555 !important; /* Borda cinza escuro para marcar o limite */
            
            border-radius: 12px !important;
            height: 65px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            transition: all 0.2s ease !important;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05) !important;
        }}

        /* Efeito ao Passar o Mouse ou Tocar */
        div[data-testid="stButton"] > button:hover {{
            background-color: #374151 !important; 
            color: #FFFFFF !important;
            border-color: #000000 !important; /* Borda escurece no foco */
        }}
        
        /* Ajuste de colunas para ficar lado a lado no celular */
        [data-testid="column"] {{ width: 48% !important; flex: 1 1 48% !important; }}
        [data-testid="stHorizontalBlock"] {{ display: flex !important; flex-direction: row !important; gap: 10px !important; }}
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
            if st.button("📝\nSimulados", use_container_width=True):
                st.session_state.menu_active = "provas"; st.rerun()
        with c2:
            if st.button("✅\nHistórico", use_container_width=True):
                st.session_state.menu_active = "historico"; st.rerun()

        # Linha 2
        c3, c4 = st.columns(2)
        with c3:
            if st.button("📊\nNotas", use_container_width=True):
                st.session_state.menu_active = "notas"; st.rerun()
        with c4:
            st.button("🔔\nAvisos", disabled=True, use_container_width=True)

        # Linha 3
        c5, c6 = st.columns(2)
        with c5:
            st.button("🛠️\nSuporte", disabled=True, use_container_width=True)
        with c6:
            st.button("⚙️\nPerfil", disabled=True, use_container_width=True)

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