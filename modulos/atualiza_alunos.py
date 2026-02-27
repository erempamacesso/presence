import streamlit as st
import pandas as pd
import re

def exibir_importacao(supabase):
    st.title("📤 Importação de Matrículas e Dados")
    st.info("Esta ferramenta processa o Excel oficial, atualiza turmas e insere Sexo/Nascimento.")

    arquivo = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])

    if arquivo:
        xl = pd.ExcelFile(arquivo)
        abas = xl.sheet_names
        
        # Filtramos apenas as abas que seguem o padrão de turmas
        abas_turmas = [a for a in abas if "EM45" in a]
        
        st.write(f"📊 **{len(abas_turmas)} turmas detectadas no arquivo.**")

        if st.button("🚀 Iniciar Processamento Global"):
            barra = st.progress(0)
            status = st.empty()
            
            for i, nome_aba in enumerate(abas_turmas):
                # Lógica Crítica: Extrair "1º A" de "1 - EM45-1IA"
                # Pegamos os dois últimos caracteres (ex: 1A, 2C) e formatamos
                sigla = nome_aba[-2:] 
                ano = sigla[0]
                letra = sigla[1]
                turma_formatada = f"{ano}º {letra}"
                
                status.text(f"Atualizando {turma_formatada}...")
                
                df = pd.read_excel(xl, sheet_name=nome_aba)
                
                # Padronização de Colunas (Garante que nomes batam com o banco)
                dados_para_upsert = []
                for _, linha in df.iterrows():
                    # Tratamento de Data
                    try:
                        dt_nasc = pd.to_datetime(linha['Data de nascimento']).strftime('%Y-%m-%d')
                    except:
                        dt_nasc = None

                    dados_para_upsert.append({
                        "nome": str(linha['Nome']).strip().upper(),
                        "turma": turma_formatada,
                        "data_nascimento": dt_nasc,
                        "sexo": str(linha['Sexo']).strip().upper()
                    })

                # UPSERT: A mágica acontece aqui. 
                # Se o nome já existir, ele só atualiza Turma, Sexo e Data.
                # Se não existir, ele cria o novo aluno.
                try:
                    supabase.table("alunos").upsert(dados_para_upsert, on_conflict="nome").execute()
                except Exception as e:
                    st.error(f"Erro na aba {nome_aba}: {e}")

                barra.progress((i + 1) / len(abas_turmas))
            
            status.success("✅ Processamento finalizado! O banco de dados está atualizado.")
