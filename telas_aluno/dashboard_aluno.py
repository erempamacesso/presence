import streamlit as st

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # =========================================================
    # BLOCO 1: ESTILIZAÇÃO (CSS SEGURO E SEM HTML FATIADO)
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

        .area-comandos {
            margin: 15px 0;
        }

        /* ============================================
           ESTILO DOS BOTÕES (CORRETO E SEGURO)
           ============================================ */
        div[data-testid="stButton"] > button {
            background-color: #4b5563 !important; /* Fundo Cinza Escuro */
            color: #ffffff !important; /* Texto Branco */
            border: none !important; 
            border-radius: 12px !important;
            height: 65px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
            transition: all 0.2s ease !important;
        }

        div[data-testid="stButton"] > button:hover {
            background-color: #1f2937 !important; /* Fica quase preto ao clicar */
            transform: scale(0.98);
        }

        /* ============================================
           BOTÃO DE INICIAR PROVA (VERDE VIBRANTE)
           ============================================ */
        .btn-iniciar div[data-testid="stButton"] > button {
            background-color: #10b981 !important; 
            font-size: 14px !important;
            font-weight: 800 !important;
            box-shadow: 0 4px 10px rgba(16, 185, 129, 0.4) !important; 
            height: 55px !important;
        }

        .btn-iniciar div[data-testid="stButton"] > button:hover {
            background-color: #059669 !important;
        }

        /* ============================================
           BOTÃO SAIR (VERMELHO DISCRETO)
           ============================================ */
        .btn-sair div[data-testid="stButton"] > button {
            background-color: transparent !important;
            color: #ef4444 !important; 
            box-shadow: none !important;
            height: auto !important;
        }
        
        .btn-sair div[data-testid="stButton"] > button:hover {
            background-color: #fee2e2 !important; 
        }

        /* Ajuste de colunas para ficar lado a lado no celular */
        [data-testid="column"] { width: 48% !important; flex: 1 1 48% !important; }
        [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; gap: 10px !important; }
        </style>
    """, unsafe_allow_html=True)

    # Início do Wrapper (Tudo aqui fica alinhado como celular)
    st.markdown('<div class="mobile-wrapper">', unsafe_allow_html=True)

    # =========================================================
    # BLOCO 2: CABEÇALHO (IDENTIDADE DO ALUNO)
    # =========================================================
    matricula = aluno.get("numero_matricula", "0000000")
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="color: #d97706; font-weight: 800; font-size: 14px;">ID: {matricula}</div>
            <div style="color: #222; font-weight: 800; font-size: 18px; line-height: 1.2;">{aluno["nome"]}</div>
            <div style="color: #555; font-size: 12px; margin-top: 5px;">{aluno.get("turma", "ESTUDANTE")} • EREMPAM</div>
        </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # BLOCO 3: MENU PRINCIPAL E BUSCA DE PROVAS
    # =========================================================
    st.markdown('<div class="area-comandos">', unsafe_allow_html=True)
    
    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    # --- TELA INICIAL (MENU COMPLETO) ---
    if st.session_state.menu_active == "home":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📝\nSimulados", use_container_width=True):
                st.session_state.menu_active = "provas"; st.rerun()
        with c2:
            if st.button("✅\nHistórico", use_container_width=True):
                st.session_state.menu_active = "historico"; st.rerun()

        c3, c4 = st.columns(2)
        with c3:
            if st.button("📊\nNotas", use_container_width=True):
                st.session_state.menu_active = "notas"; st.rerun()
        with c4:
            st.button("🔔\nAvisos", disabled=True, use_container_width=True)

        c5, c6 = st.columns(2)
        with c5:
            st.button("🛠️\nSuporte", disabled=True, use_container_width=True)
        with c6:
            st.button("⚙️\nPerfil", disabled=True, use_container_width=True)

    # --- TELA DE PROVAS (COM BANCO DE DADOS RESTAURADO) ---
    elif st.session_state.menu_active == "provas":
        if st.button("⬅ VOLTAR AO MENU", use_container_width=True):
            st.session_state.menu_active = "home"; st.rerun()
            
        st.markdown('<p style="text-align:center; font-weight:800; color:#333; margin-top:15px;">SIMULADOS DISPONÍVEIS</p>', unsafe_allow_html=True)
        
        # Filtra a série do aluno para buscar apenas as provas dele
        turma_aluno = str(aluno.get('turma', ''))
        serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"
        
        try:
            # Busca de verdade no Supabase!
            res = db_provas.table("modelos_prova").select("*").eq("serie", serie_aluno).eq("ativa", True).execute()
            
            if res.data and len(res.data) > 0:
                for prova in res.data:
                    # O "Card" visual da prova
                    st.markdown(f"""
                        <div style="background-color: #ffffff; border-left: 5px solid #10b981; border-radius: 8px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <div style="font-size: 15px; font-weight: 800; color: #1e293b;">{prova.get('titulo', 'Simulado')}</div>
                            <div style="font-size: 12px; color: #64748b; margin-top: 5px; margin-bottom: 10px;">
                                ⏱️ Tempo: {prova.get('tempo_duracao', 60)} min | 🧩 {len(prova.get('questoes_ids', []))} Questões
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # O Botão Verde de Iniciar
                    st.markdown('<div class="btn-iniciar">', unsafe_allow_html=True)
                    if st.button("INICIAR AGORA", key=f"start_prova_{prova['id']}", use_container_width=True):
                        st.session_state.prova_config = prova
                        st.session_state.etapa = "instrucoes" # Dispara o gatilho da prova
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info(f"Nenhum simulado aberto no momento para o {serie_aluno}.")
                
        except Exception as e:
            st.error("Erro ao conectar com o banco de dados das provas.")

    st.markdown('</div>', unsafe_allow_html=True) # Fim da área de comandos

    # =========================================================
    # BLOCO 4: RODAPÉ E SAÍDA
    # =========================================================
    st.write("")
    
    st.markdown('<div class="btn-sair">', unsafe_allow_html=True)
    if st.button("🚪 ENCERRAR SESSÃO", use_container_width=True):
        st.session_state.aluno = None
        st.session_state.etapa = "login"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # Fim do Wrapper Mobile