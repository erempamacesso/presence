import streamlit as st
import pandas as pd

def obter_dados_teste():
    """Gera dados fictícios simulando o Supabase para testes locais sem internet/DNS"""
    temas_fakes = [
        {"id": "ee09dbeb-af9f-4b37-9bf1-b603d6a6144a", "evento_id": "1", "titulo_trabalho": "Robótica Sustentável com Arduino", "professor_nome": "Fábio Souza", "disciplina": "Física", "Serie": "1º", "descricao": "Protótipos usando lixo eletrônico."},
        {"id": "aa123456-bb88-9999-0000-abcdefcccccc", "evento_id": "1", "titulo_trabalho": "Análise da Água do Rio Local", "professor_nome": "Maria Silva", "disciplina": "Química", "Serie": "2º", "descricao": "Coleta e verificação de pH."},
        {"id": "cc987654-dd11-2222-3333-xyzxyzxyzxyz", "evento_id": "1", "titulo_trabalho": "Desenvolvimento de Jogos Educativos", "professor_nome": "José Santos", "disciplina": "Matemática", "Serie": "3º", "descricao": "Criação de jogos lógicos no Scratch."}
    ]
    inscricoes_fakes = [
        {"tema_id": "ee09dbeb-af9f-4b37-9bf1-b603d6a6144a", "evento_id": "1", "turma": "1º Ano A", "nomes_membros": "José Silva, Lucas Almeida, Mariana Costa"}
    ]
    return temas_fakes, inscricoes_fakes

def mostrar_painel_organizacao(db_alunos, db_provas):
    st.title("📊 Painel de Monitoramento - Equipes")
    st.markdown("---")

    eventos_dict = {}
    usando_dados_teste = False

    # 1. Tenta carregar a lista de eventos do banco real
    try:
        res_eventos = db_alunos.table("feira_eventos").select("id, nome").eq("ativo", True).execute()
        if res_eventos.data:
            eventos_dict = {ev["nome"]: ev["id"] for ev in res_eventos.data}
    except Exception:
        # Se falhar o DNS/Rede aqui, ativa o fallback de teste
        usando_dados_teste = True

    # Se o banco falhou ou retornou vazio, preenche com os dados de demonstração
    if usando_dados_teste or not eventos_dict:
        usando_dados_teste = True
        st.info("💡 Conexão com o Supabase indisponível (Erro de DNS/Rede). Ativando Modo de Demonstração Local.")
        eventos_dict = {"NATUMAT 2026 (Demonstração)": "1"}

    # Componentes visuais desenhados APENAS UMA VEZ (Evita o StreamlitDuplicateElementId)
    nome_evento = st.selectbox("Selecione o Evento:", options=list(eventos_dict.keys()))
    evento_id = eventos_dict[nome_evento]
    
    serie_selecionada = st.radio("Filtrar por Série:", ["1º", "2º", "3º", "Geral"], horizontal=True)

    temas_data = []
    inscricoes_data = []

    # 2. Coleta dos dados dependendo do modo (Real ou Demonstração)
    if not usando_dados_teste:
        try:
            query_temas = db_alunos.table("feira_temas").select("*").eq("evento_id", evento_id)
            if serie_selecionada != "Geral":
                query_temas = query_temas.eq("Serie", serie_selecionada)
            temas_data = query_temas.execute().data

            inscricoes_data = db_provas.table("feira_inscricoes").select("*").eq("evento_id", evento_id).execute().data
        except Exception as e_dados:
            st.error(f"Erro ao buscar os dados do evento: {e_dados}")
            return
    else:
        # Carrega os dados simulados
        f_temas, f_insc = obter_dados_teste()
        if serie_selecionada != "Geral":
            temas_data = [t for t in f_temas if t["Serie"] == serie_selecionada]
        else:
            temas_data = f_temas
        inscricoes_data = f_insc

    # 3. Validação e Renderização
    if not temas_data:
        st.info(f"Nenhum tema disponível para exibição nesta categoria.")
        return

    df_temas = pd.DataFrame(temas_data)
    df_inscricoes = pd.DataFrame(inscricoes_data)

    # Executa o cruzamento (Merge em memória)
    if not df_inscricoes.empty:
        df_consolidado = pd.merge(
            df_temas,
            df_inscricoes,
            left_on="id",       
            right_on="tema_id", 
            how="left",
            suffixes=("_tema", "_insc")
        )
    else:
        df_consolidado = df_temas.copy()
        df_consolidado["turma"] = None
        df_consolidado["nomes_membros"] = None
        df_consolidado["tema_id"] = None

    # Painel de Métricas do topo
    total_temas = len(df_consolidado)
    vagas_ocupadas = df_consolidado["tema_id"].notna().sum() if "tema_id" in df_consolidado.columns else 0
    vagas_disponiveis = max(0, total_temas - vagas_ocupadas)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total de Temas", total_temas)
    m2.metric("Temas Ocupados", vagas_ocupadas)
    m3.metric("Temas Disponíveis", vagas_disponiveis)
    st.markdown("---")

    # Renderização dos cartões visuais com a tradução correta
    for _, row in df_consolidado.iterrows():
        with st.container(border=True):
            col_t, col_s = st.columns([3, 1])

            with col_t:
                st.markdown(f"### 📘 {row['titulo_trabalho']}")
                st.caption(f"🧪 {row['disciplina']} | 👨‍🏫 Prof. {row.get('professor_nome', 'N/A')} | 📅 Série: {row['Serie']}")
                if pd.notna(row.get('descricao')) and row['descricao']:
                    st.markdown(f"*{row['descricao']}*")

            with col_s:
                if "tema_id" in row and pd.notna(row["tema_id"]):
                    st.success("✅ INSCRITO")
                else:
                    st.warning("⚪ VAGO")

            if "tema_id" in row and pd.notna(row["tema_id"]):
                with st.expander("🔍 Ver Detalhes da Equipe"):
                    st.write(f"**Turma:** {row.get('turma', 'Não informada')}")
                    st.write("**Membros da Equipe:**")
                    membros_raw = row.get("nomes_membros", "")
                    if membros_raw:
                        membros = str(membros_raw).split(",")
                        for m in membros:
                            st.markdown(f"- {m.strip()}")