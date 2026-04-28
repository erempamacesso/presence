import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
import calendar
import traceback

# ==========================================
# 1. FUNÇÕES DE APOIO
# ==========================================
def limpar_texto(texto):
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

# ==========================================
# 2. TELA PRINCIPAL
# ==========================================
def exibir_busca_ativa(supabase, supabase_alunos):
    st.title("🕵️ Busca Ativa e Gestão de Frequência")

    # Configuração de fuso horário
    tz = pytz.timezone('America/Recife')
    hoje = datetime.now(tz)
    
    try:
        # --- CARREGAMENTO DOS ALUNOS ---
        res_al = supabase_alunos.table("alunos").select("id, nome, turma").execute()
        if not res_al.data:
            st.warning("Nenhum aluno encontrado.")
            return
        df_al = pd.DataFrame(res_al.data)

        # --- FILTRO DE DATA EM PORTUGUÊS ---
        st.markdown("### 📅 Período de Avaliação")
        col_ano, col_mes, _ = st.columns([1, 2, 2])
        
        anos_disponiveis = [hoje.year, hoje.year - 1]
        ano_sel = col_ano.selectbox("Ano", anos_disponiveis, index=0)
        
        meses_br = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]
        mes_nome_sel = col_mes.selectbox("Mês", meses_br, index=hoje.month - 1)
        mes_num_sel = meses_br.index(mes_nome_sel) + 1

        abas = st.tabs([
            "📊 Ranking de Faltas", 
            "⚠️ Risco de Abandono", 
            "🚨 Ocorrências",
            "📅 Diário de Frequência"
        ])

        # --- ABA 1: RANKING ---
        with abas[0]:
            st.subheader(f"Ranking de Faltas - {mes_nome_sel}")
            turma_sel = st.selectbox("Filtrar por Turma:", ["Todas"] + sorted(df_al['turma'].unique().tolist()), key="rank_t")
            
            # Busca frequencias do mês selecionado
            ultimo_dia = calendar.monthrange(ano_sel, mes_num_sel)[1]
            d_ini = f"{ano_sel}-{mes_num_sel:02d}-01"
            d_fim = f"{ano_sel}-{mes_num_sel:02d}-{ultimo_dia}"
            
            res_ch = supabase.table("frequencia").select("aluno_nome, data_chamada, status")\
                .filter("data_chamada", "gte", d_ini).filter("data_chamada", "lte", d_fim).execute()
            df_ch = pd.DataFrame(res_ch.data) if res_ch.data else pd.DataFrame()

            if not df_ch.empty:
                # Conta quem tem status 'P'
                presencas = df_ch[df_ch['status'] == 'P'].groupby('aluno_nome').size().reset_index(name='presencas')
                df_ranking = pd.merge(df_al, presencas, left_on='nome', right_on='aluno_nome', how='left').fillna(0)
                
                dias_letivos = df_ch['data_chamada'].nunique()
                df_ranking['faltas'] = dias_letivos - df_ranking['presencas']
                
                if turma_sel != "Todas":
                    df_ranking = df_ranking[df_ranking['turma'] == turma_sel]

                st.dataframe(df_ranking[['nome', 'turma', 'presencas', 'faltas']].sort_values('faltas', ascending=False), use_container_width=True, hide_index=True)

        # --- ABA 2: RISCO ---
        with abas[1]:
            if not df_ch.empty:
                presentes_mes = df_ch[df_ch['status'] == 'P']['aluno_nome'].unique().tolist()
                df_risco = df_al[~df_al['nome'].isin(presentes_mes)]
                st.error(f"Alunos sem NENHUMA presença ('P') em {mes_nome_sel}: {len(df_risco)}")
                st.table(df_risco[['nome', 'turma']])

        # --- ABA 3: OCORRÊNCIAS ---
        with abas[2]:
            st.subheader("Registrar Ocorrência")
            t_reg = st.selectbox("Turma:", sorted(df_al['turma'].unique()), key="reg_t")
            alunos_t = df_al[df_al['turma'] == t_reg]
            nome_sel = st.selectbox("Estudante:", alunos_t['nome'].tolist())
            
            with st.form("f_oc"):
                tipo = st.selectbox("Ação:", ["Ligação", "Advertência", "Visita", "Conselho Tutelar"])
                motivo = st.text_area("Relato:")
                if st.form_submit_button("Gravar"):
                    id_al = alunos_t[alunos_t['nome'] == nome_sel]['id'].values[0]
                    supabase.table("ocorrencias_disciplinares").insert({
                        "aluno_id": str(id_al), "aluno_nome": nome_sel, "turma": t_reg,
                        "tipo_ocorrencia": tipo, "motivo": motivo, "data_registro": hoje.strftime('%Y-%m-%d')
                    }).execute()
                    st.success("Registrado!")

        # --- ABA 4: DIÁRIO DE FREQUÊNCIA (CORREÇÃO P/F) ---
        with abas[3]:
            st.subheader(f"📅 Diário: {mes_nome_sel} / {ano_sel}")
            t_mapa = st.selectbox("Selecione a Turma:", sorted(df_al['turma'].unique()), key="mapa_t")
            
            ultimo_dia = calendar.monthrange(ano_sel, mes_num_sel)[1]
            dias_mes = [f"{d:02d}" for d in range(1, ultimo_dia + 1)]

            # Busca presenças do mês (já buscado acima, mas garantindo filtro de turma se quiser performance)
            # Reaproveitamos o df_ch para evitar múltiplas chamadas ao banco
            
            # Criamos um dicionário de status: {(nome, dia): 'P' ou 'F'}
            mapa_status = {}
            if not df_ch.empty:
                for _, r in df_ch.iterrows():
                    dia_r = str(r['data_chamada']).split("-")[2]
                    mapa_status[(r['aluno_nome'], dia_r)] = r['status']

            alunos_mapa = df_al[df_al['turma'] == t_mapa].sort_values('nome')
            
            if not alunos_mapa.empty:
                matriz = []
                for _, al in alunos_mapa.iterrows():
                    row = {"Estudante": al['nome']}
                    for d in dias_mes:
                        status_db = mapa_status.get((al['nome'], d))
                        
                        if status_db == 'P':
                            row[d] = "✅"
                        elif status_db == 'F':
                            row[d] = "❌"
                        else:
                            # Se não tem registro no banco, mas o dia já passou ou é hoje
                            dt_dia = datetime(ano_sel, mes_num_sel, int(d)).date()
                            if dt_dia <= hoje.date():
                                row[d] = "❌" # Considera falta se não foi registrado como 'P'
                            else:
                                row[d] = " " # Dia futuro
                    matriz.append(row)

                df_final_mapa = pd.DataFrame(matriz)
                
                # Configuração Visual
                conf = {d: st.column_config.TextColumn(d, width=35) for d in dias_mes}
                conf["Estudante"] = st.column_config.TextColumn("Estudante", width=250, pinned=True)

                st.dataframe(
                    df_final_mapa, 
                    use_container_width=True, 
                    hide_index=True, 
                    column_config=conf, 
                    height=550
                )
                st.caption("Legenda: ✅ (P) Presença | ❌ (F ou Sem Registro) Falta")
            else:
                st.info("Nenhum aluno nesta turma.")

    except Exception as e:
        st.error(f"Erro ao carregar Busca Ativa: {e}")
        # traceback.print_exc()