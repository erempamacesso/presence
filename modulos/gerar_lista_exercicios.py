import streamlit as st
import pandas as pd
import time


def exibir_gerador_listas(supabase):
    st.title("🏋️ Criar Lista de Exercícios de Treino")
    st.caption(
        "As listas criadas aqui servem para treino livre e não geram notas no boletim."
    )

    with st.form("form_lista_exercicios"):
        titulo = st.text_input("Título da Lista (Ex: Treino de Termoquímica - 2º Ano)")

        # Busca questões disponíveis
        res_q = (
            supabase.table("questoes").select("id, enunciado, assunto, serie").execute()
        )
        if not res_q.data:
            st.warning(
                "Nenhuma questão encontrada na biblioteca. Cadastre questões primeiro."
            )
            st.stop()

        df_q = pd.DataFrame(res_q.data)

        col1, col2 = st.columns(2)
        filtro_serie = col1.multiselect(
            "Filtrar por Série:", options=df_q["serie"].unique()
        )
        filtro_assunto = col2.multiselect(
            "Filtrar por Assunto:", options=df_q["assunto"].unique()
        )

        # Aplica filtros dinâmicos
        df_filtrado = df_q.copy()
        if filtro_serie:
            df_filtrado = df_filtrado[df_filtrado["serie"].isin(filtro_serie)]
        if filtro_assunto:
            df_filtrado = df_filtrado[df_filtrado["assunto"].isin(filtro_assunto)]

        st.write(f"Questões encontradas: {len(df_filtrado)}")

        # Seleção de questões simplificada
        import re

        def limpar_tag(t):
            return re.sub("<[^>]+>", "", str(t))[:60] + "..."

        df_filtrado["exibicao"] = df_filtrado.apply(
            lambda r: f"[{r['serie']}] {limpar_tag(r['enunciado'])} (ID:{r['id']})",
            axis=1,
        )

        selecionadas = st.multiselect(
            "Selecione as questões para a lista:",
            options=df_filtrado["id"].tolist(),
            format_func=lambda x: df_filtrado[df_filtrado["id"] == x][
                "exibicao"
            ].values[0],
        )

        publicar_agora = st.toggle("Ativar lista imediatamente?", value=True)

        btn_salvar = st.form_submit_button(
            "💾 Salvar Lista de Treino", type="primary", use_container_width=True
        )

        if btn_salvar:
            if not titulo or not selecionadas:
                st.error("Preencha o título e selecione pelo menos uma questão.")
            else:
                dados_lista = {
                    "titulo": titulo.strip(),
                    "questoes_ids": selecionadas,
                    "ativa": publicar_agora,
                }

                try:
                    supabase.table("listas_exercicios").insert(dados_lista).execute()
                    st.success("✅ Lista de Exercícios criada com sucesso!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar no Supabase: {e}")

    st.divider()
    st.subheader("📋 Listas Existentes")
    res_listas = (
        supabase.table("listas_exercicios").select("*").order("id", desc=True).execute()
    )
    if res_listas.data:
        df_listas = pd.DataFrame(res_listas.data)
        st.dataframe(
            df_listas[["titulo", "ativa"]],
            use_container_width=True,
            hide_index=True,
            column_config={"ativa": st.column_config.CheckboxColumn("Ativa?")},
        )
