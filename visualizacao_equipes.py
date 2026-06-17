import streamlit as st
import pandas as pd


def mostrar_painel_organizacao(db_alunos, db_provas):
    st.title("📊 Painel de Monitoramento - Equipes")
    st.markdown("---")

    # 1. Seleção do Evento
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
        nome_evento = st.selectbox(
            "Selecione o Evento:", options=list(eventos_dict.keys())
        )
        evento_id = eventos_dict[nome_evento]

        # 2. Seleção da Série
        serie_selecionada = st.radio(
            "Filtrar por Série:", ["1º", "2º", "3º", "Geral"], horizontal=True
        )

        # 3. Busca de Dados
        # Busca todos os temas do evento
        res_temas = (
            db_alunos.table("feira_temas")
            .select("*")
            .eq("evento_id", evento_id)
            .execute()
        )
        # Busca todas as inscrições do evento
        res_insc = (
            db_provas.table("feira_inscricoes")
            .select("*")
            .eq("evento_id", evento_id)
            .execute()
        )

        temas_df = pd.DataFrame(res_temas.data)
        inscricoes_df = pd.DataFrame(res_insc.data)

        if temas_df.empty:
            st.info("Nenhum tema cadastrado para este evento.")
            return

        # Filtrar temas pela série selecionada
        temas_filtrados = temas_df[
            temas_df["Serie"].str.contains(serie_selecionada, na=False)
        ]

        if serie_selecionada == "Geral":
            temas_filtrados = temas_df[temas_df["Serie"] == "Geral"]

        if temas_filtrados.empty:
            st.info(f"Nenhum tema cadastrado para a série {serie_selecionada}.")
            return

        # 4. Cruzamento de Dados (Visualização)
        st.subheader(f"Status dos Trabalhos - {serie_selecionada} Ano")

        metric_total = len(temas_filtrados)
        metric_inscritos = 0

        if not inscricoes_df.empty:
            metric_inscritos = (
                temas_filtrados["id"].isin(inscricoes_df["tema_id"]).sum()
            )

        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Temas", metric_total)
        c2.metric("Inscritos", metric_inscritos)
        c3.metric("Vagos", metric_total - metric_inscritos)

        st.markdown("---")

        # Listagem Detalhada
        for _, tema in temas_filtrados.sort_values(by="disciplina").iterrows():
            # Verifica se o tema tem inscrição
            inscricao = None
            if not inscricoes_df.empty:
                match = inscricoes_df[inscricoes_df["tema_id"] == tema["id"]]
                if not match.empty:
                    inscricao = match.iloc[0]

            with st.container(border=True):
                col_t, col_s = st.columns([3, 1])

                with col_t:
                    st.markdown(f"**{tema['titulo_trabalho']}**")
                    st.caption(
                        f"🧪 {tema['disciplina']} | 👨‍🏫 Prof. {tema.get('professor_nome', 'N/A')}"
                    )

                with col_s:
                    if inscricao is not None:
                        st.success("✅ INSCRITO")
                    else:
                        st.warning("⚪ VAGO")

                if inscricao is not None:
                    with st.expander("Ver Detalhes da Equipe"):
                        st.write(f"**Turma:** {inscricao['turma']}")
                        st.write(f"**Membros:**")
                        membros = inscricao["nomes_membros"].split(",")
                        for m in membros:
                            st.markdown(f"- {m.strip()}")
                        st.caption(f"Data da Inscrição: {inscricao['data_inscricao']}")

    except Exception as e:
        st.error(f"Erro ao carregar dados de gestão: {e}")


if __name__ == "__main__":
    # Apenas para teste local, na integração use os bancos reais
    pass
