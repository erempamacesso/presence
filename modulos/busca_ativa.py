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

@st.cache_data(ttl=3600)
def carregar_fotos_github_busca_ativa():
    try:
        from github import Github, Auth
        if "GITHUB_TOKEN" not in st.secrets: return {}
        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        repo = g.get_repo("erempamacesso/presence")
        contents = repo.get_contents("alunos_fotos")
        return {limpar_texto(arq.name): arq.download_url for arq in contents}
    except: return {}

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

        # Filtro de Data Global
        col_data, _ = st.columns([1, 2])
        with col_data:
            data_escolhida = st.date_input("📅 Selecione o Mês de Referência:", hoje)

        abas = st.tabs([
            "📊 Ranking de Faltas", 
            "⚠️ Risco de Abandono", 
            "🚨 Ocorrências",
            "📅 Diário de Frequência"
        ])

        # --- ABA 1: RANKING ---
        with abas[0]:
            st.subheader("Alunos com Mais Faltas")
            turma_sel = st.selectbox("Filtrar por Turma:", ["Todas"] + sorted(df_al['turma'].unique().tolist()))
            
            # CORREÇÃO: Tabela 'frequencia' e coluna 'data_chamada'
            res_ch = supabase.table("frequencia").select("aluno_nome, data_chamada, status").execute()
            df_ch = pd.DataFrame(res_ch.data) if res_ch.data else pd.DataFrame()

            if not df_ch.empty:
                # Filtramos apenas quem tem status 'PRESENTE' (ou ajuste conforme seu padrão)
                presencas = df_ch[df_ch['status'].str.upper().str.contains('PRESENTE', na=False)]
                contagem = presencas.groupby('aluno_nome').size().reset_index(name='presencas')
                
                df_ranking = pd.merge(df_al, contagem, left_on='nome', right_on='aluno_nome', how='left').fillna(0)
                dias_letivos = df_ch['data_chamada'].nunique()
                df_ranking['faltas'] = dias_letivos - df_ranking['presencas']
                
                if turma_sel != "Todas":
                    df_ranking = df_ranking[df_ranking['turma'] == turma_sel]

                st.dataframe(df_ranking[['nome', 'turma', 'presencas', 'faltas']].sort_values('faltas', ascending=False), use_container_width=True, hide_index=True)

        # --- ABA 2: RISCO ---
        with abas[1]:
            if not df_ch.empty:
                alunos_com_p = df_ch['aluno_nome'].unique().tolist()
                df_risco = df_al[~df_al['nome'].isin(alunos_com_p)]
                st.error(f"Total: {len(df_risco)} alunos sem registros no sistema.")
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
                    st.success("Salvo!")

        # --- ABA 4: DIÁRIO DE FREQUÊNCIA ---
        with abas[3]:
            st.subheader("📅 Mapa Mensal de Presença")
            t_mapa = st.selectbox("Turma:", sorted(df_al['turma'].unique()), key="mapa_t")
            
            mes, ano = data_escolhida.month, data_escolhida.year
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            dias_mes = [f"{d:02d}" for d in range(1, ultimo_dia + 1)]

            # Busca presenças do mês na tabela 'frequencia'
            d_ini, d_fim = f"{ano}-{mes:02d}-01", f"{ano}-{mes:02d}-{ultimo_dia}"
            res_m = supabase.table("frequencia").select("aluno_nome, data_chamada, status")\
                .filter("data_chamada", "gte", d_ini).filter("data_chamada", "lte", d_fim).execute()

            # Mapeamento rápido {(nome, dia): True}
            p_set = set()
            if res_m.data:
                for r in res_m.data:
                    if 'PRESENTE' in str(r['status']).upper():
                        dia_r = str(r['data_chamada']).split("-")[2]
                        p_set.add((r['aluno_nome'], dia_r))

            alunos_mapa = df_al[df_al['turma'] == t_mapa].sort_values('nome')
            if not alunos_mapa.empty:
                matriz = []
                for _, al in alunos_mapa.iterrows():
                    row = {"Estudante": al['nome']}
                    for d in dias_mes:
                        if (al['nome'], d) in p_set:
                            row[d] = "✅"
                        else:
                            dt = datetime(ano, mes, int(d)).date()
                            row[d] = "❌" if dt <= hoje.date() else " "
                    matriz.append(row)

                df_m = pd.DataFrame(matriz)
                conf = {d: st.column_config.TextColumn(d, width=35) for d in dias_mes}
                conf["Estudante"] = st.column_config.TextColumn("Estudante", width=220, pinned=True)

                st.dataframe(df_m, use_container_width=True, hide_index=True, column_config=conf, height=500)
                st.caption("✅ Presente | ❌ Falta/Sem Registro")

    except Exception as e:
        st.error(f"Erro ao carregar Busca Ativa: {e}")