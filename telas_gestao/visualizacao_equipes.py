import streamlit as st
import pandas as pd


def mostrar_painel_organizacao(db_alunos, db_provas):
    st.title("📊 Painel de Monitoramento - Equipes")
    st.markdown("---")

    if db_alunos is None or db_provas is None:
        st.error("🚨 Conexões de banco de dados não inicializadas.")
        return

    # 1. Busca dos Dados nos dois bancos
    try:
        with st.spinner("Sincronizando dados dos bancos..."):
            # Busca temas (para ter o título do trabalho)
            res_temas = (
                db_alunos.table("feira_temas").select("id, titulo_trabalho").execute()
            )
            # Busca inscrições (para ter os membros e turma)
            res_inscricoes = db_provas.table("feira_inscricoes").select("*").execute()

            df_temas = pd.DataFrame(res_temas.data)
            df_inscricoes = pd.DataFrame(res_inscricoes.data)
    except Exception as e:
        st.error(f"Erro ao conectar com os bancos: {e}")
        return

    if df_inscricoes.empty:
        st.warning("Nenhuma inscrição encontrada.")
        return

    # 2. Integração (Transformar ID em Nome)
    # Fazemos um merge: para cada inscrição, buscamos o título do tema correspondente
    df_consolidado = pd.merge(
        df_inscricoes, df_temas, left_on="tema_id", right_on="id", how="left"
    )

    # 3. Filtro de Turma
    turmas = sorted(df_consolidado["turma"].dropna().unique())
    turma_selecionada = st.selectbox("Filtrar por Turma:", ["Todas"] + turmas)

    if turma_selecionada != "Todas":
        df_exibicao = df_consolidado[df_consolidado["turma"] == turma_selecionada]
    else:
        df_exibicao = df_consolidado

    # 4. Exibição dos cards
    st.subheader(f"📋 Total de Equipes: {len(df_exibicao)}")

    for _, row in df_exibicao.iterrows():
        # Trata o título (pega do banco de temas ou avisa se não achar)
        titulo = row.get("titulo_trabalho", "Título não localizado")

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### 📘 {titulo}")
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