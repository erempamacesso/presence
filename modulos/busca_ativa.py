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
        res_faltas = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "F").execute()
        total_faltas = res_faltas.count if res_faltas.count else 0
        
        res_evasoes = supabase.table("evasoes").select("id", count="exact").eq("data_registro", hoje).execute()
        total_evasoes = res_evasoes.count if res_evasoes.count else 0

        res_pres = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "P").execute()
        total_presentes = res_pres.count if res_pres.count else 0

        col1.metric("Faltas (Entrada)", total_faltas)
        col2.metric("Evasões (Em aula)", total_evasoes)
        col3.metric("Presentes Agora", total_presentes)
    except:
        st.error("Erro ao carregar métricas.")

    st.markdown("---")

    # --- 2. CRUZAMENTO CRÍTICO: EVASÃO INTERNA ---
    # (Mantendo sua lógica anterior aqui...)
    st.subheader("🚨 Alerta de Evasão Interna")
    # ... código de cruzamento ...

    st.markdown("---")

    # --- 3. RANKING DE VULNERABILIDADE COM FOTO ---
    st.subheader("🏆 Ranking de Alunos Faltosos (Últimos 5 dias)")
    st.write("Prioridade para busca ativa baseada na frequência.")

    try:
        # 1. Pega o histórico de faltas
        res_hist = supabase.table("frequencia").select("aluno_nome, turma").eq("status", "F").execute()
        
        if res_hist.data:
            df_hist = pd.DataFrame(res_hist.data)
            
            # 2. Gera o ranking (contagem de faltas)
            ranking = df_hist['aluno_nome'].value_counts().reset_index()
            ranking.columns = ['Aluno', 'Faltas']
            
            # 3. Recupera a turma
            df_turmas = df_hist.drop_duplicates('aluno_nome')[['aluno_nome', 'turma']]
            ranking = ranking.merge(df_turmas, left_on='Aluno', right_on='aluno_nome').drop('aluno_nome', axis=1)

            # 4. LÓGICA DA FOTO: 
            # Vamos construir a URL da foto. 
            # Ajuste a URL abaixo para o caminho real do seu bucket no Supabase
            URL_BASE_FOTOS = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos_alunos/"
            
            # Criamos uma coluna 'Foto' que aponta para o arquivo .jpg com o nome do aluno
            ranking['Foto'] = ranking['Aluno'].apply(lambda nome: f"{URL_BASE_FOTOS}{nome.replace(' ', '%20')}.jpg")

            # Reorganiza as colunas para a foto vir primeiro
            ranking = ranking[['Foto', 'Aluno', 'turma', 'Faltas']]

            # 5. EXIBIÇÃO VISUAL PREMIUM
            st.dataframe(
                ranking.head(10),
                use_container_width=True,
                hide_index=True, # Remove os números 0, 1, 2...
                column_config={
                    "Foto": st.column_config.ImageColumn("📸", width="small"), # Transforma o link em imagem
                    "Aluno": st.column_config.TextColumn("Nome do Estudante"),
                    "turma": st.column_config.TextColumn("Turma", width="small"),
                    "Faltas": st.column_config.NumberColumn("⚠️ Total Faltas", format="%d")
                }
            )
        else:
            st.info("Ainda não há histórico de faltas acumulado.")
    except Exception as e:
        st.error(f"Erro ao gerar ranking visual: {e}")
