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

    # Identifica a série para filtrar as provas
    turma_aluno = str(aluno.get('turma', ''))
    serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"

    # --- ABA 1: PROVAS DISPONÍVEIS ---
    with aba_provas:
        try:
            # Nota: Em modelos_prova a coluna de data é 'criado_em' (visto no seu Print 2)
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
                st.info(f"Nenhuma atividade nova para o {serie_aluno}.")
        except Exception as e:
            st.error(f"Erro ao carregar banco de provas: {e}")

    # --- ABA 2: ATIVIDADES CONCLUÍDAS ---
    with aba_concluidas:
        st.subheader("Seu Histórico")
        try:
            # CORREÇÃO AQUI: Trocado 'created_at' por 'data_envio'
            res_c = db_provas.table("resultados_provas")\
                .select("prova_id, acertos, data_envio")\
                .eq("aluno_id", str(aluno['id']))\
                .execute()
            
            if res_c.data:
                # Lógica de agrupamento para evitar repetições
                provas_unicas = {}
                for item in res_c.data:
                    p_id = item['prova_id']
                    if p_id not in provas_unicas:
                        provas_unicas[p_id] = item

                # Busca nomes das provas para o título
                ids_lista = list(provas_unicas.keys())
                res_nomes = db_provas.table("modelos_prova")\
                    .select("id, titulo")\
                    .in_("id", ids_lista)\
                    .execute()
                
                nomes_map = {p['id']: p['titulo'] for p in res_nomes.data} if res_nomes.data else {}

                for p_id, dados in provas_unicas.items():
                    titulo_prova = nomes_map.get(p_id, f"Atividade {p_id[:8]}")
                    with st.expander(f"✅ {titulo_prova}"):
                        c1, c2 = st.columns(2)
                        c1.metric("Acertos", f"{dados.get('acertos', 0)}")
                        # CORREÇÃO AQUI: Trocado 'created_at' por 'data_envio'
                        data_final = dados.get('data_envio', '---')
                        c2.write(f"**Finalizado em:** {data_final[:10] if data_final else '---'}")
                        
                        if st.button("Ver Revisão", key=f"rev_{p_id}"):
                            st.info("A revisão detalhada será liberada em breve.")
            else:
                st.info("Você ainda não concluiu nenhuma atividade.")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

    # --- ABA 3: DESEMPENHO ---
    with aba_desempenho:
        mostrar_tela_desempenho(db_alunos, db_provas)