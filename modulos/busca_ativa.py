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

# --- [NOVA] FUNÇÃO PARA CHECAR ARQUIVOS DE FOTO ---
def listar_nomes_com_foto(pasta="alunos_fotos"):
    if not os.path.exists(pasta):
        return set()
    # Pega os nomes dos arquivos, remove a extensão e normaliza
    arquivos = os.listdir(pasta)
    nomes_fotos = {normalizar(f.replace(".png", "").replace(".jpg", "").replace(".jpeg", "")) 
                   for f in arquivos if f.lower().endswith(('.png', '.jpg', '.jpeg'))}
    return nomes_fotos

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

        # --- [CORRIGIDO] BLOCO: ALUNOS PRESENTES SEM FOTO ---
        try:
            hoje_str = hoje.strftime('%Y-%m-%d')
            # Busca quem marcou presença hoje (Usando 'data_chamada' conforme seu print)
            res_pres_hoje = supabase.table("frequencia")\
                .select("aluno_nome")\
                .eq("data_chamada", hoje_str)\
                .eq("status", "P")\
                .execute()
            
            # Lê as fotos da pasta 'alunos_fotos' que você mostrou no GitHub
            nomes_com_foto = listar_nomes_com_foto("alunos_fotos")

            if res_pres_hoje.data:
                nomes_presentes_hoje = [normalizar(p['aluno_nome']) for p in res_pres_hoje.data]
                
                # Filtra alunos que estão presentes hoje mas o nome não está na pasta de fotos
                df_presentes = df_al[df_al['nome_limpo'].isin(nomes_presentes_hoje)]
                df_sem_foto = df_presentes[~df_presentes['nome_limpo'].isin(nomes_com_foto)]

                if not df_sem_foto.empty:
                    st.error(f"📸 **Atenção:** Identificamos **{len(df_sem_foto)}** alunos presentes hoje sem foto na pasta.")
                    with st.expander("📍 Lista para Fotografar Agora"):
                        for turma_ref, grupo in df_sem_foto.groupby('turma'):
                            st.markdown(f"**Turma: {turma_ref}**")
                            st.write(", ".join(grupo.sort_values('nome')['nome'].tolist()))
                else:
                    st.success("✅ Todos os alunos presentes hoje já possuem foto!")
        except Exception as e_foto:
            st.sidebar.warning(f"Aviso Fotos: {e_foto}")

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

        # 3. BUSCA DE DADOS MENSAL
        ultimo_dia = calendar.monthrange(ano_sel, mes_num)[1]
        data_ini = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = f"{ano_sel}-{mes_num:02d}-{ultimo_dia}"

        # Importante: Mantendo 'data_chamada' que é o nome real no seu banco
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

        # 4. INTERFACE EM ABAS
        abas = st.tabs(["📊 Ranking", "❌ Presença Zero", "🚩 Gazeando", "🚨 Ocorrências", "📅 Diário"])
        
        df_t = df_al[df_al['turma'] == turma_sel].copy()

        # --- ABA 1: RANKING ---
        with abas[0]:
            st.subheader(f"Faltas no Mês: {turma_sel}")
            contagem = df_p_mes.groupby('nome_limpo').size().reset_index(name='presencas') if not df_p_mes.empty else pd.DataFrame(columns=['nome_limpo', 'presencas'])
            df_rank = pd.merge(df_t, contagem, on='nome_limpo', how='left').fillna(0)
            dias_letivos = df_p_mes['data_chamada'].nunique() if not df_p_mes.empty else 0
            df_rank['faltas'] = dias_letivos - df_rank['presencas']
            st.dataframe(df_rank[['nome', 'presencas', 'faltas']].sort_values('faltas', ascending=False), use_container_width=True, hide_index=True)

        # --- ABA 5: DIÁRIO MENSAL (Célula de Ouro) ---
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
                        try:
                            dt_dia = datetime(ano_sel, mes_num, int(d)).date()
                            if dt_dia > hoje.date(): linha[d] = " "
                            elif dt_dia.weekday() >= 5: linha[d] = "-"
                            else: linha[d] = "❌"
                        except: linha[d] = " "
                matriz.append(linha)
            
            df_mapa = pd.DataFrame(matriz)
            config_cols = {d: st.column_config.TextColumn(d, width=35) for d in dias_lista}
            config_cols["Estudante"] = st.column_config.TextColumn("Estudante", width=220, pinned=True)
            st.dataframe(df_mapa, use_container_width=True, hide_index=True, column_config=config_cols, height=500)

    except Exception as e:
        st.error(f"Erro geral: {e}")