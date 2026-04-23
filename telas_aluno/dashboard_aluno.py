import streamlit as st

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # =========================================================
    # BLOCO 1: ESTILIZAÇÃO (CSS LIMPO E SEM LINHAS FANTASMAS)
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

        /* Espaçamento da área de botões */
        .area-comandos {
            margin: 15px 0;
        }

        /* ============================================
           O JEITO CERTO DE ESTILIZAR OS BOTÕES
           ============================================ */
        div[data-testid="stButton"] > button {
            background-color: #9ca3af !important; /* Cor Cinza */
            color: #111827 !important; /* Texto Escuro */
            
            /* AQUI ESTÁ A BORDA DO BOTÃO (SEM DIVS EXTRAS) */
            border: 2px solid #333333 !important; 
            
            border-radius: 12px !important;
            height: 65px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            transition: all 0.2s ease !important;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important;
        }

        /* Efeito ao passar o mouse ou tocar */
        div[data-testid="stButton"] > button:hover {
            background-color: #374151 !important;
            color: #FFFFFF !important;
            border-color: #000000 !important;
            transform: scale(0.98);
        }

        /* Ajuste de colunas para ficar lado a lado no celular */
        [data-testid="column"] { width: 48% !important; flex: 1 1 48% !important; }
        [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; gap: 10px !important; }
        </style>
    """, unsafe_allow_html=True)

    # Início do Wrapper (Modo Celular)
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
    # BLOCO 3: ÁREA DE COMANDOS (MENU) E BUSCA DE PROVAS
    # =========================================================
    st.markdown('<div class="area-comandos">', unsafe_allow_html=True)
    
    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    # --- TELA INICIAL (OS BOTÕES) ---
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

    # --- TELA DE PROVAS (CONECTADA AO BANCO DE DADOS) ---
    elif st.session_state.menu_active == "provas":
        if st.button("⬅ VOLTAR AO MENU", use_container_width=True):
            st.session_state.menu_active = "home"; st.rerun()
            
        st.markdown('<p style="text-align:center; font-weight:800; color:#333; margin-top:15px;">SIMULADOS DISPONÍVEIS</p>', unsafe_allow_html=True)
        
        # Filtra a série do aluno para buscar apenas provas da turma dele
        turma_aluno = str(aluno.get('turma', ''))
        serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"
        
        try:
            # Busca no Supabase apenas provas ativas para a série do aluno
            res = db_provas.table("modelos_prova").select("*").eq("serie", serie_aluno).eq("ativa", True).execute()
            
            if res.data and len(res.data) > 0:
                for prova in res.data:
                    # Cria um "Card" visual para a prova
                    st.markdown(f"""
                        <div style="background-color: #f8fafc; border-left: 4px solid #d97706; border-radius: 8px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <div style="font-size: 15px; font-weight: 700; color: #1e293b;">{prova.get('titulo', 'Simulado')}</div>
                            <div style="font-size: 12px; color: #64748b; margin-top: 5px;">
                                ⏱️ Tempo: {prova.get('tempo_duracao', 60)} min | 🧩 {len(prova.get('questoes_ids', []))} Questões
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Botão para INICIAR a prova específica
                    if st.button("INICIAR AGORA", key=f"start_prova_{prova['id']}", use_container_width=True):
                        st.session_state.prova_config = prova
                        st.session_state.etapa = "instrucoes" # Dispara o roteador no app.py
                        st.rerun()
            else:
                st.info(f"Nenhum simulado aberto no momento para o {serie_aluno}.")
                
        except Exception as e:
            st.error(f"Erro ao buscar os simulados no servidor.")

    st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================
    # BLOCO 4: RODAPÉ (SAIR)
    # =========================================================
    st.write("")
    if st.button("🚪 ENCERRAR SESSÃO", use_container_width=True):
        st.session_state.aluno = None
        st.session_state.etapa = "login"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)