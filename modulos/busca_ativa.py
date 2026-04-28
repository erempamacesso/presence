import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
from urllib.parse import quote
from fpdf import FPDF 
import traceback
import calendar  # Novo import necessário

# ==========================================
# 1. FUNÇÕES DE APOIO
# ==========================================
def limpar_texto(texto):
    """Padronização idêntica ao Fotograma para bater com as fotos do GitHub"""
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

@st.cache_data(ttl=3600)
def carregar_fotos_github_busca_ativa():
    try:
        import github
        from github import Github, Auth
        
        if "GITHUB_TOKEN" not in st.secrets:
            return {}
            
        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        repo = g.get_repo("erempamacesso/presence")
        contents = repo.get_contents("alunos_fotos")
        
        return {limpar_texto(arq.name): arq.download_url for arq in contents}
    except Exception:
        return {}

# ==========================================
# 2. TELA PRINCIPAL
# ==========================================
def mostrar_tela_busca_ativa(supabase, supabase_alunos):
    st.title("🕵️ Busca Ativa e Gestão de Frequência")

    # Configuração de fuso horário
    tz = pytz.timezone('America/Recife')
    hoje = datetime.now(tz)
    hoje_str = hoje.strftime('%Y-%m-%d')

    try:
        # --- CARREGAMENTO DE DADOS ---
        res_al = supabase_alunos.table("alunos").select("id, nome, turma, status").eq("status", "Ativo").execute()
        df_al = pd.DataFrame(res_al.data) if res_al.data else pd.DataFrame()

        # Filtro de Data Global
        col_data, col_vazia = st.columns([1, 2])
        with col_data:
            data_escolhida = st.date_input("📅 Selecione a Data de Referência:", hoje)
            data_ref_str = data_escolhida.strftime('%Y-%m-%d')

        # --- ABAS ---
        # Adicionada a aba "Diário de Frequência"
        abas = st.tabs([
            "📊 Ranking de Faltas", 
            "⚠️ Risco de Abandono (0%)", 
            "🚨 Ocorrências Disciplinares",
            "📅 Diário de Frequência"
        ])

        # --- ABA 1: RANKING DE FALTAS ---
        with abas[0]:
            st.subheader("Filtrar por Turma")
            turma_sel = st.selectbox("Selecione a Turma:", ["Todas"] + sorted(df_al['turma'].unique().tolist()))
            
            # Busca todas as chamadas até hoje
            res_ch = supabase.table("chamada").select("aluno_id, data_presenca").execute()
            df_ch = pd.DataFrame(res_ch.data) if res_ch.data else pd.DataFrame()

            if not df_ch.empty and not df_al.empty:
                # Contagem de presenças por aluno
                contagem = df_ch.groupby('aluno_id').size().reset_index(name='presencas')
                df_ranking = pd.merge(df_al, contagem, left_on='id', right_on='aluno_id', how='left').fillna(0)
                
                # Cálculo de faltas aproximadas (Baseado em dias letivos únicos na tabela chamada)
                dias_letivos = df_ch['data_presenca'].nunique()
                df_ranking['faltas'] = dias_letivos - df_ranking['presencas']
                
                if turma_sel != "Todas":
                    df_ranking = df_ranking[df_ranking['turma'] == turma_sel]

                st.dataframe(
                    df_ranking[['nome', 'turma', 'presencas', 'faltas']].sort_values('faltas', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )

        # --- ABA 2: RISCO DE ABANDONO ---
        with abas[1]:
            st.warning("Alunos que ainda não registraram NENHUMA presença no sistema.")
            alunos_com_presenca = df_ch['aluno_id'].unique().tolist()
            df_risco = df_al[~df_al['id'].astype(str).isin([str(x) for x in alunos_com_presenca])]
            st.write(f"Total de Alunos em Risco: {len(df_risco)}")
            st.table(df_risco[['nome', 'turma']])

        # --- ABA 3: OCORRÊNCIAS ---
        with abas[2]:
            st.subheader("Registrar Nova Ação")
            t_escolhida_reg = st.selectbox("Turma do Estudante:", sorted(df_al['turma'].dropna().unique()), key="reg_turma")
            al_da_t = df_al[df_al['turma'] == t_escolhida_reg]
            al_dict = dict(zip(al_da_t['nome'], al_da_t['id']))
            n_escolhido = st.selectbox("Selecione o Estudante:", list(al_dict.keys()), key="reg_aluno")

            with st.form("form_oc"):
                t_ac = st.selectbox("Ação:", ["Ligação para Família", "Advertência", "Suspensão", "Visita Domiciliar", "Conselho Tutelar"])
                mot = st.text_area("Motivo:")
                mat = st.text_input("Sua Matrícula:")
                if st.form_submit_button("🚨 Gravar", type="primary"):
                    if mot and mat:
                        supabase.table("ocorrencias_disciplinares").insert({
                            "aluno_id": al_dict[n_escolhido], "aluno_nome": n_escolhido,
                            "turma": t_escolhida_reg, "tipo_ocorrencia": t_ac,
                            "motivo": mot, "quem_registrou": mat, "status": "Ativa",
                            "data_registro": hoje_str
                        }).execute()
                        st.success("Gravado com Sucesso!")
                    else: st.error("Preencha todos os campos.")

        # --- ABA 4: DIÁRIO DE FREQUÊNCIA MENSAL (NOVA FUNCIONALIDADE) ---
        with abas[3]:
            st.subheader("📅 Mapa de Frequência Mensal")
            
            # Filtros locais
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                turmas_mapa = sorted(df_al['turma'].dropna().unique())
                turma_mapa = st.selectbox("Selecione a Turma para o Mapa:", turmas_mapa, key="mapa_turma")
            
            with col_f2:
                # Usa o mês da data selecionada no topo
                mes_ref = data_escolhida.month
                ano_ref = data_escolhida.year
                nome_mes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][mes_ref - 1]
                st.info(f"Visualizando: **{nome_mes} / {ano_ref}**")

            # Cálculo de dias do mês
            ultimo_dia = calendar.monthrange(ano_ref, mes_ref)[1]
            dias_mes = [f"{d:02d}" for d in range(1, ultimo_dia + 1)]

            # Busca presenças do mês inteiro (Uma única query para performance)
            data_ini = f"{ano_ref}-{mes_ref:02d}-01"
            data_fim = f"{ano_ref}-{mes_ref:02d}-{ultimo_dia}"
            
            res_m = supabase.table("chamada").select("aluno_id, data_presenca")\
                .filter("data_presenca", "gte", data_ini)\
                .filter("data_presenca", "lte", data_fim).execute()

            # Mapeamento rápido de presenças {(aluno_id, dia): True}
            p_map = set()
            if res_m.data:
                for r in res_m.data:
                    dia_r = r['data_presenca'].split("-")[2]
                    p_map.add((str(r['aluno_id']), dia_r))

            # Montagem da Matriz de Dados
            alunos_t = df_al[df_al['turma'] == turma_mapa].sort_values('nome')
            
            if not alunos_t.empty:
                matriz_frequencia = []
                for _, al_row in alunos_t.iterrows():
                    linha = {"Estudante": al_row['nome']}
                    for d in dias_mes:
                        if (str(al_row['id']), d) in p_map:
                            linha[d] = "✅"
                        else:
                            # Só marca falta (X) se o dia já passou ou é hoje
                            data_col = datetime(ano_ref, mes_ref, int(d)).date()
                            if data_col <= hoje.date():
                                linha[d] = "❌"
                            else:
                                linha[d] = " " # Futuro fica vazio
                    matriz_frequencia.append(linha)

                df_final_mapa = pd.DataFrame(matriz_frequencia)

                # Configuração de Colunas para evitar barra lateral
                # Cada coluna de dia fica bem pequena (35px)
                conf_cols = {d: st.column_config.TextColumn(d, width=35) for d in dias_mes}
                conf_cols["Estudante"] = st.column_config.TextColumn("Estudante", width=250, pinned=True)

                st.dataframe(
                    df_final_mapa,
                    use_container_width=True,
                    hide_index=True,
                    column_config=conf_cols,
                    height=500
                )
                st.caption("✅ Presença | ❌ Falta ou Sem Registro | Coluna Fixa: Estudante")
            else:
                st.warning("Selecione uma turma para carregar o mapa.")

    except Exception as e:
        st.error(f"Erro ao carregar Busca Ativa: {e}")
        # traceback.print_exc() # Útil para debug no terminal