import streamlit as st
import pandas as pd


def mostrar_painel_organizacao(db_alunos, db_provas):
    print(f"URL ALUNOS: {os.getenv('SUPABASE_URL_ALUNOS')}")
    st.title("📊 Painel de Monitoramento - Equipes")
    st.markdown("---")

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
            st.error("🚨 Erro de conexão com o Banco de Alunos (DNS)")
            st.info(f"Detalhe técnico: {e_dns}")
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

        # 3. Busca de Dados nos dois bancos distintos
        # Busca os temas no projeto Chamada/Escola (db_alunos)
        query_temas = (
            db_alunos.table("feira_temas").select("*").eq("evento_id", evento_id)
        )
        if serie_selecionada != "Geral":
            query_temas = query_temas.eq("Serie", serie_selecionada)

        res_temas = query_temas.execute()

        # Busca as inscrições no projeto Avaliador-Provas (db_provas)
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

        # 4. Criação dos DataFrames para fazer a junção (Merge) em memória
        df_temas = pd.DataFrame(res_temas.data)
        df_inscricoes = pd.DataFrame(res_inscricoes.data)

        # 5. O "Pulo do Gato": Integrar as tabelas pelo ID do Tema
        # Fazemos um Left Join para garantir que todos os temas apareçam (mesmo os sem inscrição)
        if not df_inscricoes.empty:
            df_consolidado = pd.merge(
                df_temas,
                df_inscricoes,
                left_on="id",  # Coluna ID da tabela feira_temas (Escola)
                right_on="tema_id",  # Coluna tema_id da tabela feira_inscricoes (Provas)
                how="left",
                suffixes=("_tema", "_insc"),
            )
        else:
            # Se não houver nenhuma inscrição no banco, criamos as colunas vazias para evitar erros no loop
            df_consolidado = df_temas.copy()
            df_consolidado["turma"] = None
            df_consolidado["nomes_membros"] = None
            df_consolidado["data_inscricao"] = None

        # 6. Métricas do Painel
        total_temas = len(df_consolidado)
        vagas_ocupadas = df_consolidado["tema_id"].notna().sum()
        vagas_disponiveis = total_temas - vagas_ocupadas

        m1, m2, m3 = st.columns(3)
        m1.metric("Total de Temas", total_temas)
        m2.metric("Temas Ocupados", vagas_ocupadas)
        m3.metric("Temas Disponíveis", vagas_disponiveis)
        st.markdown("---")

        # 7. Renderização Visual dos Cartões de Temas
        for _, row in df_consolidado.iterrows():
            with st.container(border=True):
                col_t, col_s = st.columns([3, 1])

                with col_t:
                    # Exibe o Nome Real do Tema (titulo_trabalho) em vez do UUID hash!
                    st.markdown(f"### 📘 {row['titulo_trabalho']}")
                    st.caption(
                        f"🧪 {row['disciplina']} | 👨‍🏫 Prof. {row.get('professor_nome', 'N/A')} | 📅 Série: {row['Serie']}"
                    )
                    if pd.notna(row.get("descricao")):
                        st.write(f"*{row['descricao']}*")

                with col_s:
                    # Se houver correspondência de ID, o tema está ocupado
                    if pd.notna(row["tema_id"]):
                        st.success("✅ INSCRITO")
                    else:
                        st.warning("⚪ VAGO")

                # Se o tema possuir uma equipe vinculada, mostra os detalhes traduzidos
                if pd.notna(row["tema_id"]):
                    with st.expander("🔍 Ver Detalhes da Equipe"):
                        st.write(f"**Turma:** {row['turma']}")
                        st.write("**Membros da Equipe:**")

                        # Separa e lista os nomes dos alunos que vieram da tabela de inscrições
                        membros = str(row["nomes_membros"]).split(",")
                        for m in membros:
                            st.markdown(f"- {m.strip()}")

                        if pd.notna(row.get("data_inscricao")):
                            st.caption(f"Data da Inscrição: {row['data_inscricao']}")

    except Exception as e:
        st.error(f"Erro ao carregar dados de gestão: {e}")
