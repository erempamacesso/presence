import streamlit as st
import pandas as pd

def exibir_importacao(supabase):
    st.title("📤 Sistema de Sincronização SIGERPAM")
    st.markdown("---")

    # 1. UPLOAD DO ARQUIVO (Disponível para todas as abas)
    arquivo = st.file_uploader("Suba a planilha oficial do SIEPE", type=["xls", "xlsx"])

    if arquivo:
        # --- PROCESSAMENTO INICIAL ---
        try:
            xl = pd.ExcelFile(arquivo)
            abas_turmas = [a for a in xl.sheet_names if "EM45" in a]
            
            dados_lidos = []
            for aba in abas_turmas:
                sigla = aba.split('-')[-1].strip()
                turma_f = f"{sigla[0]}º {sigla[-1]}" if len(sigla) >= 2 else aba
                
                df = pd.read_excel(xl, sheet_name=aba, header=0)
                df.columns = df.columns.str.strip().str.upper()
                
                if 'NOME' in df.columns:
                    df = df.dropna(subset=['NOME'])
                    for _, linha in df.iterrows():
                        nome_limpo = str(linha['NOME']).strip().upper()
                        if nome_limpo and nome_limpo != "NAN":
                            dados_lidos.append({
                                "nome": nome_limpo,
                                "turma": turma_f,
                                "matricula": str(linha.get('MATRÍCULA', linha.get('MATRICULA', ''))).strip(),
                                "data_nascimento": str(linha.get('DATA DE NASCIMENTO', '')),
                                "sexo": str(linha.get('SEXO', ''))[0].upper() if pd.notna(linha.get('SEXO')) else None
                            })
            
            df_excel = pd.DataFrame(dados_lidos).drop_duplicates(subset=['nome'])

            # --- CRIAÇÃO DAS ABAS ---
            tab_conferencia, tab_sincronismo = st.tabs(["📊 1. Conferência por Sala", "🔄 2. Cruzamento e Sincronismo"])

            # ABA 1: CONFERÊNCIA (O que o Raio-X fazia)
            with tab_conferencia:
                st.subheader("Contagem de Alunos por Sala")
                resumo = df_excel.groupby("turma").size().reset_index(name="Total de Alunos")
                st.dataframe(resumo, hide_index=True, width="stretch")
                
                st.divider()
                st.subheader("Lista Detalhada")
                turma_sel = st.selectbox("Selecione a sala para conferir os nomes:", resumo["turma"].unique())
                df_sala = df_excel[df_excel["turma"] == turma_sel].sort_values(by="nome")
                st.write(f"Alunos encontrados na **{turma_sel}**:")
                st.dataframe(df_sala[["nome", "matricula"]], hide_index=True, width="stretch")

            # ABA 2: SINCRONISMO (Ação no Banco)
            with tab_sincronismo:
                st.subheader("Comparação com o Banco de Dados")
                st.write("Clique no botão abaixo para verificar quem entrou e quem saiu.")
                
                if st.button("🔍 Iniciar Cruzamento de Dados", type="primary"):
                    # Busca dados do Supabase
                    res_bd = supabase.table("alunos").select("nome, turma").execute()
                    df_bd = pd.DataFrame(res_bd.data)

                    nomes_excel = set(df_excel['nome'])
                    nomes_bd = set(df_bd['nome'])

                    # Identifica as diferenças
                    saíram = nomes_bd - nomes_excel  # CASO DO ARTHUR CARLINDO
                    entraram = nomes_excel - nomes_bd

                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.error(f"🔴 Saíram/Transferidos ({len(saíram)})")
                        if saíram:
                            df_saíram = df_bd[df_bd['nome'].isin(saíram)]
                            st.dataframe(df_saíram, hide_index=True)
                        else:
                            st.write("Ninguém saiu.")

                    with col2:
                        st.success(f"🟢 Novatos/Entraram ({len(entraram)})")
                        if entraram:
                            df_entraram = df_excel[df_excel['nome'].isin(entraram)]
                            st.dataframe(df_entraram[['nome', 'turma']], hide_index=True)
                        else:
                            st.write("Ninguém novo.")

                    st.divider()
                    
                    # BOTÃO FINAL DE EXECUÇÃO
                    if saíram or entraram:
                        st.warning("⚠️ **Atenção:** Ao confirmar, os nomes na lista vermelha serão removidos do sistema permanentemente.")
                        if st.button("🚀 CONFIRMAR E ATUALIZAR SIGERPAM"):
                            with st.spinner("Limpando transferidos e adicionando novatos..."):
                                # 1. Remove quem saiu
                                for nome_remover in saíram:
                                    supabase.table("alunos").delete().eq("nome", nome_remover).execute()
                                
                                # 2. Upsert (Atualiza todos que sobraram e insere os novos)
                                lista_final = df_excel.to_dict('records')
                                supabase.table("alunos").upsert(lista_final, on_conflict="nome").execute()
                                
                                st.success("🎉 Sincronização concluída com sucesso!")
                                st.balloons()
                    else:
                        st.info("✅ O banco de dados já está idêntico à planilha. Nenhuma ação necessária.")

        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")