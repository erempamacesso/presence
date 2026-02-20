import streamlit as st
import pandas as pd

def exibir_importacao(supabase):
    st.title("📤 Importação de Dados (Padrão SIGPAM)")
    
    # Instruções Visuais para o Usuário
    with st.expander("📄 Ver Padrão de Arquivo Aceito"):
        st.write("O arquivo deve ser **CSV** ou **Excel** com as colunas:")
        st.code("nome,turma")
        st.write("Exemplo: \nJOAO SILVA, 1º A")

    arquivo = st.file_uploader("Suba seu arquivo padronizado", type=["csv", "xlsx"])
    
    if arquivo:
        if st.button("🚀 Iniciar Importação"):
            try:
                # Lendo o arquivo seguindo o padrão
                if arquivo.name.endswith('.csv'):
                    df = pd.read_csv(arquivo)
                else:
                    df = pd.read_excel(arquivo)

                # Padroniza os nomes das colunas (remove espaços e deixa minúsculo)
                df.columns = [str(c).lower().strip() for c in df.columns]

                # Validação de Segurança: O arquivo tem as colunas certas?
                colunas_necessarias = ['nome', 'turma']
                if not all(c in df.columns for c in colunas_necessarias):
                    st.error(f"❌ Erro no formato! O arquivo precisa ter as colunas: {', '.join(colunas_necessarias)}")
                    st.stop()

                progresso = st.progress(0)
                status = st.empty()
                cadastrados = 0
                pulados = 0
                total = len(df)

                for i, row in df.iterrows():
                    nome_aluno = str(row['nome']).upper().strip()
                    turma_aluno = str(row['turma']).upper().strip()

                    if nome_aluno and nome_aluno != "NAN":
                        # 🔍 VERIFICAÇÃO DE DUPLICIDADE (Pelo Nome)
                        existe = supabase.table("alunos").select("id").eq("nome", nome_aluno).execute()
                        
                        if not existe.data:
                            supabase.table("alunos").insert({
                                "nome": nome_aluno, 
                                "turma": turma_aluno
                            }).execute()
                            cadastrados += 1
                        else:
                            pulados += 1
                    
                    progresso.progress((i + 1) / total)
                    status.text(f"Processando: {i+1} de {total}")

                st.success(f"✅ Importação Concluída!")
                st.write(f"- Novos alunos: **{cadastrados}**")
                st.write(f"- Alunos já existentes (pulados): **{pulados}**")
                
            except Exception as e:
                st.error(f"❌ Ocorreu um erro: {e}")
