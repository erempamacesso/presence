import streamlit as st
import pandas as pd
from datetime import date

def exibir_frequencia(supabase):
    st.title("📊 Relatório de Frequência Diária")
    
    hoje = date.today().isoformat()
    hoje_formatado = date.today().strftime('%d/%m/%Y')
    
    st.write(f"Dados referentes ao dia: **{hoje_formatado}**")
    
    try:
        # 1. Busca o total de alunos matriculados
        res_total = supabase.table("alunos").select("id", count="exact").execute()
        total_alunos = res_total.count if res_total.count else 0
        
        # 2. Busca os registos de frequência de hoje
        res_freq = supabase.table("frequencia").select("*").eq("data_chamada", hoje).execute()
        df_presenca = pd.DataFrame(res_freq.data)

        if not df_presenca.empty:
            # Conta alunos únicos presentes hoje
            presentes = len(df_presenca.drop_duplicates(subset=['aluno_id']))
            faltas = total_alunos - presentes
            
            # Exibe os cartões de métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("Total de Alunos", total_alunos)
            c2.metric("Presentes Agora", presentes, delta=f"{presentes} alunos", delta_color="normal")
            c3.metric("Ausentes", faltas, delta=f"-{faltas}", delta_color="inverse")
            
            st.divider()
            
            # Tabela detalhada
            st.subheader("Lista de Presença (Tempo Real)")
            # Limpeza simples para exibir melhor
            df_exibir = df_presenca[['aluno_nome', 'turma', 'horario_entrada']].copy()
            df_exibir.columns = ['Nome do Aluno', 'Turma', 'Hora de Entrada']
            st.dataframe(df_exibir.sort_values(by="Hora de Entrada", ascending=False), use_container_width=True)
            
        else:
            # Se não houver ninguém ainda
            c1, c2, c3 = st.columns(3)
            c1.metric("Total de Alunos", total_alunos)
            c2.metric("Presentes Agora", 0)
            c3.metric("Ausentes", total_alunos)
            
            st.info(f"Nenhum registo de frequência encontrado para hoje ({hoje_formatado}) até ao momento.")
            
    except Exception as e:
        st.error(f"Erro ao carregar dados de frequência: {e}")
