import streamlit as st
from telas_aluno.desempenho import mostrar_tela_desempenho

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # --- HEADER DISCRETO ---
    # Usando HTML para controle total do tamanho (Nome Completo, mas pequeno)
    st.markdown(f'<p class="titulo-clean">👋 Olá, {aluno["nome"]}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitulo-clean">{aluno.get("turma", "Estudante")} | EREMPAM</p>', unsafe_allow_html=True)

    if "menu_ativo" not in st.session_state:
        st.session_state.menu_ativo = "home"

    # ---------------------------------------------------------
    # TELA 1: MENU PRINCIPAL
    # ---------------------------------------------------------
    if st.session_state.menu_ativo == "home":
        st.write("Escolha uma opção:") # Texto simples sem ser header
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Simulados", key="btn_simu", use_container_width=True):
                st.session_state.menu_ativo = "provas"; st.rerun()
            if st.button("📊 Desempenho", key="btn_desem", use_container_width=True):
                st.session_state.menu_ativo = "notas"; st.rerun()
        with col2:
            if st.button("✅ Atividades", key="btn_concl", use_container_width=True):
                st.session_state.menu_ativo = "historico"; st.rerun()
            if st.button("🚪 Sair", key="btn_sair", use_container_width=True):
                st.session_state.aluno = None; st.session_state.etapa = "login"; st.rerun()

    # ---------------------------------------------------------
    # TELA 2, 3 e 4 (Títulos Discretos)
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "provas":
        if st.button("⬅️ Voltar"): st.session_state.menu_ativo = "home"; st.rerun()
        st.markdown('<p class="titulo-clean">📝 Simulados Disponíveis</p>', unsafe_allow_html=True)
        # ... resto do código das provas ...

    elif st.session_state.menu_ativo == "historico":
        if st.button("⬅️ Voltar"): st.session_state.menu_ativo = "home"; st.rerun()
        st.markdown('<p class="titulo-clean">✅ Suas Conquistas</p>', unsafe_allow_html=True)
        # ... resto do código do histórico ...
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
    # TELA 3: ATIVIDADES CONCLUÍDAS
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "historico":
        if st.button("⬅️ Voltar ao Menu"):
            st.session_state.menu_ativo = "home"
            st.rerun()
            
        st.subheader("✅ Suas Conquistas")
        
        try:
            # 1. Busca os resultados do aluno (Igual ao seu código original que funcionava!)
            res_c = db_provas.table("resultados_provas").select("*").eq("aluno_id", str(aluno['id'])).execute()
            
            if res_c.data:
                # 2. Agrupa por prova para evitar duplicatas (já que salva por questão)
                provas_concluidas = {}
                for reg in res_c.data:
                    p_id = reg.get('prova_id')
                    if p_id and p_id not in provas_concluidas:
                        provas_concluidas[p_id] = reg

                # 3. Mapeia títulos das provas em uma segunda busca
                ids_lista = list(provas_concluidas.keys())
                res_titulos = db_provas.table("modelos_prova").select("id, titulo").in_("id", ids_lista).execute()
                mapa_titulos = {p['id']: p['titulo'] for p in res_titulos.data} if res_titulos.data else {}

                # 4. Renderiza os cards com o visual de App
                for p_id, dados in provas_concluidas.items():
                    nome_atividade = mapa_titulos.get(p_id, f"Atividade {str(p_id)[:8]}")
                    
                    with st.container(border=True):
                        st.markdown(f"### ✅ {nome_atividade}")
                        
                        data_r = str(dados.get('data_resposta', ''))[:10]
                        st.caption(f"📅 Concluída em: {data_r}")
                        
                        st.write(f"📊 **Acertos:** `{dados.get('acertos', 0)}`")
                        
                        # Botão para expandir o Diagnóstico da IA
                        if st.button("🔍 Ver Diagnóstico Pedagógico", key=f"btn_feedback_{p_id}", use_container_width=True):
                            with st.status("Buscando análise da IA...", expanded=True):
                                # Busca na tabela feedback_ia_alunos
                                res_f = db_provas.table("feedback_ia_alunos")\
                                    .select("diagnostico_pedagogico")\
                                    .eq("aluno_id", str(aluno['id']))\
                                    .eq("prova_id", p_id)\
                                    .execute()
                                
                                if res_f.data:
                                    feedback_texto = res_f.data[0].get('diagnostico_pedagogico', 'Sem detalhes.')
                                    st.info(f"💡 **Dica do Professor:**\n\n{feedback_texto}")
                                else:
                                    st.warning("O diagnóstico para esta prova ainda está sendo processado.")
            else:
                st.info("Você ainda não completou nenhuma atividade.")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

    # ---------------------------------------------------------
    # TELA 4: DESEMPENHO
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "notas":
        if st.button("⬅️ Voltar ao Menu"):
            st.session_state.menu_ativo = "home"
            st.rerun()
        
        mostrar_tela_desempenho(db_alunos, db_provas)