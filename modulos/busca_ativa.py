import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
import calendar
import os

# ==========================================
# 1. FUNÇÃO DE PADRONIZAÇÃO
# ==========================================
def normalizar(nome):
    if not nome: return ""
    nfkd = unicodedata.normalize('NFKD', str(nome))
    nome_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()
    return " ".join(nome_limpo.split())

# --- FUNÇÃO PARA CHECAR ARQUIVOS DE FOTO (CORRIGIDA PARA GITHUB/MODULOS) ---
def listar_nomes_com_foto():
    caminhos = ["alunos_fotos", "../alunos_fotos"]
    pasta_ativa = None
    for c in caminhos:
        if os.path.exists(c):
            pasta_ativa = c
            break
    if not pasta_ativa:
        return set()
    try:
        arquivos = os.listdir(pasta_ativa)
        nomes_fotos = {normalizar(os.path.splitext(f)[0]) 
                       for f in arquivos if f.lower().endswith(('.png', '.jpg', '.jpeg'))}
        return nomes_fotos
    except:
        return set()

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

        # --- ALERTA DE FOTOS ---
        try:
            hoje_str = hoje.strftime('%Y-%m-%d')
            res_pres_hoje = supabase.table("frequencia").select("aluno_nome").eq("data_chamada", hoje_str).eq("status", "P").execute()
            nomes_com_foto = listar_nomes_com_foto()

            if res_pres_hoje.data and nomes_com_foto:
                nomes_presentes_hoje = [normalizar(p['aluno_nome']) for p in res_pres_hoje.data]
                df_presentes = df_al[df_al['nome_limpo'].isin(nomes_presentes_hoje)]
                df_sem_foto = df_presentes[~df_presentes['nome_limpo'].isin(nomes_com_foto)]

                if not df_sem_foto.empty:
                    st.error(f"📸 **Atenção:** {len(df_sem_foto)} alunos presentes hoje sem foto na pasta.")
                    with st.expander("📍 Ver Lista para Fotografar"):
                        for t, g in df_sem_foto.groupby('turma'):
                            st.write(f"**{t}:** {', '.join(g.sort_values('nome')['nome'].tolist())}")
        except: pass

        # 2. FILTROS
        st.markdown("### 📅 Filtros de Pesquisa")
        c1, c2, c3 = st.columns([1, 1, 2])
        meses_br = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        with c1:
            mes_nome = st.selectbox("Mês", meses_br, index=hoje.month - 1)
            mes_num = meses_br.index(mes_nome) + 1
        with c2:
            ano_sel = st.selectbox("Ano", [2025, 2026], index=1)
        with c3:
            turma_sel = st.selectbox("Selecione a Turma:", sorted(df_al['turma'].dropna().unique().tolist()))

        # 3. BUSCA DE DADOS MENSAL
        ultimo_dia = calendar.monthrange(ano_sel, mes_num)[1]
        data_ini, data_fim = f"{ano_sel}-{mes_num:02d}-01", f"{ano_sel}-{mes_num:02d}-{ultimo_dia}"

        res_mensal = supabase.table("frequencia").select("aluno_nome, data_chamada").eq("status", "P").eq("turma", turma_sel).filter("data_chamada", "gte", data_ini).filter("data_chamada", "lte", data_fim).execute()

        df_p_mes = pd.DataFrame(res_mensal.data) if res_mensal.data else pd.DataFrame()
        presencas_mes_set = set()
        if not df_p_mes.empty:
            df_p_mes['nome_limpo'] = df_p_mes['aluno_nome'].apply(normalizar)
            for _, r in df_p_mes.iterrows():
                presencas_mes_set.add((r['nome_limpo'], str(r['data_chamada']).split("-")[2]))

        # 4. INTERFACE EM ABAS
        abas = st.tabs(["📊 Ranking", "❌ Presença Zero", "🚩 Gazeando", "🚨 Ocorrências", "📅 Diário"])
        df_t = df_al[df_al['turma'] == turma_sel].copy()

        # --- ABA 0: RANKING ---
        with abas[0]:
            st.subheader(f"Resumo de Faltas - {mes_nome}")
            contagem = df_p_mes.groupby('nome_limpo').size().reset_index(name='presencas') if not df_p_mes.empty else pd.DataFrame(columns=['nome_limpo', 'presencas'])
            df_rank = pd.merge(df_t, contagem, on='nome_limpo', how='left').fillna(0)
            dias_letivos = df_p_mes['data_chamada'].nunique() if not df_p_mes.empty else 0
            df_rank['faltas'] = dias_letivos - df_rank['presencas']
            st.dataframe(df_rank[['nome', 'presencas', 'faltas']].sort_values('faltas', ascending=False), use_container_width=True, hide_index=True)

        # --- ABA 1: PRESENÇA ZERO ---
        with abas[1]:
            st.subheader("🚫 Alunos que não compareceram no mês")
            nomes_com_presenca = df_p_mes['nome_limpo'].unique() if not df_p_mes.empty else []
            df_zero = df_t[~df_t['nome_limpo'].isin(nomes_com_presenca)]
            if not df_zero.empty:
                st.warning(f"Identificados {len(df_zero)} alunos com 0% de frequência.")
                st.dataframe(df_zero[['nome', 'turma']], use_container_width=True, hide_index=True)
            else:
                st.success("Nenhum aluno com presença zero este mês!")

        # --- ABA 2: GAZEANDO (Risco de Evasão) ---
        with abas[2]:
            st.subheader("🚩 Alerta de Frequência Crítica")
            if not df_p_mes.empty:
                # Alunos que faltaram mais de 50% dos dias que houve aula
                df_gaze = pd.merge(df_t, contagem, on='nome_limpo', how='left').fillna(0)
                df_gaze['pct'] = (df_gaze['presencas'] / dias_letivos) * 100
                df_critico = df_gaze[(df_gaze['presencas'] > 0) & (df_gaze['pct'] < 70)]
                if not df_critico.empty:
                    st.error("Alunos que frequentam raramente (Menos de 70% de presença)")
                    st.dataframe(df_critico[['nome', 'presencas', 'pct']].sort_values('pct'), use_container_width=True, hide_index=True)
                else:
                    st.success("Nenhum aluno em situação crítica de 'Gazeando'.")
            else: st.info("Dados insuficientes para calcular alertas.")

        # --- ABA 3: OCORRÊNCIAS ---
        with abas[3]:
            st.subheader("📝 Registrar Busca Ativa")
            with st.form("nova_oc"):
                aluno_oc = st.selectbox("Estudante:", df_t['nome'].tolist())
                tipo = st.selectbox("Tipo:", ["Falta Constante", "Abandono", "Saúde", "Visita Domiciliar", "Outros"])
                relato = st.text_area("Relato da Conversa/Situação:")
                if st.form_submit_button("Salvar Registro"):
                    try:
                        supabase.table("ocorrencias").insert({
                            "aluno_nome": aluno_oc, "tipo": tipo, "descricao": relato,
                            "data_registro": hoje.strftime('%Y-%m-%d'), "turma": turma_sel
                        }).execute()
                        st.success("Ocorrência registrada!")
                    except: st.error("Erro: Verifique se a tabela 'ocorrencias' existe no Supabase.")

        # --- ABA 4: DIÁRIO MENSAL ---
        with abas[4]:
            st.subheader(f"📅 Mapa: {turma_sel}")
            dias = [f"{d:02d}" for d in range(1, ultimo_dia + 1)]
            matriz = []
            for _, aluno in df_t.sort_values('nome').iterrows():
                linha = {"Estudante": aluno['nome']}
                for d in dias:
                    if (aluno['nome_limpo'], d) in presencas_mes_set: linha[d] = "✅"
                    else:
                        try:
                            dt = datetime(ano_sel, mes_num, int(d)).date()
                            if dt > hoje.date(): linha[d] = " "
                            elif dt.weekday() >= 5: linha[d] = "-"
                            else: linha[d] = "❌"
                        except: linha[d] = " "
                matriz.append(linha)
            st.dataframe(pd.DataFrame(matriz), use_container_width=True, hide_index=True, column_config={d: st.column_config.TextColumn(d, width=35) for d in dias})

    except Exception as e:
        st.error(f"Erro geral: {e}")