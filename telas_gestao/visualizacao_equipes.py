import streamlit as st
import pandas as pd


def mostrar_painel_organizacao(db_alunos, db_provas):
    st.title("📊 Painel de Monitoramento - Equipes")
    st.markdown("---")

    # Garante que os objetos de conexão passados pelo gestao_feira.py existem
    if db_alunos is None or db_provas is None:
        st.error(
            "🚨 Conexões de banco de dados não inicializadas no arquivo principal."
        )
        return

    # 1. Componentes de Filtro Visuais (Criados apenas uma vez)
    try:
        res_eventos = (
            db_alunos.table("feira_eventos")
            .select("id, nome")
            .eq("ativo", True)
            .execute()
        )
        if not res_eventos.data:
            st.warning("Não há eventos ativos no momento.")
            return
        eventos_dict = {ev["nome"]: ev["id"] for ev in res_eventos.data}
    except Exception as e_net:
        st.error("🚨 Erro de Rede/DNS ao alcançar o servidor do Supabase.")
        st.info(
            "Verifique se as chaves estão corretas nas Settings do Streamlit Cloud."
        )
        with st.expander("Detalhes do erro técnico"):
            st.code(str(e_net))
        return

    nome_evento = st.selectbox("Selecione o Evento:", options=list(eventos_dict.keys()))
    evento_id = eventos_dict[nome_evento]

    serie_selecionada = st.radio(
        "Filtrar por Série:", ["1º", "2º", "3º", "Geral"], horizontal=True
    )

    # 2. Coleta de Dados Brutos nos dois bancos isolados
    try:
        # Busca temas no Projeto Alunos (Banco 1)
        query_temas = (
            db_alunos.table("feira_temas").select("*").eq("evento_id", evento_id)
        )
        if serie_selecionada != "Geral":
            query_temas = query_temas.eq("Serie", serie_selecionada)
        res_temas = query_temas.execute()

        # Busca inscrições no Projeto Provas (Banco 2)
        res_inscricoes = (
            db_provas.table("feira_inscricoes")
            .select("*")
            .eq("evento_id", evento_id)
            .execute()
        )

    except Exception as e_busca:
        st.error(f"Erro ao consultar tabelas nos bancos: {e_busca}")
        return

    if not res_temas.data:
        st.info(
            f"Nenhum tema cadastrado para a série {serie_selecionada} neste evento."
        )
        return

    # 3. Integração em Memória com Pandas (O "Join" dos dois Bancos)
    df_temas = pd.DataFrame(res_temas.data)
    df_inscricoes = pd.DataFrame(res_inscricoes.data)

    if not df_inscricoes.empty:
        df_consolidado = pd.merge(
            df_temas,
            df_inscricoes,
            left_on="id",  # Coluna 'id' da imagem da tabela feira_temas
            right_on="tema_id",  # Coluna 'tema_id' da imagem da tabela feira_inscricoes
            how="left",
            suffixes=("_tema", "_insc"),
        )
    else:
        df_consolidado = df_temas.copy()
        df_consolidado["turma"] = None
        df_consolidado["nomes_membros"] = None
        df_consolidado["tema_id"] = None

    # 4. Painel de Indicadores
    total_temas = len(df_consolidado)
    vagas_ocupadas = (
        df_consolidado["tema_id"].notna().sum()
        if "tema_id" in df_consolidado.columns
        else 0
    )
    vagas_disponiveis = max(0, total_temas - vagas_ocupadas)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total de Temas", total_temas)
    m2.metric("Temas Ocupados", vagas_ocupadas)
    m3.metric("Temas Disponíveis", vagas_disponiveis)
    st.markdown("---")

    # 5. Apresentação dos Cards Traduzidos
    for _, row in df_consolidado.iterrows():
        with st.container(border=True):
            col_t, col_s = st.columns([3, 1])

            with col_t:
                # TRADUÇÃO CONCLUÍDA: Mostra o Nome Real do trabalho em vez do ID alfanumérico!
                st.markdown(f"### 📘 {row['titulo_trabalho']}")
                st.caption(
                    f"🧪 {row['disciplina']} | 👨‍🏫 Prof. {row.get('professor_nome', 'N/A')} | 📅 Série: {row['Serie']}"
                )

            with col_s:
                if "tema_id" in row and pd.notna(row["tema_id"]):
                    st.success("✅ INSCRITO")
                else:
                    st.warning("⚪ VAGO")

            # Se houver uma equipe casada a este tema, detalha o grupo
            if "tema_id" in row and pd.notna(row["tema_id"]):
                with st.expander("🔍 Ver Detalhes da Equipe"):
                    st.write(f"**Turma:** {row.get('turma', 'Não informada')}")
                    st.write("**Membros da Equipe:**")
                    membros_raw = row.get("nomes_membros", "")
                    if membros_raw:
                        membros = str(membros_raw).split(",")
                        for m in membros:
                            st.markdown(f"- {m.strip()}")