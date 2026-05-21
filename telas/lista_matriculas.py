import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import unicodedata

def mostrar_tela_lista_matriculas(supabase_alunos):
    st.title("👥 Listas por Turma (PDF)")
    st.write("Visualize a listagem de alunos com o número de matrícula oficial.")

    try:
        # Busca os alunos
        res_a = supabase_alunos.table("alunos").select("*").execute()
        
        if res_a.data:
            df_alunos = pd.DataFrame(res_a.data)
            
            # --- MAPEAMENTO EXATO (Baseado no seu Supabase) ---
            col_t = 'turma' 
            col_n = 'nome' 
            col_m = 'id' 

            if col_t not in df_alunos.columns or col_n not in df_alunos.columns or col_m not in df_alunos.columns:
                st.error("Erro técnico: Colunas 'id', 'nome' ou 'turma' não encontradas. Verifique o banco.")
            else:
                # Seletor de Turma
                turmas_disponiveis = sorted(df_alunos[col_t].dropna().unique())
                turma_selecionada = st.selectbox("Selecione a Turma:", turmas_disponiveis)

                # Filtro e Ordenação por Nome
                df_turma = df_alunos[df_alunos[col_t] == turma_selecionada].sort_values(by=col_n).reset_index(drop=True)
                
                # Adiciona o número de ordem (1, 2, 3...)
                df_turma['Nº'] = df_turma.index + 1 
                
                # Prepara colunas para exibição na tela
                colunas_tela = ['Nº']
                if col_m in df_alunos.columns:
                    colunas_tela.append(col_m)
                colunas_tela.append(col_n)

                st.write(f"Total de alunos na turma: **{len(df_turma)}**")
                
                # Exibe a tabela formatada (Trocando na tela para ficar bonito)
                df_exibir = df_turma[colunas_tela].copy()
                if col_m in df_alunos.columns:
                    df_exibir = df_exibir.rename(columns={col_m: "Matrícula"})
                
                st.dataframe(df_exibir, use_container_width=False, hide_index=True)

                st.divider()

                # --- GERAÇÃO DO PDF ---
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, 'EREMPAM - LISTAGEM DE MATRICULAS', ln=True, align='C')
                
                t_limpa = unicodedata.normalize('NFKD', str(turma_selecionada)).encode('ASCII', 'ignore').decode('ASCII')
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, f'TURMA: {t_limpa}', ln=True, align='L')
                pdf.ln(5)

                # Cabeçalho do PDF
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(12, 8, 'N', border=1, align='C')
                
                larg_nome = 110
                if col_m in df_alunos.columns:
                    pdf.cell(35, 8, 'MATRICULA', border=1, align='C')
                    larg_nome = 95
                    
                pdf.cell(larg_nome, 8, 'NOME DO ALUNO', border=1, align='C')
                pdf.cell(35, 8, 'OBSERVACAO', border=1, align='C')
                pdf.ln()

                # Linhas do PDF
                pdf.set_font('Arial', '', 10)
                for row in df_turma.itertuples():
                    pdf.cell(12, 8, str(row.Index + 1), border=1, align='C')
                    
                    if col_m in df_alunos.columns:
                        # Pega o valor da matrícula diretamente
                        val_m = str(getattr(row, col_m))
                        pdf.cell(35, 8, val_m, border=1, align='C')
                        
                    nome_p = unicodedata.normalize('NFKD', str(getattr(row, col_n))).encode('ASCII', 'ignore').decode('ASCII')[:35]
                    pdf.cell(larg_nome, 8, nome_p, border=1, align='L')
                    pdf.cell(35, 8, '', border=1, align='C')
                    pdf.ln()

                # Download
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    pdf.output(tmp.name)
                    with open(tmp.name, "rb") as f:
                        pdf_bytes = f.read()

                st.download_button(
                    label="📥 Baixar PDF da Turma",
                    data=pdf_bytes,
                    file_name=f"Matriculas_{t_limpa.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
        else:
            st.warning("Nenhum dado encontrado na tabela de alunos.")

    except Exception as e:
        st.error(f"Erro ao processar matrículas: {e}")