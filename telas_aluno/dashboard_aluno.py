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

    # Identifica a série para filtrar as provas (Ex: "2º C" vira "2º Ano")
    turma_aluno = str(aluno.get('turma', ''))
    serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"

    # --- ABA 1: PROVAS DISPONÍVEIS ---
    with aba_provas:
        try:
            # CORREÇÃO: Filtramos por 'ativa' (a coluna real do seu banco)
            res = (
                db_provas.table("modelos_prova")
                .select("*")
                .eq("serie", serie_aluno)
                .eq("ativa", True)
                .order("criado_em", desc=True)
                .execute()
            )

            provas = res.data if res and res.data else []

            if provas:
                for prova in provas:
                    with st.container(border=True):
                        col_info, col_btn = st.columns([3, 1])

                        with col_info:
                            titulo = prova.get("titulo", "Atividade sem título")
                            materia = prova.get("materia", "Geral")
                            # Tenta buscar o tempo em diferentes nomes de coluna por segurança
                            tempo = prova.get("tempo_duracao", prova.get("tempo_dur", "N/A"))
                            data_limite = prova.get("data_limite")

                            st.subheader(titulo)
                            st.write(f"📚 **Matéria:** {materia}")
                            st.caption(f"⏱️ **Tempo:** {tempo} min")

                            if data_limite:
                                st.caption(f"📅 **Prazo Final:** {data_limite}")

                        with col_btn:
                            st.write("") # Espaçador visual
                            prova_id = prova.get("id", "sem_id")
                            if st.button("Abrir Atividade", key=f"p_{prova_id}", use_container_width=True):
                                st.session_state.prova_config = prova
                                st.session_state.etapa = "instrucoes"
                                st.rerun()
            else:
                st.info(f"Nenhuma atividade nova disponível para o {serie_aluno}.")

        except Exception as e:
            st.error(f"Erro ao carregar banco de provas: {e}")

    # --- ABA 2: ATIVIDADES CONCLUÍDAS ---
    with aba_concluidas:
        st.subheader("Seu Histórico")
        try:
            res_c = db_provas.table("resultados_provas")\
                .select("*")\
                .eq("aluno_id", str(aluno['id']))\
                .execute()
            
            if res_c.data:
                for res in res_c.data:
                    with st.expander(f"✅ Atividade Finalizada (ID: {res['prova_id']})"):
                        st.write(f"**Pontuação:** {res.get('pontuacao', 0)}")
                        st.caption(f"Finalizado em: {res.get('created_at', '')[:10]}")
            else:
                st.info("Você ainda não possui atividades concluídas no sistema.")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

    # --- ABA 3: DESEMPENHO ---
    with aba_desempenho:
        # Passa as duas conexões conforme a nova estrutura do desempenho.py
        mostrar_tela_desempenho(db_alunos, db_provas)