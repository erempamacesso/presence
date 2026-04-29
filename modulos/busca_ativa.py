import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
import calendar

# ==========================================
# 1. FUNÇÃO DE PADRONIZAÇÃO (A BASE DO FUNCIONAMENTO)
# ==========================================
def normalizar(nome):
    if not nome: return ""
    nfkd = unicodedata.normalize('NFKD', str(nome))
    nome_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()
    return " ".join(nome_limpo.split())

def exibir_busca_ativa(supabase, supabase_alunos):
    st.title("🕵️ Busca Ativa e Gestão de Frequência")

    tz = pytz.timezone('America/Recife')
    hoje = datetime.now(tz)
    
    try:
        # 1. CARREGA LISTA GERAL DE ALUNOS
        res_al = supabase_alunos.table("alunos").select("id, nome, turma").execute()
        if not res_al.data:
            st.error("Erro: Tabela de alunos não encontrada.")
            return
        
        df_al = pd.DataFrame(res_al.data)
        df_al['nome_limpo'] = df_al['nome'].apply(normalizar)

        # 2. FILTROS DE TOPO
        st.markdown("### 📅 Filtros de Pesquisa")
        c1, c2, c3 = st.columns([1, 1, 2])
        meses_br = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        with c1:
            mes_nome = st.selectbox("Mês", meses_br, index=hoje.month - 1)
            mes_num = meses_br.index(mes_nome) + 1
        with c2:
            ano_sel = st.selectbox("Ano", [2025, 2026], index=1)
        with c3:
            turmas_lista = sorted(df_al['turma'].dropna().unique().tolist())
            turma_sel = st.selectbox("Selecione a Turma:", turmas_lista)

        # --- BUSCA DE DADOS HISTÓRICOS (Para Presença Zero) ---
        res_p_historico = supabase.table("frequencia").select("aluno_nome").eq("status", "P").execute()
        nomes_com_presenca_historica = {normalizar(r['aluno_nome']) for r in res_p_historico.data} if res_p_historico.data else set()

        # --- BUSCA DE DADOS MENSAL (Para Diário e Ranking) ---
        ultimo_dia = calendar.monthrange(ano_sel, mes_num)[1]
        data_ini = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = f"{ano_sel}-{mes_num:02d}-{ultimo_dia}"

        res_mensal = supabase.table("frequencia")\
            .select("aluno_nome, data_chamada")\
            .eq("status", "P")\
            .eq("turma", turma_sel)\
            .filter("data_chamada", "gte", data_ini)\
            .filter("data_chamada", "lte", data_fim)\
            .execute()

        df_p_mes = pd.DataFrame(res_mensal.data) if res_mensal.data else pd.DataFrame()
        presencas_mes_set = set()
        if not df_p_mes.empty:
            df_p_mes['nome_limpo'] = df_p_mes['aluno_nome'].apply(normalizar)
            for _, row in df_p_mes.iterrows():
                dia = str(row['data_chamada']).split("-")[2]
                presencas_mes_set.add((row['nome_limpo'], dia))

        # --- DEFINIÇÃO DAS ABAS ---
        abas = st.tabs([
            "📊 Ranking de Faltas", 
            "❌ Presença Zero", 
            "🚩 Evasão Interna (Gazeando)", 
            "🚨 Ocorrências", 
            "📅 Diário de Frequência"
        ])
        
        df_t = df_al[df_al['turma'] == turma_sel].copy()

        # --- ABA 1: RANKING ---
        with abas[0]:
            st.subheader(f"Assiduidade Mensal: {turma_sel}")
            contagem = df_p_mes.groupby('nome_limpo').size().reset_index(name='presencas') if not df_p_mes.empty else pd.DataFrame(columns=['nome_limpo', 'presencas'])
            df_rank = pd.merge(df_t, contagem, on='nome_limpo', how='left').fillna(0)
            dias_letivos = df_p_mes['data_chamada'].nunique() if not df_p_mes.empty else 0
            df_rank['faltas'] = dias_letivos - df_rank['presencas']
            st.dataframe(df_rank[['nome', 'presencas', 'faltas']].sort_values('faltas', ascending=False), use_container_width=True, hide_index=True)

        # --- ABA 2: PRESENÇA ZERO (HISTÓRICO) ---
        with abas[1]:
            st.subheader("⚠️ Alunos que NUNCA registraram presença")
            df_presenca_zero = df_t[~df_t['nome_limpo'].isin(nomes_com_presenca_historica)]
            if not df_presenca_zero.empty:
                st.error(f"Detectamos {len(df_presenca_zero)} alunos na turma {turma_sel} sem histórico de presença 'P'.")
                st.dataframe(df_presenca_zero[['nome', 'turma']], use_container_width=True, hide_index=True)
            else:
                st.success("Todos os alunos desta turma já vieram pelo menos uma vez!")

        # --- ABA 3: EVASÃO INTERNA (VISUALIZAÇÃO E EXCLUSÃO) ---
       
        # --- ABA: EVASÃO INTERNA (VISUALIZAÇÃO FILTRADA E EXCLUSÃO) ---
        with abas[2]:
            st.subheader("🚩 Gestão de Evasões Internas (Gazeando)")
            
            # 1. SELETOR DE DATA PARA FILTRO (PADRÃO PT-BR)
            col_filtro, _ = st.columns([2, 2])
            with col_filtro:
                # O calendário ajudará a filtrar a coluna 'registro de dados'
                data_busca = st.date_input("Filtrar registros por dia:", hoje, format="DD/MM/YYYY")

            try:
                # BUSCA CORRIGIDA: Usando o nome exato da coluna 'registro de dados'
                # conforme visto na estrutura da sua tabela no Supabase
                res_ev = supabase.table("evasoes")\
                    .select("*")\
                    .eq("turma", turma_sel)\
                    .eq("registro de dados", data_busca.strftime('%Y-%m-%d'))\
                    .execute()
                
                df_ev_raw = pd.DataFrame(res_ev.data) if res_ev.data else pd.DataFrame()

                if not df_ev_raw.empty:
                    # Formatação brasileira para exibição das colunas existentes
                    # Usamos 'registro de dados' para a data e 'período_de_aula' para o horário/aula
                    df_ev_raw['Data'] = pd.to_datetime(df_ev_raw['registro de dados']).dt.strftime('%d/%m/%Y')
                    df_ev_raw['Estudante'] = df_ev_raw['aluno_nome']
                    df_ev_raw['Aula/Período'] = df_ev_raw['período_de_aula'] # Nome da coluna no seu print
                    df_ev_raw['Ação'] = "🗑️ Pendente"

                    st.info(f"Exibindo {len(df_ev_raw)} registro(s) para o dia {data_busca.strftime('%d/%m/%Y')}:")

                    # Tabela com altura dinâmica para mostrar todos os alunos de uma vez
                    st.data_editor(
                        df_ev_raw[['Data', 'Estudante', 'Aula/Período', 'Ação']],
                        use_container_width=True,
                        hide_index=True,
                        key="editor_ev_dia",
                        disabled=['Data', 'Estudante', 'Aula/Período', 'Ação'],
                        height=(len(df_ev_raw) + 1) * 38 
                    )

                    # 2. CENTRAL DE EXCLUSÃO
                    st.divider()
                    with st.expander(f"🗑️ Excluir registro de {data_busca.strftime('%d/%m/%Y')}"):
                        # Criamos as opções usando o UUID (coluna 'eu ia') para deletar com precisão
                        opcoes_del = {
                            f"{row['aluno_nome']} ({row['período_de_aula']})": row['eu ia'] 
                            for _, row in df_ev_raw.iterrows()
                        }
                        
                        alvo_del = st.selectbox(
                            "Selecione o registro para apagar:",
                            options=list(opcoes_del.keys()),
                            index=None,
                            placeholder="Escolha o estudante..."
                        )
                        
                        if alvo_del:
                            if st.button("Confirmar Exclusão Permanente", type="primary"):
                                id_para_deletar = opcoes_del[alvo_del]
                                # Deleta usando a coluna de ID correta: 'eu ia'
                                supabase.table("evasoes").delete().eq("eu ia", id_para_deletar).execute()
                                st.success("Registro removido com sucesso!")
                                st.rerun()
                else:
                    st.warning(f"Nenhum registro de evasão encontrado em {data_busca.strftime('%d/%m/%Y')}.")

            except Exception as e:
                st.error(f"Erro ao acessar base de evasões: {e}")

        # --- ABA 4: OCORRÊNCIAS ---
        with abas[3]:
            st.subheader("🚨 Ocorrências Disciplinares")
            nome_oc = st.selectbox("Estudante:", df_t['nome'].tolist(), key="sb_oc")
            with st.form("form_oc"):
                tipo = st.selectbox("Tipo:", ["Ligação", "Visita", "Conselho Tutelar"])
                relato = st.text_area("Relato:")
                resp_oc = st.text_input("Responsável:")
                if st.form_submit_button("💾 Salvar"):
                    if relato:
                        id_al = df_t[df_t['nome'] == nome_oc]['id'].values[0]
                        supabase.table("ocorrencias_disciplinares").insert({
                            "aluno_id": str(id_al), "aluno_nome": nome_oc, "turma": turma_sel,
                            "tipo_ocorrencia": tipo, "motivo": relato, "quem_registrou": resp_oc,
                            "data_registro": hoje.strftime('%Y-%m-%d')
                        }).execute()
                        st.success("Ocorrência salva!")

        # --- ABA 5: DIÁRIO ---
        with abas[4]:
            st.subheader(f"📅 Mapa Mensal: {turma_sel}")
            dias_lista = [f"{d:02d}" for d in range(1, ultimo_dia + 1)]
            matriz = []
            for _, aluno in df_t.sort_values('nome').iterrows():
                linha = {"Estudante": aluno['nome']}
                for d in dias_lista:
                    if (aluno['nome_limpo'], d) in presencas_mes_set:
                        linha[d] = "✅"
                    else:
                        dt_dia = datetime(ano_sel, mes_num, int(d)).date()
                        if dt_dia > hoje.date(): linha[d] = " "
                        elif dt_dia.weekday() >= 5: linha[d] = "-"
                        else: linha[d] = "❌"
                matriz.append(linha)
            
            df_mapa = pd.DataFrame(matriz)
            config_cols = {d: st.column_config.TextColumn(d, width=35) for d in dias_lista}
            config_cols["Estudante"] = st.column_config.TextColumn("Estudante", width=220, pinned=True)
            st.dataframe(df_mapa, use_container_width=True, hide_index=True, column_config=config_cols, height=500)

    except Exception as e:
        st.error(f"Erro: {e}")