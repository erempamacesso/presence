import streamlit as st

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # ==========================================
    # CSS: CLONE DA IDENTIDADE VISUAL "TELA"
    # ==========================================
    st.markdown(f"""
        <style>
        /* 1. Fundo Global Neutro */
        [data-testid="stAppViewContainer"] {{
            background-color: #E0E0E0 !important;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        [data-testid="stHeader"] {{
            visibility: hidden;
        }}

        /* 2. Moldura Centralizada (O Frame da Imagem) */
        .moldura-central {{
            background-color: #FFFFFF;
            border: 2px solid #333333;
            border-radius: 10px;
            padding: 40px 20px;
            max-width: 550px;
            margin: 0 auto;
            min-height: 80vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }}

        /* 3. Caixa de Informações do Aluno */
        .info-aluno-box {{
            background-color: #D1D5DB; /* Cinza médio */
            padding: 10px 20px;
            border-radius: 5px;
            text-align: center;
            width: 100%;
            margin-bottom: 20px;
        }}
        
        .info-txt-matricula {{
            color: #d97706; /* Laranja da imagem */
            font-weight: 800;
            font-size: 13px;
            margin: 0;
        }}
        
        .info-txt-nome {{
            color: #4b5563;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            margin: 0;
        }}

        /* 4. Estilização dos Botões (Escala de Cinza + Efeito) */
        div[data-testid="stButton"] > button {{
            background-color: #9ca3af !important; /* Cinza Base */
            color: #111827 !important; /* Texto Escuro */
            border: 1px solid #374151 !important;
            border-radius: 50px !important; /* Formato Pílula da Imagem */
            height: 55px !important;
            font-weight: 700 !important;
            font-size: 12px !important;
            text-transform: uppercase !important;
            transition: all 0.3s ease !important;
            box-shadow: inset 0 -4px 0 rgba(0,0,0,0.2) !important; /* Efeito 3D leve */
        }}

        /* Efeito de Hover (Muda cor ao passar o mouse) */
        div[data-testid="stButton"] > button:hover {{
            background-color: #374151 !important; /* Cinza Escuro */
            color: #FFFFFF !important; /* Texto Branco */
            transform: scale(1.02);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2) !important;
        }}

        /* Botões Especiais (Voltar e Sair) */
        .btn-acao-topo div[data-testid="stButton"] > button {{
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 13px !important;
            color: #000000 !important;
            height: auto !important;
        }}
        
        .btn-acao-topo div[data-testid="stButton"] > button:hover {{
            background-color: transparent !important;
            color: #d97706 !important;
            transform: none;
        }}

        /* Forçar Grid 2 colunas no Mobile */
        @media (max-width: 600px) {{
            div[data-testid="stHorizontalBlock"] {{
                flex-direction: row !important;
                display: flex !important;
            }}
            div[data-testid="column"] {{
                width: 50% !important;
                flex: 1 1 48% !important;
            }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- INÍCIO DA MOLDURA CENTRAL ---
    st.markdown('<div class="moldura-central">', unsafe_allow_html=True)
    
    st.markdown('<h3 style="text-align:center; color:#000; margin-bottom:20px;">MOLDURA CENTRAL</h3>', unsafe_allow_html=True)

    # 1. BLOCO DE INFOS (HEADER)
    matricula = aluno.get("numero_matricula", "0000000")
    st.markdown(f"""
        <div class="info-aluno-box">
            <p class="info-txt-matricula">[{matricula}] - {aluno["nome"]}</p>
            <p class="info-txt-nome">{aluno.get("turma", "SERIE")} // EREMPAM</p>
        </div>
    """, unsafe_allow_html=True)

    # 2. BOTÕES DE AÇÃO RÁPIDA (VOLTAR / SAIR)
    col_v, col_s = st.columns(2)
    with col_v:
        st.markdown('<div class="btn-acao-topo">', unsafe_allow_html=True)
        if st.button("⬅ VOLTAR", key="btn_voltar_top"):
            st.session_state.menu_active = "home"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_s:
        st.markdown('<div class="btn-acao-topo">', unsafe_allow_html=True)
        if st.button("🚪 ENCERRAR SEÇÃO", key="btn_sair_top"):
            st.session_state.aluno = None
            st.session_state.etapa = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("---") # Linha divisória fina

    # 3. O GRID DE BOTÕES (TABELA INVISÍVEL 2x3)
    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

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
            if st.button("Painel de\nDesempenho", use_container_width=True):
                st.session_state.menu_active = "notas"; st.rerun()
        with c4:
            if st.button("Avisos", use_container_width=True):
                pass # Espaço para avisos

        # Linha 3
        c5, c6 = st.columns(2)
        with c5:
            if st.button("Suporte", use_container_width=True):
                pass
        with c6:
            st.empty() # Espaço vazio como na imagem

    # --- LOGICA DAS TELAS DE PROVAS ---
    elif st.session_state.menu_active == "provas":
        st.markdown('<p style="color:#333; font-weight:bold; text-align:center;">SIMULADOS DISPONÍVEIS</p>', unsafe_allow_html=True)
        
        turma_aluno = str(aluno.get('turma', ''))
        serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"
        
        try:
            res = db_provas.table("modelos_prova").select("*").eq("serie", serie_aluno).eq("ativa", True).execute()
            if res.data:
                for prova in res.data:
                    with st.container():
                        st.markdown(f"""
                            <div style="background:#f3f4f6; padding:10px; border-radius:10px; margin-bottom:10px; border:1px solid #ccc;">
                                <b style="color:#000">{prova.get('titulo')}</b><br>
                                <small style="color:#666">Duração: {prova.get('tempo_duracao')}min</small>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button("INICIAR AGORA", key=f"p_{prova['id']}", use_container_width=True):
                            st.session_state.prova_config = prova
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
            else:
                st.info("Nenhuma prova ativa.")
        except:
            st.error("Erro ao carregar.")

    st.markdown('</div>', unsafe_allow_html=True) # FIM DA MOLDURA CENTRAL