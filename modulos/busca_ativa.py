import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

def exibir_busca_ativa(supabase):
    st.title("🔎 Painel de Busca Ativa")
    st.caption("Inteligência de Dados para Prevenção ao Abandono Escolar")
    st.markdown("---")

    fuso = pytz.timezone('America/Recife')
    hoje = datetime.now(fuso).strftime('%Y-%m-%d')

    # --- 1. MÉTRICAS RÁPIDAS (HOJE) ---
    st.subheader(f"📊 Resumo do Dia: {datetime.now(fuso).strftime('%d/%m/%Y')}")
    
    col1, col2, col3 = st.columns(3)

    try:
        # Faltas totais hoje (Tabela frequencia onde status = 'F')
        res_faltas = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "F").execute()
        total_faltas = res_faltas.count if res_faltas.count else 0
        
        # Evasões totais hoje (Tabela evasoes)
        res_evasoes = supabase.table("evasoes").select("id", count="exact").eq("data_registro", hoje).execute()
        total_evasoes = res_evasoes.count if res_evasoes.count else 0

        # Presentes na entrada
        res_pres = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "P").execute()
        total_presentes = res_pres.count if res_pres.count else 0

        col1.metric("Faltas (Entrada)", total_faltas)
        col2.metric("Evasões (Em aula)", total_evasoes)
        col3.metric("Presentes Agora", total_presentes)
    except:
        st.error("Erro ao carregar métricas em tempo real.")

    st.markdown("---")

    # --- 2. CRUZAMENTO CRÍTICO: EVASÃO INTERNA ---
    st.subheader("🚨 Alerta de Evasão Interna")
    st.write("Alunos que deram presença na entrada, mas foram registrados saindo de alguma aula.")

    try:
        # Busca quem deu presença hoje
        pres_hoje = supabase.table("frequencia").select("aluno_nome, turma").eq("data_chamada", hoje).eq("status", "P").execute()
        # Busca quem fugiu hoje
        evas_hoje = supabase.table("evasoes").select("aluno_nome, turma, aula_periodo").eq("data_registro", hoje).execute()

        if pres_hoje.data and evas_hoje.data:
            df_pres = pd.DataFrame(pres_hoje.data)
            df_evas = pd.DataFrame(evas_hoje.data)
            
            # Filtra apenas quem está nas duas listas (Cruzamento)
            fugoes_internos = df_evas[df_evas['aluno_nome'].isin(df_pres['aluno_nome'])]
            
            if not fugoes_internos.empty:
                st.warning(f"Atenção: {len(fugoes_internos)} alunos entraram na escola mas não estão em sala.")
                st.dataframe(fugoes_internos[['aluno_nome', 'turma', 'aula_periodo']], use_container_width=True)
            else:
                st.success("Nenhuma evasão interna detectada hoje.")
        else:
            st.info("Aguardando registros de frequência e evasão para cruzar dados.")
    except Exception as e:
        st.error(f"Erro no processamento: {e}")

    st.markdown("---")

    # --- 3. RANKING DE VULNERABILIDADE (HISTÓRICO DE 5 DIAS) ---
    st.subheader("🏆 Ranking de Alunos Faltosos (Últimos 5 dias)")
    st.write("Identifique quem precisa de uma conversa com a coordenação.")

    try:
        # Pega todo o histórico de faltas ('F') da tabela frequencia
        res_hist = supabase.table("frequencia").select("aluno_nome, turma").eq("status", "F").execute()
        
        if res_hist.data:
            df_hist = pd.DataFrame(res_hist.data)
            ranking = df_hist['aluno_nome'].value_counts().reset_index()
            ranking.columns = ['Aluno', 'Total de Faltas']
            
            # Adiciona a turma ao ranking para facilitar a localização
            df_turmas = df_hist.drop_duplicates('aluno_nome')[['aluno_nome', 'turma']]
            ranking = ranking.merge(df_turmas, left_on='Aluno', right_on='aluno_nome').drop('aluno_nome', axis=1)
            
            # Exibe o Top 10
            st.table(ranking.head(10))
        else:
            st.info("Ainda não há histórico de faltas acumulado.")
    except:
        st.error("Erro ao gerar ranking histórico.")
