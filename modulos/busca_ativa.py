import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
import calendar

# ==========================================
# 1. FUNÇÃO DE PADRONIZAÇÃO DE NOMES
# ==========================================
def normalizar(nome):
    if not nome: return ""
    # Remove acentos e deixa em maiúsculo
    nfkd = unicodedata.normalize('NFKD', str(nome))
    nome_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()
    # Remove espaços extras no início, fim e entre nomes
    return " ".join(nome_limpo.split())

# ==========================================
# 2. TELA PRINCIPAL
# ==========================================
def exibir_busca_ativa(supabase, supabase_alunos):
    st.title("🕵️ Busca Ativa - Foco em Presenças (P)")

    tz = pytz.timezone('America/Recife')
    hoje = datetime.now(tz)
    
    try:
        # 1. PEGAR LISTA DE ALUNOS
        res_al = supabase_alunos.table("alunos").select("id, nome, turma").execute()
        if not res_al.data:
            st.error("Erro: Tabela de alunos vazia.")
            return
        
        df_al = pd.DataFrame(res_al.data)
        df_al['nome_limpo'] = df_al['nome'].apply(normalizar)

        # 2. FILTROS DE DATA (PORTUGUÊS)
        st.markdown("### 📅 Seleção do Período")
        col1, col2 = st.columns(2)
        meses_br = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        with col1:
            mes_nome = st.selectbox("Mês", meses_br, index=hoje.month - 1)
            mes_num = meses_br.index(mes_nome) + 1
        with col2:
            ano_sel = st.selectbox("Ano", [hoje.year, hoje.year - 1], index=0)

        # 3. FILTRO DE TURMA (Fundamental para a nova tática)
        turmas_lista = sorted(df_al['turma'].unique().tolist())
        turma_sel = st.selectbox("Selecione a Turma para Analisar:", turmas_lista)

        # --- BUSCA NO BANCO DE DADOS (APENAS O QUE É 'P') ---
        ultimo_dia = calendar.monthrange(ano_sel, mes_num)[1]
        data_inicio = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = f"{ano_sel}-{mes_num:02d}-{ultimo_dia}"

        # TÁTICA: Filtrar por turma e status 'P' direto na consulta para não perder dados
        res_frequencia = supabase.table("frequencia")\
            .select("aluno_nome, data_chamada")\
            .eq("status", "P")\
            .eq("turma", turma_sel)\
            .filter("data_chamada", "gte", data_inicio)\
            .filter("data_chamada", "lte", data_fim)\
            .limit(5000)\
            .execute()

        df_p = pd.DataFrame(res_frequencia.data) if res_frequencia.data else pd.DataFrame()
        
        # Mapear presenças confirmadas num Set para busca ultra rápida
        presencas_set = set()
        if not df_p.empty:
            df_p['nome_limpo'] = df_p['aluno_nome'].apply(normalizar)
            for _, row in df_p.iterrows():
                dia = str(row['data_chamada']).split("-")[2]
                presencas_set.add((row['nome_limpo'], dia))

        # 4. MONTAGEM DAS ABAS
        abas = st.tabs(["📊 Ranking", "📅 Diário de Classe", "🚨 Ocorrências"])

        # --- ABA RANKING ---
        with abas[0]:
            st.subheader(f"Total de Presenças - {mes_nome}")
            df_turma = df_al[df_al['turma'] == turma_sel].copy()
            
            # Contar presenças de cada um
            contagem = df_p.groupby('nome_limpo').size().reset_index(name='qtd_p') if not df_p.empty else pd.DataFrame(columns=['nome_limpo', 'qtd_p'])
            df_ranking = pd.merge(df_turma, contagem, on='nome_limpo', how='left').fillna(0)
            
            # Dias letivos registrados (quantas datas diferentes têm 'P' na turma)
            dias_com_aula = df_p['data_chamada'].nunique() if not df_p.empty else 0
            df_ranking['faltas'] = dias_com_aula - df_ranking['qtd_p']
            
            st.dataframe(df_ranking[['nome', 'qtd_p', 'faltas']].sort_values('nome'), use_container_width=True, hide_index=True)

        # --- ABA DIÁRIO (MAPA VISUAL) ---
        with abas[1]:
            st.subheader(f"Mapa de Presenças: {turma_sel}")
            dias_lista = [f"{d:02d}" for d in range(1, ultimo_dia + 1)]
            
            matriz = []
            for _, aluno in df_turma.sort_values('nome').iterrows():
                linha = {"Estudante": aluno['nome']}
                for d in dias_lista:
                    # Se o par (NOME, DIA) está no set de presenças 'P'
                    if (aluno['nome_limpo'], d) in presencas_set:
                        linha[d] = "✅"
                    else:
                        # Verifica se é fim de semana ou dia futuro
                        dt_atual = datetime(ano_sel, mes_num, int(d)).date()
                        if dt_atual > hoje.date():
                            linha[d] = " "
                        elif dt_atual.weekday() >= 5:
                            linha[d] = "-"
                        else:
                            linha[d] = "❌" # Se não é 'P' e já passou, é falta
                matriz.append(linha)

            df_mapa = pd.DataFrame(matriz)
            
            # Configuração das colunas
            config = {d: st.column_config.TextColumn(d, width=35) for d in dias_lista}
            config["Estudante"] = st.column_config.TextColumn("Estudante", width=220, pinned=True)

            st.dataframe(df_mapa, use_container_width=True, hide_index=True, column_config=config, height=500)
            st.caption("✅ = Presença (P) encontrada no banco | ❌ = Sem registro de presença")

        # --- ABA OCORRÊNCIAS ---
        with abas[2]:
            st.info("Utilize esta aba para registrar contatos com os alunos que possuem muitos ❌.")
            # (Aqui você pode manter o formulário de gravação que já tínhamos)

    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")