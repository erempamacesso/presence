import streamlit as st
import pandas as pd
import datetime
import io

# Importações do ReportLab para os PDFs
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def exibir_cenario(supabase):
    st.title("📊 Cenário do Dia & Gestão de Frequência") 
    
    # --- CALENDÁRIO PE 2026 ---
    TRIMESTRES = {
        "1º Tri": (datetime.date(2026, 2, 2), datetime.date(2026, 5, 20)),
        "2º Tri": (datetime.date(2026, 5, 21), datetime.date(2026, 9, 11)),
        "3º Tri": (datetime.date(2026, 9, 12), datetime.date(2026, 12, 30))
    }
    RECESSO = (datetime.date(2026, 7, 10), datetime.date(2026, 7, 24))

    # ==========================================
    # 1. CONTROLE GLOBAL DE DATA
    # ==========================================
    col_data, col_vazia = st.columns([3, 7])
    with col_data:
        data_hoje = st.date_input("📅 Data de Análise:", value=datetime.date.today(), format="DD/MM/YYYY")
    
    hoje_iso = data_hoje.isoformat()
    st.divider()

    # ==========================================
    # 2. CRIAÇÃO DAS ABAS (NAVEGAÇÃO)
    # ==========================================
    tab_presenca, tab_evasao = st.tabs(["📋 Panorama de Presença (Diária)", "🏃‍♂️ Mapa de Evasões (Gazeadores)"])

    # #####################################################################
    # ABA 1: PANORAMA DE PRESENÇA (SEU CÓDIGO ORIGINAL + PDF DE FALTAS)
    # #####################################################################
    with tab_presenca:
        col_esq, col_dir = st.columns([7, 3], gap="large")
        
        df_presentes_hoje = pd.DataFrame()
        n_presentes, total_alunos, n_faltas, perc = 0, 0, 0, 0

        try:
            # Pega total de alunos
            res_total = supabase.table("alunos").select("id", count="exact").execute()
            total_alunos = res_total.count if res_total.count else 0
            
            # Pega presentes do dia
            res_freq = supabase.table("frequencia").select("*").eq("data_chamada", hoje_iso).eq("status", "P").execute()
            
            if res_freq.data:
                df_presentes_hoje = pd.DataFrame(res_freq.data)
                col_nome = next((c for c in ['aluno_nome', 'nome_aluno'] if c in df_presentes_hoje.columns), None)
                
                if col_nome:
                    n_presentes = len(df_presentes_hoje[col_nome].unique())
                else:
                    n_presentes = len(df_presentes_hoje)
                    
            # Cálculos de faltas e percentual
            n_faltas = total_alunos - n_presentes
            perc = (n_presentes / total_alunos * 100) if total_alunos > 0 else 0
            
        except Exception as e:
            st.error(f"⚠️ Erro na conexão: {e}")

        # LADO ESQUERDO (Métricas e Gráfico)
        with col_esq:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Presentes", n_presentes)
            c2.metric("Ausentes do Dia", n_faltas, delta=f"{n_faltas}", delta_color="inverse")
            c3.metric("% Freq", f"{perc:.1f}%")
            c4.metric("Matrícula", total_alunos)

            if RECESSO[0] <= data_hoje <= RECESSO[1]:
                st.info("ℹ️ Período de Recesso Escolar")

            st.divider()

            try:
                if not df_presentes_hoje.empty and 'turma' in df_presentes_hoje.columns:
                    st.subheader("🏫 Presença por Turma")
                    df_turmas = df_presentes_hoje.groupby('turma').size().reset_index(name='Presentes')
                    st.bar_chart(data=df_turmas, x="turma", y="Presentes", color="#00C896", height=450, use_container_width=True)
                else:
                    st.info("Aguardando registros de chamada para gerar o gráfico.")
            except:
                pass

        # LADO DIREITO (Tabela Resumo)
        with col_dir:
            st.subheader("📋 Resumo por Sala")
            if not df_presentes_hoje.empty and 'turma' in df_presentes_hoje.columns:
                df_resumo = df_presentes_hoje.groupby('turma').size().reset_index(name='Qtd')
                df_resumo = df_resumo.sort_values(by='turma')
                st.dataframe(
                    df_resumo, use_container_width=True, hide_index=True, height=530,
                    column_config={"turma": st.column_config.TextColumn("Turma"), "Qtd": st.column_config.NumberColumn("Presentes")}
                )
            else:
                st.info("Nenhuma presença registrada.")

        # ÁREA INFERIOR (Alunos Ausentes + PDF)
        st.divider() 
        st.subheader(f"🚨 Estudantes Ausentes ({data_hoje.strftime('%d/%m/%Y')})")
        st.caption("Selecione uma turma para ver quem faltou hoje e baixar a lista.")

        try:
            res_t_raw = supabase.table("alunos").select("turma").execute().data
            lista_turmas = []
            if res_t_raw:
                lista_turmas = sorted(list(set([t['turma'] for t in res_t_raw if t.get('turma')])))
            
            if lista_turmas:
                turma_selecionada = st.pills("Turmas disponíveis:", options=lista_turmas, key="pills_faltas")
                
                if turma_selecionada:
                    res_f = supabase.table("frequencia").select("aluno_nome").eq("data_chamada", hoje_iso).eq("turma", turma_selecionada).eq("status", "F").execute().data
                    
                    if res_f:
                        df_faltosos = pd.DataFrame(res_f).sort_values(by="aluno_nome")
                        
                        # --- GERADOR DE PDF DE FALTAS ---
                        buffer_faltas = io.BytesIO()
                        pdf_f = canvas.Canvas(buffer_faltas, pagesize=A4)
                        pdf_f.setFont("Helvetica-Bold", 16)
                        pdf_f.drawString(50, 800, f"Lista de Ausentes - {turma_selecionada}")
                        pdf_f.setFont("Helvetica", 12)
                        pdf_f.drawString(50, 780, f"Data: {data_hoje.strftime('%d/%m/%Y')}")
                        y_pos = 740
                        pdf_f.setFont("Helvetica-Bold", 12)
                        pdf_f.drawString(50, y_pos, f"Total de ausentes: {len(df_faltosos)}")
                        y_pos -= 20
                        pdf_f.setFont("Helvetica", 12)
                        for idx, row in df_faltosos.iterrows():
                            pdf_f.drawString(60, y_pos, f"• {row['aluno_nome']}")
                            y_pos -= 20
                            if y_pos < 50:
                                pdf_f.showPage()
                                y_pos = 800
                                pdf_f.setFont("Helvetica", 12)
                        pdf_f.save()
                        buffer_faltas.seek(0)
                        
                        # Exibição na Tela
                        df_exibicao = df_faltosos.copy()
                        df_exibicao['Ícone'] = "❌"
                        df_exibicao = df_exibicao[['Ícone', 'aluno_nome']] 
                        
                        col_vazia1, col_tabela, col_vazia2 = st.columns([1, 2, 1])
                        with col_tabela:
                            st.dataframe(df_exibicao, use_container_width=True, hide_index=True, column_config={"Ícone": st.column_config.TextColumn("", width="small"), "aluno_nome": st.column_config.TextColumn("Nome do Estudante")})
                            st.download_button(
                                label="📥 Baixar Lista de Ausentes (PDF)",
                                data=buffer_faltas.getvalue(),
                                file_name=f"Faltas_{turma_selecionada}_{data_hoje.strftime('%d_%m_%Y')}.pdf",
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True
                            )
                    else:
                        st.success(f"🎉 Excelente! Nenhuma falta registrada para a turma {turma_selecionada} hoje.")
        except Exception as e:
            st.error(f"Erro ao carregar lista de ausentes: {e}")

    # #####################################################################
    # ABA 2: MAPA DE EVASÕES (GAZEADORES)
    # #####################################################################
    with tab_evasao:
        st.subheader(f"🏃‍♂️ Mapa de Infrequência Seletiva ({data_hoje.strftime('%d/%m/%Y')})")
        st.caption("Análise de estudantes que se ausentam durante as aulas específicas.")

        try:
            res_ev = supabase.table("evasoes").select("*").eq("data_registro", hoje_iso).execute()
            df_ev = pd.DataFrame(res_ev.data)

            if not df_ev.empty:
                # KPIs
                total_evasoes = len(df_ev)
                pico_aula = df_ev['aula_periodo'].value_counts().idxmax()
                turma_critica = df_ev['turma'].value_counts().idxmax()

                c1, c2, c3 = st.columns(3)
                c1.metric("Total de Fugas Registradas", total_evasoes)
                c2.metric("Horário de Maior Fuga", pico_aula)
                c3.metric("Turma com Mais Ocorrências", turma_critica)

                st.divider()

                # Gráficos e Rankings
                col_chart, col_rank = st.columns([6, 4])
                with col_chart:
                    st.write("**Frequência de Evasão por Aula/Período**")
                    df_aula = df_ev.groupby('aula_periodo').size().reset_index(name='Qtd')
                    st.bar_chart(df_aula, x="aula_periodo", y="Qtd", color="#FF8000")

                with col_rank:
                    st.write("**🏆 Top Gazeadores do Dia**")
                    df_rank = df_ev['aluno_nome'].value_counts().reset_index()
                    df_rank.columns = ['Estudante', 'Nº de Fugas']
                    st.dataframe(df_rank, use_container_width=True, hide_index=True)

                # Tabela de Detalhes
                st.write("**📋 Registro Detalhado**")
                st.dataframe(
                    df_ev[['turma', 'aluno_nome', 'aula_periodo', 'observacao']].sort_values(by=['turma', 'aluno_nome']),
                    use_container_width=True,
                    hide_index=True
                )

                # --- GERADOR DE PDF DO MAPA DE EVASÕES ---
                st.divider()
                buffer_ev = io.BytesIO()
                doc = SimpleDocTemplate(buffer_ev, pagesize=A4)
                elements = []
                styles = getSampleStyleSheet()

                elements.append(Paragraph(f"<b>RELATÓRIO DE EVASÃO ESCOLAR (GAZEADORES) - EREMPAM</b>", styles['Title']))
                elements.append(Paragraph(f"Data: {data_hoje.strftime('%d/%m/%Y')}", styles['Normal']))
                elements.append(Paragraph(f"Total de Registros: {total_evasoes}", styles['Normal']))
                elements.append(Spacer(1, 20))

                data_pdf = [["Turma", "Nome do Estudante", "Aula/Período"]]
                for _, row in df_ev.sort_values(by=['turma', 'aluno_nome']).iterrows():
                    data_pdf.append([str(row['turma']), str(row['aluno_nome']), str(row['aula_periodo'])])

                t = Table(data_pdf, colWidths=[80, 280, 100])
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
                
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    st.download_button(
                        label="📥 Imprimir Mapa de Evasão Completo (PDF)",
                        data=buffer_ev.getvalue(),
                        file_name=f"Mapa_Evasao_{data_hoje.strftime('%d_%m_%Y')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
            else:
                st.success(f"✅ Nenhum registro de evasão (fuga de aula) para o dia {data_hoje.strftime('%d/%m/%Y')}. Tudo sob controle!")

        except Exception as e:
            st.error(f"Erro ao processar mapa de evasão: {e}")