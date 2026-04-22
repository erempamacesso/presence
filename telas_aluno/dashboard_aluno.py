import streamlit as st
from telas_aluno.desempenho import mostrar_tela_desempenho

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # ==========================================
    # CSS: MOLDURA FINA E GRID ORGANIZADO
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

        /* Header (Matrícula amarela e Nome) */
        .welcome-container {{
            padding: 10px 0 20px 0;
            text-align: left;
            margin-bottom: 10px;
        }}
        
        .welcome-title {{
            font-size: 13px;
            font-weight: 700;
            color: #facc15; 
            margin: 0;
            text-transform: uppercase;
        }}
        
        .welcome-subtitle {{
            font-size: 11px;
            color: #ffffff; 
            opacity: 0.7;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        /* A MOLDURA (Container que delimita os botões) */
        .main-frame {{
            border: 1px solid rgba(255, 255, 255, 0.15); /* Linha fina cinza claro */
            border-radius: 20px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.02);
            margin-bottom: 20px;
        }}

        /* Botões com borda de 1px (Mais fininha) */
        div[data-testid="stButton"] > button {{
            background-color: transparent !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.4) !important; /* Borda fina */
            border-radius: 12px !important;
            padding: 15px 5px !important; 
            font-size: 11px !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            height: 80px;
            transition: all 0.3s ease !important;
        }}

        div[data-testid="stButton"] > button:hover {{
            background-color: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid #ffffff !important;
        }}

        /* Botão Sair Estilo Link */
        .logout-btn div[data-testid="stButton"] > button {{
            border: none !important;
            background: transparent !important;
            color: rgba(255, 255, 255, 0.6) !important;
            font-size: 12px !important;
            height: auto;
            margin-top: 10px;
        }}

        /* Ajuste Mobile para manter 2 colunas na moldura */
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

    # --- HEADER ---
    matricula = aluno.get("numero_matricula", "0000000")
    st.markdown(f"""
        <div class="welcome-container">
            <p class="welcome-title">[{matricula}] - {aluno["nome"]}</p>
            <p class="welcome-subtitle">{aluno.get("turma", "Estudante")} // EREMPAM</p>
        </div>
    """, unsafe_allow_html=True)

    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    # ---------------------------------------------------------
    # MENU COM MOLDURA
    # ---------------------------------------------------------
    if st.session_state.menu_active == "home":
        
        # Início da Moldura
        st.markdown('<div class="main-frame">', unsafe_allow_html=True)
        
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
            st.button("", disabled=True, use_container_width=True) # Botão vazio

        st.markdown('</div>', unsafe_allow_html=True) # Fim da Moldura

        # Botão Sair fora da moldura
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("ENCERRAR SESSÃO", use_container_width=True):
            st.session_state.aluno = None
            st.session_state.etapa = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ... (Restante das telas de Provas e Notas segue a mesma lógica)