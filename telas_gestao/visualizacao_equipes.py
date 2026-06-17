import streamlit as st
import pandas as pd


def mostrar_painel_organizacao(db_alunos, db_provas):
    st.title("📊 Painel de Monitoramento - Equipes")
    st.markdown("---")

    if db_alunos is None or db_provas is None:
        st.error("🚨 Conexões de banco de dados não inicializadas.")
        return

    # 1. Busca dos Dados
    try:
        with st.spinner("Sincronizando dados dos bancos..."):
            # Selecionamos professor_nome e disciplina para usar nos filtros e cards
            res_temas = (
                db_alunos.table("feira_temas")
                .select("id, titulo_trabalho, professor_nome, disciplina")
                .execute()
            )
            res_inscricoes = db_provas.table("feira_inscricoes").select("*").execute()

            df_temas = pd.DataFrame(res_temas.data)
            df_inscricoes = pd.DataFrame(res_inscricoes.data)
    except Exception as e:
        st.error(f"Erro ao conectar com os bancos: {e}")
        return

    if df_inscricoes.empty:
        st.warning("Nenhuma inscrição encontrada.")
        return

    # 2. Integração
    df_consolidado = pd.merge(
        df_inscricoes, df_temas, left_on="tema_id", right_on="id", how="left"
    )

    # 3. Filtros (Turma e Professor)
    col_f1, col_f2 = st.columns(2)

    # Filtro de Turma
    turmas = sorted(df_consolidado["turma"].dropna().unique())
    turma_sel = col_f1.selectbox("Filtrar por Turma:", ["Todas"] + turmas)

    # Filtro de Professor (Multiselect para permitir selecionar vários)
    professores = sorted(df_consolidado["professor_nome"].dropna().unique())
    prof_sel = col_f2.multiselect("Filtrar por Professor(es):", professores)

    # Aplicando os filtros
    df_exibicao = df_consolidado.copy()

    if turma_sel != "Todas":
        df_exibicao = df_exibicao[df_exibicao["turma"] == turma_sel]

    if prof_sel:
        df_exibicao = df_exibicao[df_exibicao["professor_nome"].isin(prof_sel)]

    # 4. Exibição dos cards
    st.subheader(f"📋 Total de Equipes Filtradas: {len(df_exibicao)}")

    for _, row in df_exibicao.iterrows():
        titulo = row.get("titulo_trabalho", "Título não localizado")
        prof = row.get("professor_nome", "Não informado")
        disc = row.get("disciplina", "Não informada")

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### 📘 {titulo}")
                st.caption(f"👨‍🏫 **Orientador:** {prof} | 🧪 **Disciplina:** {disc}")
                st.markdown(f"🏫 **Turma:** {row.get('turma', 'N/A')}")

            with col2:
                st.success("✅ INSCRITO")

            # Recurso de Sanfona para os membros
            membros_raw = row.get("nomes_membros", "")
            with st.expander("👤 Ver Membros da Equipe"):
                if membros_raw:
                    membros = [m.strip() for m in str(membros_raw).split(",")]
                    for m in membros:
                        st.markdown(f"• {m}")
                else:
                    st.caption("Nenhum membro listado.")