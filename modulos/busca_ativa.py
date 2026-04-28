import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
import calendar

# ==========================================
# 1. FUNÇÃO DE PADRONIZAÇÃO (EVITA ERROS DE NOME)
# ==========================================
def normalizar(nome):
    if not nome: return ""
    nfkd = unicodedata.normalize('NFKD', str(nome))
    nome_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()
    return " ".join(nome_limpo.split())

# ==========================================
# 2. TELA PRINCIPAL
# ==========================================
def exibir_busca_ativa(supabase, supabase_alunos):
    st.title("🕵️ Busca Ativa e Gestão de Frequência")

    tz = pytz.timezone('America/Recife')
    hoje = datetime.now(tz)
    
    try:
        # 1. CARREGA LISTA GERAL DE ALUNOS (Tabela: alunos)
        res_al = supabase_alunos.table("alunos").select("id, nome, turma").execute()
        if not res_al.data:
            st.error("Erro: Tabela de alunos não encontrada.")
            return
        
        df_al = pd.DataFrame(res_al.data)
        df_al['nome_limpo'] = df_al['nome'].apply(normalizar)

        # 2. SELEÇÃO DE PERÍODO E TURMA
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

        # --- BUSCA DE DADOS (APENAS STATUS 'P' NA TABELA FREQUENCIA) ---
        ultimo_dia = calendar.monthrange(ano_sel, mes_num)[1]
        data_ini = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = f"{ano_sel}-{mes_num:02d}-{ultimo_dia}"

        # Consulta otimizada para evitar limites de linhas
        res_f = supabase.table("frequencia")\
            .select("aluno_nome, data_chamada")\
            .eq("status", "P")\
            .eq("turma", turma_sel)\
            .filter("data_chamada", "gte", data_ini)\
            .filter("data_chamada", "lte", data_fim)\
            .limit(5000).execute()

        df_p = pd.DataFrame(res_f.data) if res_f.data else pd.DataFrame()
        
        # Mapeamento rápido de presenças confirmadas
        presencas_confirmadas = set()
        if not df_p.empty:
            df_p['nome_limpo'] = df_p['aluno_nome'].apply(normalizar)
            for _, row in df_p.iterrows():
                # Extrai o dia da string de data (YYYY-MM-DD)
                dia = str(row['data_chamada']).split("-")[2]
                presencas_confirmadas.add((row['nome_limpo'], dia))

        # --- DEFINIÇÃO DAS 4 ABAS RESTAURADAS ---
        abas = st.tabs([
            "📊 Ranking de Faltas", 
            "⚠️ Risco de Abandono", 
            "🚨 Ocorrências",
            "📅 Diário de Frequência"
        ])

        # Filtragem dos alunos da turma selecionada
        df_t = df_al[df_al['turma'] == turma_sel].copy()

        # --- ABA 1: RANKING ---
        with abas[0]:
            st.subheader(f"Assiduidade: Turma {turma_sel}")
            contagem = df_p.groupby('nome_limpo').size().reset_index(name='presencas') if not df_p.empty else pd.DataFrame(columns=['nome_limpo', 'presencas'])
            df_rank = pd.merge(df_t, contagem, on='nome_limpo', how='left').fillna(0)
            
            # Dias letivos são baseados nas datas únicas com presença 'P' na turma
            dias_com_p = df_p['data_chamada'].nunique() if not df_p.empty else 0
            df_rank['faltas'] = dias_com_p - df_rank['presencas']
            
            st.dataframe(df_rank[['nome', 'presencas', 'faltas']].sort_values('faltas', ascending=False), use_container_width=True, hide_index=True)

        # --- ABA 2: RISCO DE ABANDONO ---
        with abas[1]:
            st.subheader("⚠️ Alunos sem nenhuma presença no mês")
            nomes_com_p = df_p['nome_limpo'].unique() if not df_p.empty else []
            df_risco = df_t[~df_t['nome_limpo'].isin(nomes_com_p)]
            
            if not df_risco.empty:
                st.error(f"Existem {len(df_risco)} alunos sem registro de 'P' nesta turma.")
                st.table(df_risco[['nome']])
            else:
                st.success("Todos os alunos possuem ao menos uma presença registrada.")

        # --- ABA 3: OCORRÊNCIAS (FORMULÁRIO COMPLETO) ---
        with abas[2]:
            st.subheader("🚨 Registrar Ação de Busca Ativa")
            nome_oc = st.selectbox("Estudante:", df_t['nome'].tolist(), key="sb_oc")
            
            with st.form("form_ocorrencia"):
                col_tipo, col_data = st.columns(2)
                tipo = col_tipo.selectbox("Tipo de Ação:", ["Ligação Telefônica", "Visita Domiciliar", "Advertência", "Conselho Tutelar"])
                data_oc = col_data.date_input("Data:", hoje)
                relato = st.text_area("Relato da Situação:")
                responsavel = st.text_input("Responsável pelo Registro:")
                
                if st.form_submit_button("✅ Salvar no Banco"):
                    if relato and responsavel:
                        id_aluno = df_t[df_t['nome'] == nome_oc]['id'].values[0]
                        supabase.table("ocorrencias_disciplinares").insert({
                            "aluno_id": str(id_aluno), "aluno_nome": nome_oc,
                            "turma": turma_sel, "tipo_ocorrencia": tipo,
                            "motivo": relato, "quem_registrou": responsavel,
                            "data_registro": data_oc.strftime('%Y-%m-%d')
                        }).execute()
                        st.success("Ocorrência gravada com sucesso!")
                    else:
                        st.warning("Preencha o relato e o responsável.")

        # --- ABA 4: DIÁRIO DE FREQUÊNCIA (MAPA VISUAL) ---
        with abas[3]:
            st.subheader(f"📅 Diário: {mes_nome} / {ano_sel}")
            dias_lista = [f"{d:02d}" for d in range(1, ultimo_dia + 1)]
            
            matriz = []
            for _, aluno in df_t.sort_values('nome').iterrows():
                linha = {"Estudante": aluno['nome']}
                for d in dias_lista:
                    if (aluno['nome_limpo'], d) in presencas_confirmadas:
                        linha[d] = "✅"
                    else:
                        dt_dia = datetime(ano_sel, mes_num, int(d)).date()
                        if dt_dia > hoje.date(): linha[d] = " "
                        elif dt_dia.weekday() >= 5: linha[d] = "-"
                        else: linha[d] = "❌"
                matriz.append(linha)

            df_mapa = pd.DataFrame(matriz)
            
            # Configuração corrigida para evitar erro de variável não definida
            config_cols = {d: st.column_config.TextColumn(d, width=35) for d in dias_lista}
            config_cols["Estudante"] = st.column_config.TextColumn("Estudante", width=220, pinned=True)

            st.dataframe(df_mapa, use_container_width=True, hide_index=True, column_config=config_cols, height=500)
            st.caption("✅ Presença | ❌ Falta | - Fim de Semana")

    except Exception as e:
        st.error(f"Erro Geral: {e}")