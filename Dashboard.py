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

    # ==========================================
    # 2. BUSCA DE DADOS
    # ==========================================
    with col_esq:
        data_hoje = st.date_input("Data de Análise:", value=datetime.date.today(), format="DD/MM/YYYY")
    
    hoje_iso = data_hoje.isoformat()
    df_matriculas_total = pd.DataFrame()
    df_presentes_hoje = pd.DataFrame()
    n_presentes, total_alunos = 0, 0

    try:
        # Puxa todos os alunos para contar o total real por turma
        res_alunos = supabase.table("alunos").select("id, turma").execute()
        if res_alunos.data:
            df_matriculas_total = pd.DataFrame(res_alunos.data)
            total_alunos = len(df_matriculas_total)
        
        # Puxa frequencia do dia
        res_freq = supabase.table("frequencia").select("aluno_nome, turma").eq("data_chamada", hoje_iso).eq("status", "P").execute()
        if res_freq.data:
            df_presentes_hoje = pd.DataFrame(res_freq.data)
            n_presentes = len(df_presentes_hoje)

        n_faltas = total_alunos - n_presentes
        perc = (n_presentes / total_alunos * 100) if total_alunos > 0 else 0
        
    except Exception as e:
        st.error(f"Erro na conexão: {e}")

    # ==========================================
    # 3. COLUNA ESQUERDA: MÉTRICAS E GRÁFICO
    # ==========================================
    with col_esq:
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Presentes", n_presentes)
        m2.metric("Ausentes", n_faltas, delta=f"-{n_faltas}", delta_color="inverse")
        m3.metric("% Frequência", f"{perc:.1f}%")
        m4.metric("Matrícula Total", total_alunos)

        if RECESSO[0] <= data_hoje <= RECESSO[1]:
            st.info("ℹ️ Período de Recesso Escolar")

        st.divider()
        st.subheader("🏫 Presença por Turma")
        if not df_presentes_hoje.empty:
            df_graf = df_presentes_hoje.groupby('turma').size().reset_index(name='Presentes')
            st.bar_chart(df_graf, x="turma", y="Presentes", color="turma", height=400)
        else:
            st.info("Nenhuma presença registrada para este dia.")

    # ==========================================
    # 4. COLUNA DIREITA: A TABELA QUE VOCÊ QUERIA
    # ==========================================
    with col_dir:
        st.subheader("📋 Resumo por Sala")
        
        if not df_matriculas_total.empty:
            # 1. Conta total de alunos por turma (da tabela alunos)
            df_resumo = df_matriculas_total.groupby('turma').size().reset_index(name='Total')
            
            # 2. Conta presentes por turma (da tabela frequencia)
            if not df_presentes_hoje.empty:
                df_p = df_presentes_hoje.groupby('turma').size().reset_index(name='Pres.')
                # Junta as duas informações
                df_resumo = pd.merge(df_resumo, df_p, on='turma', how='left').fillna(0)
            else:
                df_resumo['Pres.'] = 0
            
            # Formatação final
            df_resumo['Pres.'] = df_resumo['Pres.'].astype(int)
            df_resumo = df_resumo.sort_values(by='turma')
            
            # Exibe a tabela organizada: Turma | Presentes | Total
            st.dataframe(
                df_resumo[['turma', 'Pres.', 'Total']],
                use_container_width=True,
                hide_index=True,
                height=550,
                column_config={
                    "turma": "Turma",
                    "Pres.": st.column_config.NumberColumn("Pres.", help="Alunos presentes hoje"),
                    "Total": st.column_config.NumberColumn("Total", help="Total de matriculados")
                }
            )
        else:
            st.warning("Não há dados de matrícula.")

    # ==========================================
    # 5. RODAPÉ: LISTA DE AUSENTES (PDF)
    # ==========================================
    st.divider()
    st.subheader("🚨 Lista de Estudantes Ausentes")
    
    try:
        if not df_matriculas_total.empty:
            lista_t = sorted(df_matriculas_total['turma'].unique())
            t_sel = st.pills("Selecione a turma para ver faltas:", options=lista_t)
            
            if t_sel:
                res_f = supabase.table("frequencia").select("aluno_nome").eq("data_chamada", hoje_iso).eq("turma", t_sel).eq("status", "F").execute()
                if res_f.data:
                    df_f = pd.DataFrame(res_f.data).sort_values(by="aluno_nome")
                    st.table(df_f)
                    
                    # Gerar PDF
                    buf = io.BytesIO()
                    c = canvas.Canvas(buf, pagesize=A4)
                    c.drawString(50, 800, f"Ausentes - {t_sel} - {data_hoje}")
                    y = 770
                    for n in df_f['aluno_nome']:
                        c.drawString(60, y, f"• {n}")
                        y -= 20
                    c.save()
                    st.download_button("📥 Baixar PDF", buf.getvalue(), f"Faltas_{t_sel}.pdf", "application/pdf")
                else:
                    st.success("Tudo certo! Nenhuma falta nesta turma.")
    except Exception as e:
        st.error(f"Erro ao listar ausentes: {e}")