import streamlit as st
import pandas as pd

def exibir_painel_aee(supabase):
    st.title("🧩 Painel AEE & Inclusão")
    st.caption("Gestão de Estudantes com Especificidades e Investigação Pedagógica")
    st.markdown("---")

    # 1. BUSCA DO ALUNO
    st.subheader("🔍 Localizar Estudante")
    
    # Buscamos todos os alunos para o selectbox
    try:
        res = supabase.table("alunos").select("id, nome, turma, status_aee, cid, relatorio_aee").order("nome").execute()
        df_alunos = pd.DataFrame(res.data)
        
        if not df_alunos.empty:
            # Criar uma label bonita para o select: "NOME - TURMA"
            df_alunos['label'] = df_alunos['nome'] + " (" + df_alunos['turma'] + ")"
            aluno_selecionado = st.selectbox("Selecione o aluno para atualizar prontuário:", 
                                             options=df_alunos['id'].tolist(),
                                             format_func=lambda x: df_alunos[df_alunos['id'] == x]['label'].values[0])
            
            # Pegar dados atuais do aluno selecionado
            dados_atuais = df_alunos[df_alunos['id'] == aluno_selecionado].iloc[0]
            
            st.markdown("---")
            
            # 2. FORMULÁRIO DE ATUALIZAÇÃO
            col1, col2 = st.columns(2)
            
            with col1:
                novo_status = st.selectbox(
                    "🚦 Status de Acompanhamento:",
                    options=["Nenhum", "Em Investigação", "Laudo Confirmado"],
                    index=["Nenhum", "Em Investigação", "Laudo Confirmado"].index(dados_atuais['status_aee']) if dados_atuais['status_aee'] in ["Nenhum", "Em Investigação", "Laudo Confirmado"] else 0
                )
                
                novo_cid = st.text_input("🆔 Código CID (Ex: F84.0):", value=dados_atuais['cid'] if dados_atuais['cid'] else "")

            with col2:
                st.info(f"**Aluno:** {dados_atuais['nome']}\n\n**Turma:** {dados_atuais['turma']}")

            novo_relatorio = st.text_area("📝 Relatório Médico / Observações Pedagógicas:", 
                                          value=dados_atuais['relatorio_aee'] if dados_atuais['relatorio_aee'] else "",
                                          height=150)

            if st.button("💾 Salvar Prontuário AEE", use_container_width=True):
                try:
                    supabase.table("alunos").update({
                        "status_aee": novo_status,
                        "cid": novo_cid,
                        "relatorio_aee": novo_relatorio
                    }).eq("id", aluno_selecionado).execute()
                    
                    st.success(f"Prontuário de {dados_atuais['nome']} atualizado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

        else:
            st.warning("Nenhum aluno cadastrado no banco de dados.")
            
    except Exception as e:
        st.error(f"Erro ao carregar lista de alunos: {e}")

    # 3. RESUMO DO QUADRO DE INCLUSÃO
    st.markdown("---")
    st.subheader("📋 Quadro Resumo de Inclusão")
    
    # Mostrar quem já está marcado para facilitar a gestão
    df_resumo = df_alunos[df_alunos['status_aee'] != "Nenhum"].copy()
    if not df_resumo.empty:
        st.dataframe(df_resumo[['nome', 'turma', 'status_aee', 'cid']], 
                     use_container_width=True, 
                     hide_index=True)
    else:
        st.info("Nenhum aluno em acompanhamento especial no momento.")
