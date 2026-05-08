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

#---------------------------------------------------------------------------------------------------------
        
        # --- [NOVO] ALERTA DE FOTOS PENDENTES (VISÃO GERAL) ---
        from fotograma_aba import listar_fotos_github, limpar_texto

        mapa_fotos = listar_fotos_github()
        
        # Cruzamos a lista geral de alunos (df_al) com o que existe no GitHub
        df_al['tem_foto'] = df_al['nome'].apply(lambda x: limpar_texto(x) in mapa_fotos)
        df_sem_foto_geral = df_al[df_al['tem_foto'] == False]

        if not df_sem_foto_geral.empty:
            st.error(f"📸 Existem **{len(df_sem_foto_geral)}** estudantes sem foto no fotograma.")
            with st.expander("📂 Ver lista de pendências por turma", expanded=False):
                # Mostra o nome e a turma para facilitar a busca ativa do professor
                df_pendentes_view = df_sem_foto_geral[['nome', 'turma']].sort_values(by=['turma', 'nome'])
                st.dataframe(df_pendentes_view, use_container_width=True, hide_index=True)
        else:
            st.success("✅ 100% dos estudantes possuem foto no sistema!")
        
        st.divider() # Mantém a interface organizada

#----------------------------------------------------------------------------------------------------

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

     
       # --- ABA: EVASÃO INTERNA (VISUALIZAÇÃO E EXCLUSÃO) ---
        with abas[2]:
            st.subheader("🚩 Registros de Evasão Interna (Gazeando)")
            
            try:
                # Busca registros da tabela 'evasoes' filtrando pela turma selecionada
                res_ev = supabase.table("evasoes").select("*").eq("turma", turma_sel).order("data_registro", desc=True).execute()
                df_ev_raw = pd.DataFrame(res_ev.data) if res_ev.data else pd.DataFrame()

                if not df_ev_raw.empty:
                    # Formatação da data para o padrão brasileiro
                    df_ev_raw['Data'] = pd.to_datetime(df_ev_raw['data_registro']).dt.strftime('%d/%m/%Y')
                    
                    # Preparamos o DataFrame para exibição
                    df_display = df_ev_raw[['Data', 'aluno_nome', 'aula_periodo']].copy()
                    df_display.columns = ['Data', 'Estudante', 'Aula/Período']
                    
                    st.warning("⚠️ Para apagar um registro: Selecione a linha e aperte 'Delete' no teclado ou use a lixeira que aparecerá ao lado.")

                    # O editor de dados agora permite deletar linhas diretamente
                    # O 'num_rows="dynamic"' habilita a lixeira nativa do Streamlit
                    event = st.data_editor(
                        df_display,
                        use_container_width=True,
                        hide_index=True,
                        key="editor_evasoes",
                        disabled=['Data', 'Estudante', 'Aula/Período'], 
                        height=(len(df_display) + 1) * 36,
                        num_rows="dynamic" # ISSO ATIVA A LIXEIRA
                    )

                    # Lógica para detectar se o usuário apagou algo na tabela
                    if len(event) < len(df_display):
                        # Descobrimos qual item sumiu comparando os índices
                        indices_atuais = event.index.tolist()
                        indices_originais = df_display.index.tolist()
                        index_removido = list(set(indices_originais) - set(indices_atuais))[0]
                        
                        # Pegamos o ID real do banco para deletar
                        id_para_deletar = df_ev_raw.iloc[index_removido]['id']
                        
                        with st.spinner("Excluindo registro..."):
                            supabase.table("evasoes").delete().eq("id", id_para_deletar).execute()
                            st.success("Registro removido com sucesso!")
                            st.rerun()

                else:
                    st.info(f"Nenhum registro de evasão encontrado para a turma {turma_sel}.")

            except Exception as e:
                st.error(f"Erro ao carregar evasões: {e}")        

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