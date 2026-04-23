import streamlit as st

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # ==========================================
    # CSS: MOLDURA INTEGRADA AO FUNDO (#E0E0E0)
    # ==========================================
    st.markdown(f"""
        <style>
        /* 1. Fundo Global e da Moldura Unificados */
        [data-testid="stAppViewContainer"] {{
            background-color: #E0E0E0 !important;
            font-family: 'Segoe UI', sans-serif;
        }}
        
        [data-testid="stHeader"] {{
            visibility: hidden;
        }}

        /* 2. A Moldura Central (Agora com a cor do fundo) */
        .moldura-central {{
            background-color: #E0E0E0; /* Mesma cor do fundo */
            border: 2px solid #333333; /* Borda forte que define o frame */
            border-radius: 15px;
            padding: 30px 15px;
            max-width: 500px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            min-height: 70vh;
            box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
        }}

        /* 3. Cabeçalho de Identificação */
        .header-box {{
            text-align: center;
            margin-bottom: 25px;
            border-bottom: 1px solid #333;
            padding-bottom: 15px;
        }}
        
        .txt-matricula {{
            color: #d97706; /* Dourado/Laranja */
            font-weight: 800;
            font-size: 14px;
            margin: 0;
        }}
        
        .txt-aluno {{
            color: #1f2937;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            margin: 5px 0;
        }}

        /* 4. Botões Estilo Grayscale (Dentro da Moldura) */
        div[data-testid="stButton"] > button {{
            background-color: #9ca3af !important; /* Cinza */
            color: #111827 !important;
            border: 1px solid #374151 !important;
            border-radius: 30px !important;
            height: 60px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            transition: all 0.3s ease !important;
            margin-bottom: 10px;
        }}

        /* Efeito de Hover */
        div[data-testid="stButton"] > button:hover {{
            background-color: #374151 !important; /* Escurece */
            color: #FFFFFF !important; /* Texto brilha */
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
        }}
        
        /* Botão de Sair (Diferenciado) */
        .btn-sair div[data-testid="stButton"] > button {{
            background-color: transparent !important;
            border: none !important;
            color: #b91c1c !important;
            font-size: 11px !important;
            height: auto !important;
            box-shadow: none !important;
        }}

        /* Ajuste de colunas para telas pequenas */
        @media (max-width: 600px) {{
            div[data-testid="stHorizontalBlock"] {{
                display: flex !important;
                flex-direction: row !important;
            }}
            div[data-testid="column"] {{
                width: 50% !important;
                flex: 1 1 50% !important;
            }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- INÍCIO DO CONTEÚDO DENTRO DA MOLDURA ---
    st.markdown('<div class="moldura-central">', unsafe_allow_html=True)

    # 1. INFO DO ALUNO (Sempre visível no topo da moldura)
    matricula = aluno.get("numero_matricula", "0000000")
    st.markdown(f"""
        <div class="header-box">
            <p class="txt-matricula">MATRÍCULA: {matricula}</p>
            <p class="txt-aluno">{aluno["nome"]}</p>
            <p style="font-size:11px; color:#4b5563; margin:0;">{aluno.get("turma", "SÉRIE")} // EREMPAM</p>
        </div>
    """, unsafe_allow_html=True)

    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    # 2. GRID DE BOTOES (2 COLUNAS X 3 LINHAS)
    if st.session_state.menu_active == "home":
        # Linha 1
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Simulados\nAbertos", use_container_width=True):
                st.session_state.menu_active = "provas"; st.rerun()
        with c2:
            if st.button("Atividades\nConcluídas", use_container_width=True):
                st.session_state.menu_active = "historico"; st.rerun()

        # Linha 2
        c3, c4 = st.columns(2)
        with c3:
            if st.button("Meu\nDesempenho", use_container_width=True):
                st.session_state.menu_active = "notas"; st.rerun()
        with c4:
            st.button("Avisos\nEscolares", disabled=True, use_container_width=True)

        # Linha 3
        c5, c6 = st.columns(2)
        with c5:
            st.button("Suporte\nAluno", disabled=True, use_container_width=True)
        with c6:
            st.button("Config.\nConta", disabled=True, use_container_width=True)

    # 3. LÓGICA DE TELAS INTERNAS (Mantendo dentro da moldura)
    elif st.session_state.menu_active == "provas":
        if st.button("⬅ VOLTAR", use_container_width=True):
            st.session_state.menu_active = "home"; st.rerun()
            
        st.write("---")
        
        turma_aluno = str(aluno.get('turma', ''))
        serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"
        
        try:
            res = db_provas.table("modelos_prova").select("*").eq("serie", serie_aluno).eq("ativa", True).execute()
            if res.data:
                for prova in res.data:
                    st.markdown(f"**{prova.get('titulo')}**")
                    if st.button(f"INICIAR", key=f"p_{prova['id']}", use_container_width=True):
                        st.session_state.prova_config = prova
                        st.session_state.etapa = "instrucoes"
                        st.rerun()
            else:
                st.info("Nenhuma prova no momento.")
        except:
            st.error("Erro ao carregar simulados.")

    # 4. BOTÃO SAIR (No rodapé da moldura)
    st.markdown('<div style="flex-grow: 1;"></div>', unsafe_allow_html=True) # Empurra o botão sair para o fim
    st.markdown('<div class="btn-sair">', unsafe_allow_html=True)
    if st.button("SAIR DO SISTEMA", use_container_width=True):
        st.session_state.aluno = None
        st.session_state.etapa = "login"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # FIM DA MOLDURA CENTRAL