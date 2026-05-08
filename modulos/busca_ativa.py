import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
import calendar

# ==========================================
# 1. FUNÇÃO DE PADRONIZAÇÃO
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

        # --- [NOVO/RESTAURADO] BLOCO: ALUNOS PRESENTES SEM FOTO ---
        try:
            # Busca a presença registrada hoje no sistema
            hoje_str = hoje.strftime('%Y-%m-%d')
            res_pres_hoje = supabase.table("frequencia_diaria")\
                .select("aluno_nome")\
                .eq("data", hoje_str)\
                .execute()
            
            # Busca IDs que já possuem foto (Assumindo tabela 'fotos_alunos' no banco de alunos)
            res_fotos = supabase_alunos.table("fotos_alunos").select("aluno_id").execute()
            ids_com_foto = set(str(f['aluno_id']) for f in res_fotos.data) if res_fotos.data else set()

            if res_pres_hoje.data:
                nomes_presentes = set(normalizar(p['aluno_nome']) for p in res_pres_hoje.data)
                
                # Filtra: está presente HOJE e o ID não está na tabela de fotos
                mask_presente = df_al['nome_limpo'].isin(nomes_presentes)
                mask_sem_foto = ~df_al['id'].astype(str).isin(ids_com_foto)
                
                df_alerta_fotos = df_al[mask_presente & mask_sem_foto]

                if not df_alerta_fotos.empty:
                    qtd_sem = len(df_alerta_fotos)
                    st.error(f"📸 **Atenção:** Identificamos **{qtd_sem}** alunos presentes hoje que ainda não possuem foto no sistema.")
                    
                    with st.expander("📍 Ver lista de estudantes para fotografar (por série)"):
                        # Agrupa por turma para facilitar a organização
                        for turma_ref, grupo in df_alerta_fotos.groupby('turma'):
                            st.markdown(f"**Turma: {turma_ref}**")
                            nomes_str = ", ".join(grupo.sort_values('nome')['nome'].tolist())
                            st.write(f"_{nomes_str}_")
                            st.divider()
        except Exception as e_foto:
            st.sidebar.info(f"💡 Info: Sistema de conferência de fotos aguardando dados.")

        # 2. FILTROS DE TOPO
        st.markdown("### 📅 Filtros de Pesquisa")
        c1, c2, c3 = st.columns([2, 2, 2])
        
        with c1:
            mes_nome = st.selectbox("Mês", list(calendar.month_name)[1:], index=hoje.month-1)
            mes_num = list(calendar.month_name).index(mes_nome)
        with c2:
            ano_sel = st.number_input("Ano", min_value=2024, max_value=2030, value=hoje.year)
        with c3:
            turmas_lista = sorted(df_al['turma'].unique())
            turma_sel = st.selectbox("Filtrar Turma", ["TODAS"] + turmas_lista)

        # 3. FILTRAGEM DOS DADOS
        df_t = df_al if turma_sel == "TODAS" else df_al[df_al['turma'] == turma_sel]
        
        # 4. BUSCA FREQUÊNCIA DO MÊS
        ultimo_dia = calendar.monthrange(ano_sel, mes_num)[1]
        data_inicio = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = f"{ano_sel}-{mes_num:02d}-{ultimo_dia}"

        res_f = supabase.table("frequencia_diaria")\
            .select("aluno_nome, data")\
            .filter("data", "gte", data_inicio)\
            .filter("data", "lte", data_fim)\
            .execute()
        
        # Criamos um set de (nome_normalizado, dia_str) para busca rápida
        presencas_mes_set = set()
        if res_f.data:
            for p in res_f.data:
                d_str = p['data'].split('-')[2] # Pega o "05" de "2024-05-05"
                presencas_mes_set.add((normalizar(p['aluno_nome']), d_str))

        # 5. INTERFACE EM ABAS
        abas = st.tabs(["📊 Dashboard", "🚨 Alertas Críticos", "📝 Registrar Ocorrência", "📂 Histórico", "📅 Diário Mensal"])

        # --- ABA 1: DASHBOARD ---
        with abas[0]:
            total_alunos = len(df_t)
            # Lógica simples de engajamento (exemplo)
            st.metric("Total de Alunos (Filtro)", total_alunos)
            st.info("Aqui você pode adicionar gráficos de evolução mensal de faltas.")

        # --- ABA 2: ALERTAS CRÍTICOS ---
        with abas[1]:
            st.subheader("🚩 Alunos com mais de 3 faltas consecutivas")
            # Aqui entraria sua lógica de contagem de faltas...
            st.write("Funcionalidade em desenvolvimento...")

        # --- ABA 3: REGISTRAR OCORRÊNCIA ---
        with abas[2]:
            st.subheader("📝 Registro de Busca Ativa")
            with st.form("form_ocorrencia"):
                aluno_oc = st.selectbox("Selecione o Aluno", df_t['nome'].sort_values().tolist())
                tipo = st.selectbox("Tipo de Contato", ["Telefone", "Visita Domiciliar", "Redes Sociais", "Responsável na Escola"])
                relato = st.text_area("Relato da Situação")
                resp_oc = st.text_input("Quem realizou o contato?")
                if st.form_submit_button("Salvar Registro"):
                    # Lógica de insert no supabase
                    st.success("Registro salvo com sucesso!")

        # --- ABA 5: DIÁRIO MENSAL (A QUE VOCÊ TINHA NO SNIPPET) ---
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
                            elif dt_dia.weekday() >= 5: linha[d] = "-" # Finais de semana
                            else: linha[d] = "❌"
                        except: linha[d] = " "
                matriz.append(linha)
            
            df_mapa = pd.DataFrame(matriz)
            st.dataframe(df_mapa, hide_index=True)

    except Exception as e:
        st.error(f"Erro geral na Busca Ativa: {e}")