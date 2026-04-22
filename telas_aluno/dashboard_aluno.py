import streamlit as st
from telas_aluno.desempenho import mostrar_tela_desempenho

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # ==========================================
    # CSS: MINIMALISMO EXTREMO & GRID 3x4
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

        /* Header Minimalista */
        .welcome-container {{
            padding: 20px 0;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 30px;
        }}
        
        .welcome-title {{
            font-size: 18px; /* Reduzido para caber em uma linha */
            font-weight: 500;
            letter-spacing: 0.5px;
            color: #ffffff;
            margin: 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis; /* Se o nome for gigante, ele corta com ... */
        }}
        
        .welcome-subtitle {{
            font-size: 10px;
            color: #ffffff; /* Alto contraste */
            opacity: 0.8;
            margin-top: 2px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        /* Botões em Grade Estilo Dashboard Técnico */
        div[data-testid="stButton"] > button {{
            background-color: rgba(255, 255, 255, 0.02) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 2px !important;
            padding: 25px 10px !important; /* Mais alto para parecer um bloco de grade */
            font-size: 11px !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 1.5px !important;
            transition: all 0.3s ease !important;
            width: 100%;
            height: 100px; /* Altura fixa para manter a grade simétrica */
        }}

        div[data-testid="stButton"] > button:hover {{
            background-color: #ffffff !important;
            color: #0b132b !important;
            border: 1px solid #ffffff !important;
        }}

        /* Label da Seção */
        .grid-label {{
            font-size: 10px;
            text-transform: uppercase;
            color: #5d6d81;
            letter-spacing: 2px;
            margin-bottom: 15px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- HEADER ---
    st.markdown(f"""
        <div class="welcome-container">
            <h1 class="welcome-title">{aluno["nome"].upper()}</h1>
            <p class="welcome-subtitle">{aluno.get("turma", "Estudante")} // EREMPAM</p>
        </div>
    """, unsafe_allow_html=True)

    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    # ---------------------------------------------------------
    # MENU PRINCIPAL (GRADE 3xN)
    # ---------------------------------------------------------
    if st.session_state.menu_active == "home":
        st.markdown('<p class="grid-label">Terminal de Acesso</p>', unsafe_allow_html=True)
        
        # Criando a Grade 3x4 (3 colunas)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Simulados\nAbertos", use_container_width=True):
                st.session_state.menu_active = "provas"
                st.rerun()
        
        with col2:
            if st.button("Atividades\nConcluídas", use_container_width=True):
                st.session_state.menu_active = "historico"
                st.rerun()
                
        with col3:
            if st.button("Painel de\nDesempenho", use_container_width=True):
                st.session_state.menu_active = "notas"
                st.rerun()

        # Segunda linha da grade
        col4, col5, col6 = st.columns(3)
        
        with col4:
            if st.button("Encerrar\nSessão", use_container_width=True):
                st.session_state.aluno = None
                st.session_state.etapa = "login"
                st.rerun()
        
        with col5:
            # Botão vazio/placeholder para manter a estética da grade
            st.button("Suporte\nTécnico", disabled=True, use_container_width=True)
            
        with col6:
            st.button("Avisos\nEscolares", disabled=True, use_container_width=True)

    # ---------------------------------------------------------
    # TELAS SECUNDÁRIAS (PROVAS / NOTAS)
    # ---------------------------------------------------------
    elif st.session_state.menu_active == "provas":
        if st.button("← VOLTAR", use_container_width=True): 
            st.session_state.menu_active = "home"
            st.rerun()
        st.markdown('<p class="grid-label">Simulados Disponíveis</p>', unsafe_allow_html=True)
        # ... (restante da lógica de busca de provas que você já tem)

    elif st.session_state.menu_active == "notas":
        if st.button("← VOLTAR", use_container_width=True): 
            st.session_state.menu_active = "home"
            st.rerun()
        mostrar_tela_desempenho(db_alunos, db_provas)