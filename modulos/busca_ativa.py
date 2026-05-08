import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
import calendar

# ==========================================
# CONFIGURAÇÃO DE NOMES DO BANCO (AJUSTE AQUI)
# ==========================================
TABELA_FREQUENCIA = "frequencia"
COLUNA_DATA = "data"    # <-- SE DER ERRO DE NOVO, TENTE MUDAR PARA 'created_at' OU O NOME CERTO LÁ
TABELA_FOTOS = "fotos_alunos"
COLUNA_FOTO_ID = "aluno_id"

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
        df_al = pd.DataFrame(res_al.data)
        df_al['nome_limpo'] = df_al['nome'].apply(normalizar)

        # --- BLOCO: ALUNOS PRESENTES SEM FOTO ---
        try:
            hoje_str = hoje.strftime('%Y-%m-%d')
            # Busca presença de hoje
            res_pres_hoje = supabase.table(TABELA_FREQUENCIA)\
                .select("aluno_nome")\
                .eq(COLUNA_DATA, hoje_str)\
                .execute()
            
            # Busca IDs com foto
            res_fotos = supabase_alunos.table(TABELA_FOTOS).select(COLUNA_FOTO_ID).execute()
            ids_com_foto = set(str(f[COLUNA_FOTO_ID]) for f in res_fotos.data) if res_fotos.data else set()

            if res_pres_hoje.data:
                nomes_presentes = set(normalizar(p['aluno_nome']) for p in res_pres_hoje.data)
                mask_presente = df_al['nome_limpo'].isin(nomes_presentes)
                mask_sem_foto = ~df_al['id'].astype(str).isin(ids_com_foto)
                df_alerta_fotos = df_al[mask_presente & mask_sem_foto]

                if not df_alerta_fotos.empty:
                    st.error(f"📸 **Atenção:** {len(df_alerta_fotos)} alunos presentes hoje sem foto!")
                    with st.expander("📍 Ver lista para fotografar"):
                        for turma_ref, grupo in df_alerta_fotos.groupby('turma'):
                            st.write(f"**{turma_ref}:** {', '.join(grupo['nome'].tolist())}")
        except Exception:
            st.info(f"💡 Info: A tabela '{TABELA_FOTOS}' ou a coluna de data não foi encontrada. Verifique o banco.")

        # 2. FILTROS
        st.markdown("### 📅 Filtros")
        c1, c2, c3 = st.columns(3)
        with c1:
            mes_nome = st.selectbox("Mês", list(calendar.month_name)[1:], index=hoje.month-1)
            mes_num = list(calendar.month_name).index(mes_nome)
        with c2:
            ano_sel = st.number_input("Ano", value=hoje.year)
        with c3:
            turma_sel = st.selectbox("Turma", ["TODAS"] + sorted(df_al['turma'].unique()))

        # 3. BUSCA FREQUÊNCIA MENSAL
        ultimo_dia = calendar.monthrange(ano_sel, mes_num)[1]
        data_inicio = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = f"{ano_sel}-{mes_num:02d}-{ultimo_dia}"

        # ATENÇÃO: Se o erro persistir, o nome da coluna no .filter() deve ser igual ao do banco
        res_f = supabase.table(TABELA_FREQUENCIA)\
            .select(f"aluno_nome, {COLUNA_DATA}")\
            .filter(COLUNA_DATA, "gte", data_inicio)\
            .filter(COLUNA_DATA, "lte", data_fim)\
            .execute()
        
        presencas_mes_set = set()
        if res_f.data:
            for p in res_f.data:
                # Ajuste para pegar a data independente do formato (ISO ou simples)
                data_valor = str(p[COLUNA_DATA])
                d_str = data_valor.split('T')[0].split('-')[2] 
                presencas_mes_set.add((normalizar(p['aluno_nome']), d_str))

        # 4. ABAS
        abas = st.tabs(["📊 Dash", "🚨 Alertas", "📝 Ocorrência", "📂 Histórico", "📅 Diário"])

        with abas[4]: # Diário Mensal
            df_t = df_al if turma_sel == "TODAS" else df_al[df_al['turma'] == turma_sel]
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
            
            st.dataframe(pd.DataFrame(matriz), hide_index=True)

    except Exception as e:
        st.error(f"Erro Crítico: {e}")
        st.info("Dica: Verifique se o nome da coluna de data na tabela 'frequencia' é realmente 'data'.")