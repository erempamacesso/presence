import streamlit as st
import pandas as pd
import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def exibir_cenario(supabase):
    st.title("📊 Cenário do Dia") 
    
    # --- CALENDÁRIO PE 2026 ---
    RECESSO = (datetime.date(2026, 7, 10), datetime.date(2026, 7, 24))

    # ==========================================
    # 1. DIVISÃO DA TELA (70% Esq / 30% Dir)
    # ==========================================
    col_esq, col_dir = st.columns([7, 3], gap="large")

    with col_esq:
        data_hoje = st.date_input("Data de Análise:", value=datetime.date.today(), format="DD/MM/YYYY")
    
    hoje_iso = data_hoje.isoformat()
    df_matriculas_total = pd.DataFrame()
    df_presentes_hoje = pd.DataFrame()
    n_presentes, total_alunos = 0, 0

    # Bloco de busca de dados
    try:
        # Puxa matrículas
        res_alunos = supabase.table("alunos").select("id, turma").execute()
        if res_alunos.data:
            df_matriculas_total = pd.DataFrame(res_alunos.data)
            total_alunos = len(df_matriculas_total)
        
        # Puxa frequencia
        res_freq = supabase.table("frequencia").select("aluno_nome, turma").eq("data_chamada", hoje_iso).eq("status", "P").execute()
        if res_freq.data:
            df_presentes_hoje = pd.DataFrame(res_freq.data)
            n_presentes = len(df_presentes_hoje)

        n_faltas = total_alunos - n_presentes
        perc = (n_presentes / total_alunos * 100) if total_alunos > 0 else 0
        
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")

    # ==========================================
    # 2. COLUNA ESQUERDA (Métricas e Gráfico)
    # ==========================================
    with col_esq:
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Presentes", n_presentes)
        m2.metric("Ausentes", n_faltas, delta=f"-{n_faltas}", delta_color="inverse")
        m3.metric("% Frequência", f"{perc:.1f}%")
        m4.metric("Matrícula Total", total_alunos)

        st.divider()
        st.subheader("🏫 Presença por Turma")
        if not df_presentes_hoje.empty:
            df_graf = df_presentes_hoje.groupby('turma').size().reset_index(name='Presentes')
            st.bar_chart(df_graf, x="turma", y="Presentes", color="turma", height=400)
        else:
            st.info("Nenhuma presença registrada.")

    # ==========================================
    # 3. COLUNA DIREITA (Tabela com parênteses)
    # ==========================================
    with col_dir:
        st.subheader("📋 Resumo por Sala")
        
        if not df_matriculas_total.empty:
            # Agrupa totais e presentes
            df_resumo = df_matriculas_total.groupby('turma').size().reset_index(name='Total')
            
            if not df_presentes_hoje.empty:
                df_p = df_presentes_hoje.groupby('turma').size().reset_index(name='Pres.')
                df_resumo = pd.merge(df_resumo, df_p, on='turma', how='left').fillna(0)
            else:
                df_resumo['Pres.'] = 0
            
            df_resumo['Pres.'] = df_resumo['Pres.'].astype(int)
            df_resumo = df_resumo.sort_values(by='turma')
            
            # Formatação solicitada: 1º A (39)
            df_resumo['Turma_Formatada'] = df_resumo['turma'] + " (" + df_resumo['Total'].astype(str) + ")"
            
            st.dataframe(
                df_resumo[['Turma_Formatada', 'Pres.']],
                use_container_width=True,
                hide_index=True,
                height=550,
                column_config={
                    "Turma_Formatada": "Turma (Total)",
                    "Pres.": "Presentes"
                }
            )
        else:
            st.warning("Sem dados.")

    # ==========================================
    # 4. LISTA DE AUSENTES
    # ==========================================
    st.divider()
    st.subheader("🚨 Estudantes Ausentes")
    try:
        if not df_matriculas_total.empty:
            lista_t = sorted(df_matriculas_total['turma'].unique())
            t_sel = st.pills("Selecione a turma:", options=lista_t)
            
            if t_sel:
                res_f = supabase.table("frequencia").select("aluno_nome").eq("data_chamada", hoje_iso).eq("turma", t_sel).eq("status", "F").execute()
                if res_f.data:
                    df_f = pd.DataFrame(res_f.data).sort_values(by="aluno_nome")
                    st.table(df_f)
    except Exception as e:
        pass # Silencia erro na listagem se houver
