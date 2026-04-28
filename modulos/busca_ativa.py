import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
import calendar

# ==========================================
# 1. FUNÇÕES DE APOIO
# ==========================================
def normalizar_nome(nome):
    """Remove espaços extras e padroniza para maiúsculas para comparação segura"""
    if not nome: return ""
    return str(nome).strip().upper()

# ==========================================
# 2. TELA PRINCIPAL
# ==========================================
def exibir_busca_ativa(supabase, supabase_alunos):
    st.title("🕵️ Busca Ativa e Gestão de Frequência")

    tz = pytz.timezone('America/Recife')
    hoje = datetime.now(tz)
    
    try:
        # --- CARREGAMENTO DOS ALUNOS ---
        res_al = supabase_alunos.table("alunos").select("id, nome, turma").execute()
        if not res_al.data:
            st.warning("Nenhum aluno encontrado.")
            return
        df_al = pd.DataFrame(res_al.data)

        # Filtro de Data em Português
        st.markdown("### 📅 Período de Avaliação")
        col_ano, col_mes, _ = st.columns([1, 2, 2])
        ano_sel = col_ano.selectbox("Ano", [hoje.year, hoje.year - 1], index=0)
        meses_br = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_nome_sel = col_mes.selectbox("Mês", meses_br, index=hoje.month - 1)
        mes_num_sel = meses_br.index(mes_nome_sel) + 1

        abas = st.tabs(["📊 Ranking de Faltas", "⚠️ Risco de Abandono", "🚨 Ocorrências", "📅 Diário de Frequência"])

        # --- BUSCA DE DADOS DE FREQUÊNCIA (UMA ÚNICA VEZ PARA TODAS AS ABAS) ---
        ultimo_dia = calendar.monthrange(ano_sel, mes_num_sel)[1]
        d_ini = f"{ano_sel}-{mes_num_sel:02d}-01"
        d_fim = f"{ano_sel}-{mes_num_sel:02d}-{ultimo_dia}"
        
        res_frequencia = supabase.table("frequencia").select("aluno_nome, data_chamada, status")\
            .filter("data_chamada", "gte", d_ini).filter("data_chamada", "lte", d_fim).execute()
        df_frequencia = pd.DataFrame(res_frequencia.data) if res_frequencia.data else pd.DataFrame()

        # --- ABA 1: RANKING ---
        with abas[0]:
            st.subheader(f"Assiduidade - {mes_nome_sel}")
            if not df_frequencia.empty:
                # Normalizamos os nomes para contagem correta
                df_frequencia['nome_limpo'] = df_frequencia['aluno_nome'].apply(normalizar_nome)
                df_al['nome_limpo'] = df_al['nome'].apply(normalizar_nome)
                
                presencas = df_frequencia[df_frequencia['status'] == 'P'].groupby('nome_limpo').size().reset_index(name='presencas')
                df_ranking = pd.merge(df_al, presencas, on='nome_limpo', how='left').fillna(0)
                
                dias_uteis = df_frequencia['data_chamada'].nunique()
                df_ranking['faltas'] = dias_uteis - df_ranking['presencas']
                
                turma_sel = st.selectbox("Turma:", ["Todas"] + sorted(df_al['turma'].unique().tolist()))
                if turma_sel != "Todas":
                    df_ranking = df_ranking[df_ranking['turma'] == turma_sel]

                st.dataframe(df_ranking[['nome', 'turma', 'presencas', 'faltas']].sort_values('faltas', ascending=False), use_container_width=True, hide_index=True)

        # --- ABA 2: RISCO ---
        with abas[1]:
            if not df_frequencia.empty:
                nomes_com_p = df_frequencia[df_frequencia['status'] == 'P']['nome_limpo'].unique()
                df_risco = df_al[~df_al['nome_limpo'].isin(nomes_com_p)]
                st.error(f"Alunos sem nenhuma presença ('P') neste mês: {len(df_risco)}")
                st.table(df_risco[['nome', 'turma']])

        # --- ABA 3: OCORRÊNCIAS (Mantida) ---
        with abas[2]:
            st.info("Espaço para registro de ações da Busca Ativa.")

        # --- ABA 4: DIÁRIO DE FREQUÊNCIA (O SEU PEDIDO) ---
        with abas[3]:
            st.subheader(f"📅 Mapa: {mes_nome_sel} / {ano_sel}")
            t_mapa = st.selectbox("Turma para o Mapa:", sorted(df_al['turma'].unique()), key="mapa_t")
            
            dias_mes = [f"{d:02d}" for d in range(1, ultimo_dia + 1)]

            # Criamos um mapeamento seguro {(NOME_LIMPO, DIA): STATUS}
            mapa_status = {}
            if not df_frequencia.empty:
                for _, r in df_frequencia.iterrows():
                    nome_key = normalizar_nome(r['aluno_nome'])
                    dia_key = str(r['data_chamada']).split("-")[2]
                    mapa_status[(nome_key, dia_key)] = r['status']

            alunos_mapa = df_al[df_al['turma'] == t_mapa].sort_values('nome')
            
            if not alunos_mapa.empty:
                matriz = []
                for _, al in alunos_mapa.iterrows():
                    row = {"Estudante": al['nome']}
                    nome_aluno_limpo = normalizar_nome(al['nome'])
                    
                    for d in dias_mes:
                        status_db = mapa_status.get((nome_aluno_limpo, d))
                        
                        if status_db == 'P':
                            row[d] = "✅"
                        elif status_db == 'F':
                            row[d] = "❌"
                        else:
                            # Se não achou registro, checa se o dia já passou
                            dt_dia = datetime(ano_sel, mes_num_sel, int(d)).date()
                            row[d] = "❌" if dt_dia <= hoje.date() else " "
                    matriz.append(row)

                df_final_mapa = pd.DataFrame(matriz)
                
                # Configuração de exibição compacta
                conf = {d: st.column_config.TextColumn(d, width=35) for d in dias_mes}
                conf["Estudante"] = st.column_config.TextColumn("Estudante", width=250, pinned=True)

                st.dataframe(df_final_mapa, use_container_width=True, hide_index=True, column_config=conf, height=550)
                st.caption("✅ (P) Presente | ❌ (F ou Sem Registro) Falta")

    except Exception as e:
        st.error(f"Erro ao carregar Busca Ativa: {e}")