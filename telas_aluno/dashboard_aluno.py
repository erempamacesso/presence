import streamlit as st
from telas_aluno.desempenho import mostrar_tela_desempenho

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno
    
    # CSS Específico para deixar os botões com cara de "Cards de App"
    st.markdown("""
        <style>
        .stButton > button {
            width: 100%;
            height: 120px !important;
            border-radius: 15px !important;
            background-color: #ffffff !important;
            color: #31333F !important;
            border: 1px solid #e0e0e0 !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
            font-size: 18px !important;
            font-weight: bold !important;
            flex-direction: column !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 10px !important;
        }
        
        .stButton > button:hover {
            border-color: #4CAF50 !important;
            color: #4CAF50 !important;
            background-color: #f9fff9 !important;
            transform: translateY(-2px);
            transition: all 0.2s ease;
        }

        div[data-testid="stVerticalBlock"] > div:last-child .stButton > button {
            border-color: #ff4b4b22 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if "menu_ativo" not in st.session_state:
        st.session_state.menu_ativo = "home"

    # --- HEADER DO APP (Agora com NOME COMPLETO) ---
    st.markdown(f"## 👋 Olá, {aluno['nome']}!")
    st.caption(f"📍 {aluno.get('turma', 'Estudante')} | EREMPAM")

    # ---------------------------------------------------------
    # TELA 1: MENU PRINCIPAL (GRID DE CARDS)
    # ---------------------------------------------------------
    if st.session_state.menu_ativo == "home":
        st.write("### O que vamos fazer agora?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📝\nSimulados\nDisponíveis", key="btn_simu", use_container_width=True):
                st.session_state.menu_ativo = "provas"
                st.rerun()
            
            if st.button("📊\nMeu\nDesempenho", key="btn_desem", use_container_width=True):
                st.session_state.menu_ativo = "notas"
                st.rerun()

        with col2:
            if st.button("✅\nAtividades\nConcluídas", key="btn_concl", use_container_width=True):
                st.session_state.menu_ativo = "historico"
                st.rerun()

            if st.button("🚪\nSair do\nPortal", key="btn_sair", use_container_width=True):
                st.session_state.aluno = None
                st.session_state.etapa = "login"
                st.rerun()

    # ---------------------------------------------------------
    # TELA 2: PROVAS DISPONÍVEIS
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "provas":
        if st.button("⬅️ Voltar ao Menu"):
            st.session_state.menu_ativo = "home"
            st.rerun()
        
        st.subheader("📝 Simulados para Você")
        
        turma_aluno = str(aluno.get('turma', ''))
        serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"

        try:
            res = db_provas.table("modelos_prova").select("*").eq("serie", serie_aluno).eq("ativa", True).execute()
            if res.data:
                for prova in res.data:
                    with st.container(border=True):
                        st.markdown(f"**{prova.get('titulo')}**")
                        st.caption(f"Questões: {prova.get('config_prova', {}).get('total_questoes', 'N/A')}")
                        if st.button(f"Iniciar Prova", key=f"start_{prova['id']}", type="primary"):
                            st.session_state.prova_config = prova
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
            else:
                st.info("Nenhuma prova disponível para sua série no momento.")
        except Exception as e:
            st.error(f"Erro ao buscar provas: {e}")

    # ---------------------------------------------------------
    # TELA 3: ATIVIDADES CONCLUÍDAS (Ajuste o nome da Tabela aqui!)
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "historico":
        if st.button("⬅️ Voltar ao Menu"):
            st.session_state.menu_ativo = "home"
            st.rerun()
            
        st.subheader("✅ Suas Conquistas")
        
        try:
            # 🛑 ATENÇÃO: TROQUE 'respostas_alunos' PELO NOME REAL DA SUA TABELA!
            nome_da_tabela = "modelos_prova" 
            
            res_r = db_provas.table(nome_da_tabela).select("*, modelos_prova(titulo)").eq("aluno_id", str(aluno['id'])).execute()
            
            if res_r.data:
                for resp in res_r.data:
                    with st.container(border=True):
                        titulo = resp.get('modelos_prova', {}).get('titulo', 'Prova Finalizada')
                        nota = resp.get('nota_final', 0)
                        st.markdown(f"**{titulo}**")
                        st.write(f"Nota: `{nota:.1f}`")
                        
                        if st.button("Ver Diagnóstico IA", key=f"ia_{resp['id']}"):
                            st.toast("Buscando análise...")
                            # Aqui entra a sua lógica de IA
            else:
                st.info("Você ainda não completou nenhuma atividade.")
        except Exception as e:
            st.error(f"Erro no histórico: {e}")

    # ---------------------------------------------------------
    # TELA 4: DESEMPENHO
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "notas":
        if st.button("⬅️ Voltar ao Menu"):
            st.session_state.menu_ativo = "home"
            st.rerun()
        
        mostrar_tela_desempenho(db_alunos, db_provas)