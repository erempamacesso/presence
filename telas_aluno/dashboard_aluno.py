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

    # --- ABA 2: ATIVIDADES CONCLUÍDAS (BLINDADO) ---
    with aba_concluidas:
        st.subheader("Seu Histórico")
        try:
            # 1. Busca todos os registros do aluno (usando * para evitar erro de coluna)
            res_c = db_provas.table("resultados_provas")\
                .select("*")\
                .eq("aluno_id", str(aluno['id']))\
                .execute()
            
            if res_c.data:
                # 2. Agrupamento por prova_id (evita repetir o card para cada questão da prova)
                provas_concluidas = {}
                for reg in res_c.data:
                    p_id = reg.get('prova_id')
                    if p_id and p_id not in provas_concluidas:
                        provas_concluidas[p_id] = reg

                # 3. Busca títulos das provas para exibir bonito
                ids_lista = list(provas_concluidas.keys())
                res_titulos = db_provas.table("modelos_prova").select("id, titulo").in_("id", ids_lista).execute()
                mapa_titulos = {p['id']: p['titulo'] for p in res_titulos.data} if res_titulos.data else {}

                # 4. Renderização dos cards
                for p_id, dados in provas_concluidas.items():
                    nome_atividade = mapa_titulos.get(p_id, f"Atividade {str(p_id)[:8]}")
                    
                    with st.expander(f"✅ {nome_atividade}"):
                        c1, c2 = st.columns(2)
                        
                        # Usa 'acertos' conforme sua imagem da estrutura
                        pontos = dados.get('acertos', 0)
                        c1.metric("Pontuação", f"{pontos}")
                        
                        # Usa 'data_resposta' conforme sua imagem da estrutura
                        data_bruta = dados.get('data_resposta', '---')
                        data_limpa = str(data_bruta)[:10] if data_bruta else "---"
                        c2.write(f"**Data:** {data_limpa}")
                        
                        if st.button("Revisar", key=f"rev_{p_id}"):
                            st.info("Detalhes das questões em desenvolvimento.")
            else:
                st.info("Você ainda não possui atividades concluídas.")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

    # --- ABA 3: DESEMPENHO ---
    with aba_desempenho:
        mostrar_tela_desempenho(db_alunos, db_provas)