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

    # Identifica a série para filtrar as provas (Ex: "2º Ano")
    serie_aluno = str(aluno.get('turma', ''))[:2] + " Ano"

    with aba_provas:
        try:
            # Busca provas que estão marcadas como 'visivel' no Projeto Provas
            res = db_provas.table("modelos_prova")\
                .select("*")\
                .eq("visivel", True)\
                .eq("serie", serie_aluno)\
                .execute()
            
            if res.data:
                for prova in res.data:
                    with st.container(border=True):
                        st.subheader(prova['titulo'])
                        st.write(f"📚 Matéria: {prova['materia']}")
                        if st.button("Abrir Atividade", key=f"p_{prova['id']}"):
                            st.session_state.prova_config = prova
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
            else:
                st.info(f"Nenhuma atividade nova para o {serie_aluno}.")
        except Exception as e:
            st.error(f"Erro ao carregar banco de provas: {e}")

    with aba_concluidas:
        st.write("Aqui aparecerão seus resultados passados.")
        # Opcional: Adicionar busca na tabela resultados_provas aqui

    with aba_desempenho:
        # CHAMA A TELA DE DESEMPENHO USANDO OS DOIS BANCOS
        # db_alunos (Notas da Chamada) e db_provas (Histórico de Simulados)
        mostrar_tela_desempenho(db_alunos, db_provas)