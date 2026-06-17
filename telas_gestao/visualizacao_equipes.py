import streamlit as st
import pandas as pd


def mostrar_painel_organizacao(db_alunos, db_provas):
    st.title("📊 Painel de Monitoramento - Inscrições Realizadas")
    st.markdown("---")

    # Verifica se a conexão necessária com o banco de provas está ativa
    if db_provas is None:
        st.error("🚨 Conexão com o Banco de Provas (Avaliador) não inicializada.")
        return

    # 1. Coleta de Dados Direta e Isolada (Apenas no Banco de Provas)
    try:
        with st.spinner("Carregando dados das inscrições..."):
            res_inscricoes = db_provas.table("feira_inscricoes").select("*").execute()
    except Exception as e_pr:
        st.error("🚨 Erro de conexão com o Banco de Provas (Inscrições).")
        st.info(
            "Verifique se as credenciais do projeto Avaliador estão corretas nas Secrets."
        )
        with st.expander("Detalhes do erro técnico"):
            st.code(str(e_pr))
        return

    # Se não houver nenhum dado registrado na tabela
    if not res_inscricoes.data:
        st.warning(
            "Nenhuma inscrição encontrada na tabela 'feira_inscricoes' até o momento."
        )
        return

    # 2. Convertendo os dados coletados em DataFrame
    df_inscricoes = pd.DataFrame(res_inscricoes.data)

    # 3. Painel Superior de Indicadores (Métricas Rápidas)
    total_equipes = len(df_inscricoes)

    # Contagem de turmas únicas registradas
    if "turma" in df_inscricoes.columns:
        total_turmas = df_inscricoes["turma"].nunique()
    else:
        total_turmas = 0

    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Total de Equipes Inscritas", total_equipes)
    col_m2.metric("Turmas Engajadas", total_turmas)
    st.markdown("---")

    # 4. Filtro Interativo por Turma (Criado dinamicamente com base nas turmas existentes)
    if "turma" in df_inscricoes.columns and total_turmas > 0:
        lista_turmas = sorted(df_inscricoes["turma"].dropna().unique())
        lista_turmas.insert(0, "Todas as Turmas")
        turma_selecionada = st.selectbox(
            "Filtrar visualização por Turma:", options=lista_turmas
        )

        # Aplica o filtro caso o usuário escolha uma turma específica
        if turma_selecionada != "Todas as Turmas":
            df_exibicao = df_inscricoes[df_inscricoes["turma"] == turma_selecionada]
        else:
            df_exibicao = df_inscricoes
    else:
        df_exibicao = df_inscricoes

    # 5. Apresentação das Equipes em Formato de Cartões (Cards)
    st.subheader(f"📋 Listagem de Equipes ({len(df_exibicao)})")

    for idx, row in df_exibicao.iterrows():
        with st.container(border=True):
            col_info, col_status = st.columns([3, 1])

            with col_info:
                # Como não temos o texto do título neste banco, identificamos pelo código/ID do tema de forma limpa
                id_tema_curto = str(row.get("tema_id", "N/A"))
                st.markdown(f"### 👥 Equipe — Código do Tema: `{id_tema_curto}`")

                # Exibe a Turma de forma destacada
                st.markdown(f"🏫 **Turma:** {row.get('turma', 'Não informada')}")

                # Renderiza e formata os membros da equipe
                membros_raw = row.get("nomes_membros", "")
                if membros_raw:
                    st.markdown("**Membros Integrantes:**")
                    membros = str(membros_raw).split(",")
                    for m in membros:
                        st.markdown(f"- {m.strip()}")
                else:
                    st.caption("*Nenhum nome de membro preenchido nesta inscrição.*")

            with col_status:
                # Adiciona um marcador visual verde indicando que o registro está ativo e confirmado neste banco
                st.success("🔒 CONFIRMADO")

                # Informação complementar se houver coluna de data de criação
                if "created_at" in row and pd.notna(row["created_at"]):
                    data_formatada = str(row["created_at"]).split("T")[0]
                    st.caption(f"Registrado em: {data_formatada}")