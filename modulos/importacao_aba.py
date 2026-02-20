import streamlit as st
import pandas as pd

def exibir_importacao(supabase):
    st.title("📤 Importação de Dados")
    st.info("Utilize esta tela apenas para cargas em massa no início do período letivo.")
    
    arquivo = st.file_uploader("Selecione a planilha (Excel ou CSV)", type=["csv", "xlsx"])
    if arquivo:
        if st.button("Processar e Salvar no Banco"):
            try:
                df = pd.read_csv(arquivo) if arquivo.name.endswith('.csv') else pd.read_excel(arquivo)
                df.columns = [c.lower().strip() for c in df.columns]
                
                progresso = st.progress(0)
                count = 0
                for i, row in df.iterrows():
                    nome = str(row['nome']).upper().strip()
                    turma = f"{row['serie']} {row['turma']}".strip()
                    # Verifica se já existe para não duplicar
                    existe = supabase.table("alunos").select("id").eq("nome", nome).execute()
                    if not existe.data:
                        supabase.table("alunos").insert({"nome": nome, "turma": turma}).execute()
                        count += 1
                    progresso.progress((i + 1) / len(df))
                st.success(f"Sucesso! {count} novos alunos cadastrados.")
            except Exception as e: st.error(f"Erro no processamento: {e}")
