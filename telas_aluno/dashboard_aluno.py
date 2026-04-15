import streamlit as st
from telas_aluno.desempenho import mostrar_tela_desempenho

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno
    
    st.markdown(f"## 👋 Bem-vindo, {aluno['nome']}!")
    
    aba_provas, aba_concluidas, aba_desempenho = st.tabs([
        "📝 Provas Disponíveis", 
        "✅ Atividades Concluídas", 
        "📊 Meu Desempenho"
    ])

    # Filtro de série
    turma_aluno = str(aluno.get('turma', ''))
    serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"

    # --- ABA 1: PROVAS DISPONÍVEIS ---
    with aba_provas:
        try:
            res = db_provas.table("modelos_prova").select("*")\
                .eq("serie", serie_aluno)\
                .eq("ativa", True)\
                .execute()

            if res.data:
                for prova in res.data:
                    with st.container(border=True):
                        col_info, col_btn = st.columns([3, 1])
                        with col_info:
                            st.subheader(prova.get("titulo", "Sem título"))
                            st.write(f"📚 Matéria: {prova.get('materia', 'Geral')}")
                        with col_btn:
                            if st.button("Abrir Atividade", key=f"p_{prova['id']}", use_container_width=True):
                                st.session_state.prova_config = prova
                                st.session_state.etapa = "instrucoes"
                                st.rerun()
            else:
                st.info(f"Nenhuma atividade disponível para o {serie_aluno}.")
        except Exception as e:
            st.error(f"Erro no banco de provas: {e}")

    # --- ABA 2: ATIVIDADES CONCLUÍDAS (AGORA COM FEEDBACK IA) ---
    with aba_concluidas:
        st.subheader("Seu Histórico e Diagnóstico")
        try:
            # 1. Busca os resultados do aluno
            res_c = db_provas.table("resultados_provas").select("*").eq("aluno_id", str(aluno['id'])).execute()
            
            if res_c.data:
                # 2. Agrupa por prova para evitar duplicatas
                provas_concluidas = {}
                for reg in res_c.data:
                    p_id = reg.get('prova_id')
                    if p_id and p_id not in provas_concluidas:
                        provas_concluidas[p_id] = reg

                # 3. Mapeia títulos das provas
                ids_lista = list(provas_concluidas.keys())
                res_titulos = db_provas.table("modelos_prova").select("id, titulo").in_("id", ids_lista).execute()
                mapa_titulos = {p['id']: p['titulo'] for p in res_titulos.data} if res_titulos.data else {}

                # 4. Renderiza os cards
                for p_id, dados in provas_concluidas.items():
                    nome_atividade = mapa_titulos.get(p_id, f"Atividade {str(p_id)[:8]}")
                    
                    # Cria um container visual para a atividade
                    with st.container(border=True):
                        col_t, col_d = st.columns([3, 1])
                        col_t.markdown(f"#### ✅ {nome_atividade}")
                        
                        data_r = str(dados.get('data_resposta', ''))[:10]
                        col_d.caption(f"📅 {data_r}")

                        c1, c2, c3 = st.columns([1, 1, 2])
                        c1.metric("Acertos", f"{dados.get('acertos', 0)}")
                        
                        # Botão para expandir o Diagnóstico da IA
                        if c3.button("Ver Diagnóstico Pedagógico", key=f"btn_feedback_{p_id}", use_container_width=True):
                            with st.status("Buscando análise da IA...", expanded=True):
                                # Busca na tabela feedback_ia_alunos
                                res_f = db_provas.table("feedback_ia_alunos")\
                                    .select("diagnostico_pedagogico")\
                                    .eq("aluno_id", str(aluno['id']))\
                                    .eq("prova_id", p_id)\
                                    .execute()
                                
                                if res_f.data:
                                    feedback_texto = res_f.data[0].get('diagnostico_pedagogico', 'Sem detalhes.')
                                    st.write("---")
                                    st.info(f"💡 **Dica do Professor IA:**\n\n{feedback_texto}")
                                else:
                                    st.warning("O diagnóstico para esta prova ainda está sendo processado.")
            else:
                st.info("Você ainda não possui atividades concluídas.")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

    # --- ABA 3: DESEMPENHO ---
    with aba_desempenho:
        mostrar_tela_desempenho(db_alunos, db_provas)