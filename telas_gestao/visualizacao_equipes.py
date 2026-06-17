import streamlit as st
import pandas as pd
import os


def mostrar_painel_organizacao(db_alunos, db_provas):
    st.title("📊 Painel de Monitoramento - Equipes")
    st.markdown("---")

    # Garante que temos as conexões antes de prosseguir
    if db_alunos is None or db_provas is None:
        st.error(
            "🚨 As conexões com os bancos de dados não foram inicializadas corretamente no arquivo principal."
        )
        return

    try:
        # 1. Busca e seleção do Evento (Projeto Alunos)
        try:
            res_eventos = (
                db_alunos.table("feira_eventos")
                .select("id, nome")
                .eq("ativo", True)
                .execute()
            )
        except Exception as e_dns:
            st.error(
                "🚨 Erro de comunicação com o banco de dados (Verifique sua conexão de rede/DNS)"
            )
            with st.expander("Ver detalhes técnicos do erro"):
                st.code(str(e_dns))
            st.stop()

        if not res_eventos.data:
            st.warning("Não há eventos ativos no momento.")
            return

        eventos_dict = {ev["nome"]: ev["id"] for ev in res_eventos.data}
        nome_evento = st.selectbox(
            "Selecione o Evento:", options=list(eventos_dict.keys())
        )
        evento_id = eventos_dict[nome_evento]

        # 2. Seleção de Filtro por Série
        serie_selecionada = st.radio(
            "Filtrar por Série:", ["1º", "2º", "3º", "Geral"], horizontal=True
        )

        # 3. Busca de Dados em Ambos os Bancos
        # Busca os temas cadastrados no Projeto Alunos
        query_temas = (
            db_alunos.table("feira_temas").select("*").eq("evento_id", evento_id)
        )
        if serie_selecionada != "Geral":
            query_temas = query_temas.eq("Serie", serie_selecionada)

        res_temas = query_temas.execute()

        # Busca as inscrições feitas no Projeto Provas
        res_inscricoes = (
            db_provas.table("feira_inscricoes")
            .select("*")
            .eq("evento_id", evento_id)
            .execute()
        )

        if not res_temas.data:
            st.info(
                f"Nenhum tema cadastrado para a série {serie_selecionada} neste evento."
            )
            return

        # 4. Criação dos DataFrames para Integração em Memória
        df_temas = pd.DataFrame(res_temas.data)
        df_inscricoes = pd.DataFrame(res_inscricoes.data)

        # 5. O Cruzamento de Dados (Merge): Associa o ID do tema ao Nome Real do Trabalho
        if not df_inscricoes.empty:
            df_consolidado = pd.merge(
                df_temas,
                df_inscricoes,
                left_on="id",  # UUID da tabela feira_temas
                right_on="tema_id",  # Coluna correspondente na feira_inscricoes
                how="left",
                suffixes=("_tema", "_insc"),
            )
        else:
            # Caso não existam inscrições ainda, estruturamos colunas vazias preventivas
            df_consolidado = df_temas.copy()
            df_consolidado["turma"] = None
            df_consolidado["nomes_membros"] = None
            df_consolidado["tema_id"] = None

        # 6. Métricas do Painel Superior
        total_temas = len(df_consolidado)
        vagas_ocupadas = (
            df_consolidado["tema_id"].notna().sum()
            if "tema_id" in df_consolidado.columns
            else 0
        )
        vagas_disponiveis = max(0, total_temas - vagas_ocupadas)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total de Temas", total_temas)
        m2.metric("Temas Ocupados (Inscritos)", vagas_ocupadas)
        m3.metric("Temas Disponíveis (Vagos)", vagas_disponiveis)
        st.markdown("---")

        # 7. Renderização Visual Inteligente
        for _, row in df_consolidado.iterrows():
            with st.container(border=True):
                col_t, col_s = st.columns([3, 1])

                with col_t:
                    # Aqui passamos a exibir o Nome Real do trabalho em vez do Hash ID!
                    st.markdown(f"### 📘 {row['titulo_trabalho']}")
                    st.caption(
                        f"🧪 {row['disciplina']} | 👨‍🏫 Prof. {row.get('professor_nome', 'N/A')} | 📅 Série: {row['Serie']}"
                    )
                    if pd.notna(row.get("descricao")) and row["descricao"]:
                        st.markdown(f"*{row['descricao']}*")

                with col_s:
                    # Verifica se o tema possui par inscrito
                    if "tema_id" in row and pd.notna(row["tema_id"]):
                        st.success("✅ INSCRITO")
                    else:
                        st.warning("⚪ VAGO")

                # Se houver dados de inscrição atrelados a este tema, mostramos os detalhes expandidos
                if "tema_id" in row and pd.notna(row["tema_id"]):
                    with st.expander("🔍 Ver Detalhes da Equipe"):
                        st.write(f"**Turma:** {row.get('turma', 'Não informada')}")
                        st.write("**Membros da Equipe:**")

                        membros_raw = row.get("nomes_membros", "")
                        if membros_raw:
                            membros = str(membros_raw).split(",")
                            for m in membros:
                                st.markdown(f"- {m.strip()}")
                        else:
                            st.write("*Nenhum nome listado.*")

    except Exception as e_geral:
        st.error(f"Erro ao processar e integrar painel: {e_geral}")