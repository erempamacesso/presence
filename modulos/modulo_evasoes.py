import streamlit as st
import pandas as pd
import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def exibir_evasoes(supabase):
    st.title("🏃‍♂️ Mapa de Infrequência Seletiva (Evasões)")
    st.caption("Análise de estudantes que se ausentam durante as aulas")

    # 1. FILTROS
    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        data_sel = st.date_input("Filtrar por data:", datetime.date.today())
    
    # 2. BUSCA DE DADOS
    try:
        res = supabase.table("evasoes").select("*").eq("data_registro", data_sel.isoformat()).execute()
        df = pd.DataFrame(res.data)

        if not df.empty:
            # MÉTRICAS RÁPIDAS
            total_evasoes = len(df)
            pico_aula = df['aula_periodo'].value_counts().idxmax()
            turma_critica = df['turma'].value_counts().idxmax()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total de Evasões", total_evasoes)
            c2.metric("Horário Crítico", pico_aula)
            c3.metric("Turma Líder", turma_critica)

            st.divider()

            # 3. VISUALIZAÇÃO DIGITAL (MAPA NA TELA)
            col_chart, col_rank = st.columns([6, 4])

            with col_chart:
                st.subheader("📊 Frequência por Período de Aula")
                df_aula = df.groupby('aula_periodo').size().reset_index(name='Qtd')
                st.bar_chart(df_aula, x="aula_periodo", y="Qtd", color="#FF8000")

            with col_rank:
                st.subheader("🏆 Top Gazeadores do Dia")
                df_rank = df['aluno_nome'].value_counts().reset_index()
                df_rank.columns = ['Estudante', 'Fugas']
                st.dataframe(df_rank, use_container_width=True, hide_index=True)

            # 4. TABELA DETALHADA
            st.subheader("📋 Registro Detalhado")
            st.dataframe(
                df[['turma', 'aluno_nome', 'aula_periodo']].sort_values(by=['turma', 'aluno_nome']),
                use_container_width=True,
                hide_index=True
            )

            # 5. GERADOR DE PDF (O MAPA PARA IMPRESSÃO)
            st.divider()
            
            # --- Lógica do PDF ---
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()

            # Título e Cabeçalho
            elements.append(Paragraph(f"<b>RELATÓRIO DE EVASÃO ESCOLAR - EREMPAM</b>", styles['Title']))
            elements.append(Paragraph(f"Data de Análise: {data_sel.strftime('%d/%m/%Y')}", styles['Normal']))
            elements.append(Paragraph(f"Total de Registros: {total_evasoes}", styles['Normal']))
            elements.append(Spacer(1, 20))

            # Tabela de Dados para o PDF
            data_pdf = [["Turma", "Nome do Estudante", "Aula/Período"]]
            for _, row in df.sort_values(by=['turma', 'aluno_nome']).iterrows():
                data_pdf.append([row['turma'], row['aluno_nome'], row['aula_periodo']])

            t = Table(data_pdf, colWidths=[60, 300, 100])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
            ]))
            elements.append(t)
            doc.build(elements)
            
            # Botão de Download
            st.download_button(
                label="📥 Baixar Mapa de Evasão (PDF)",
                data=buffer.getvalue(),
                file_name=f"Evasao_{data_sel.strftime('%d_%m_%Y')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

        else:
            st.success(f"✅ Nenhum registro de evasão para o dia {data_sel.strftime('%d/%m/%Y')}. Tudo sob controle!")

    except Exception as e:
        st.error(f"Erro ao processar mapa de evasão: {e}")