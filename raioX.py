import streamlit as st
import pandas as pd

st.set_page_config(page_title="Raio-X do SIEPE", layout="wide")

st.title("🕵️‍♂️ Raio-X da Planilha do SIEPE")
st.write("Este painel não altera o banco de dados. Ele serve apenas para vermos **exatamente** o que a planilha Excel contém.")

arquivo = st.file_uploader("Suba a planilha gerada pela Secretaria (.xls ou .xlsx)", type=["xls", "xlsx"])

if arquivo:
    with st.spinner("Lendo o arquivo linha por linha..."):
        try:
            xl = pd.ExcelFile(arquivo)
            abas = [a for a in xl.sheet_names if "EM45" in a]
            
            if not abas:
                st.error("Nenhuma aba com 'EM45' encontrada.")
                st.stop()

            dados_totais = []
            
            for aba in abas:
                # Extraindo o nome da turma (Ex: EM45-1IA -> 1º A)
                sigla = aba.split('-')[-1].strip() if '-' in aba else aba.strip()
                turma_formatada = f"{sigla[0]}º {sigla[-1]}" if len(sigla) >= 2 and sigla[0].isdigit() else aba

                df = pd.read_excel(xl, sheet_name=aba, header=0)
                
                # Limpando os nomes das colunas
                df.columns = df.columns.str.strip().str.upper()
                
                # Procurando as colunas de Nome e Situação de forma flexível
                col_nome = [c for c in df.columns if "NOME" in c]
                col_sit = [c for c in df.columns if "SITUA" in c]
                
                if not col_nome:
                    st.warning(f"Ignorando aba {aba}: Coluna de Nome não encontrada.")
                    continue
                    
                nome_col = col_nome[0]
                sit_col = col_sit[0] if col_sit else None
                
                # Lendo os alunos da aba
                for _, row in df.iterrows():
                    nome = str(row[nome_col]).strip().upper()
                    
                    if nome == "NAN" or not nome: 
                        continue
                    
                    # Verifica a situação (se a coluna existir naquela aba)
                    situacao = str(row[sit_col]).strip().upper() if sit_col else "COLUNA NÃO EXISTE NA ABA"
                    
                    dados_totais.append({
                        "Turma": turma_formatada,
                        "Nome do Aluno no Excel": nome,
                        "Situação Lida": situacao,
                        "Aba Original": aba
                    })
            
            df_final = pd.DataFrame(dados_totais)
            
            # ==========================================
            # VISUALIZAÇÃO DOS DADOS
            # ==========================================
            st.success(f"Leitura concluída! O Excel possui **{len(df_final)}** linhas válidas com nomes.")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("Resumo por Turma")
                resumo = df_final.groupby("Turma").size().reset_index(name="Quantidade de Nomes Lidos")
                st.dataframe(resumo, hide_index=True, use_container_width=True)
                
            with col2:
                st.subheader("Verificar Alunos por Sala")
                turma_selecionada = st.selectbox("Escolha a sala para listar os nomes:", ["Todas as Salas"] + sorted(list(df_final["Turma"].unique())))
                
                if turma_selecionada != "Todas as Salas":
                    df_exibir = df_final[df_final["Turma"] == turma_selecionada]
                else:
                    df_exibir = df_final
                    
                st.dataframe(df_exibir, hide_index=True, use_container_width=True)
                
                # Campo de busca para você testar um nome específico
                st.divider()
                st.write("🔍 **Teste Rápido:** Digite o nome de um aluno que a secretaria disse que foi transferido:")
                busca = st.text_input("Buscar nome:")
                if busca:
                    resultado_busca = df_final[df_final["Nome do Aluno no Excel"].str.contains(busca.upper())]
                    if not resultado_busca.empty:
                        st.error(f"⚠️ ACHEI! O aluno **{busca.upper()}** AINDA ESTÁ no Excel gerado pela secretaria. O sistema não vai excluí-lo.")
                        st.dataframe(resultado_busca, hide_index=True)
                    else:
                        st.success(f"O aluno **{busca.upper()}** NÃO está no Excel. O sistema vai excluí-lo perfeitamente.")

        except Exception as e:
            st.error(f"Erro ao ler a planilha: {e}")