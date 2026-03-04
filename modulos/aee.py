import streamlit as st
import pandas as pd

def exibir_painel_aee(supabase):
    st.title("🧩 Painel AEE & Inclusão")
    st.caption("Gestão de Estudantes com Especificidades e Investigação Pedagógica")
    st.markdown("---")

    # 1. BUSCA E FILTRO POR TURMA
    try:
        # Buscamos os dados base
        res = supabase.table("alunos").select("id, nome, turma, status_aee, cid, relatorio_aee").order("nome").execute()
        df_alunos = pd.DataFrame(res.data)
        
        if not df_alunos.empty:
            # --- FILTRO POR TURMA (ST.PILLS) ---
            lista_turmas = sorted(df_alunos['turma'].unique().tolist())
            turma_selecionada = st.pills("📍 Filtrar por Turma:", options=lista_turmas)
            
            if turma_selecionada:
                # Filtra o dataframe apenas pela turma clicada
                df_filtrado = df_alunos[df_alunos['turma'] == turma_selecionada].copy()
                
                st.subheader(f"🔍 Estudantes da Turma: {turma_selecionada}")
                
                # Selectbox agora só mostra alunos daquela turma
                aluno_selecionado = st.selectbox(
                    "Selecione o aluno para atualizar prontuário:", 
                    options=df_filtrado['id'].tolist(),
                    format_func=lambda x: df_filtrado[df_filtrado['id'] == x]['nome'].values[0]
                )
                
                # Pegar dados atuais do aluno selecionado
                dados_atuais = df_filtrado[df_filtrado['id'] == aluno_selecionado].iloc[0]
                
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

                    # --- TRADUTOR DE CID EM PORTUGUÊS ---
                    if novo_cid:
                        dic_cid_pt = {
                            "F84.0": "Autismo Infantil",
                            "F84": "Transtornos Globais do Desenvolvimento",
                            "F90.0": "TDAH (Distúrbio da Atividade e Atenção)",
                            "F90": "TDAH (Transtornos Hipercinéticos)",
                            "F91.2": "Transtorno de Conduta Socializado",
                            "F91": "Distúrbios de Conduta",
                            "F70": "Retardo Mental Leve",
                            "F71": "Retardo Mental Moderado",
                            "F79": "Retardo Mental Não Especificado",
                            "G40": "Epilepsia",
                            "F30": "Episódio Maníaco / Hipomania",
                            "F41": "Transtorno de Ansiedade",
                            "F89": "Atraso no Desenvolvimento Psicológico",
                        }
                        
                        busca = novo_cid.upper().strip().replace(".", "")
                        resultado = None
                        for cod, desc in dic_cid_pt.items():
                            if cod.replace(".", "") in busca:
                                resultado = desc
                                break
                        
                        if resultado:
                            st.success(f"✅ **Diagnóstico:** {resultado}")
                    # -----------------------------------

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
                st.info("👆 Selecione uma turma acima para listar os alunos.")

        else:
            st.warning("Nenhum aluno cadastrado no banco de dados.")
            
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

    # 3. RESUMO DO QUADRO DE INCLUSÃO (ORDENADO POR TURMA)
    st.markdown("---")
    st.subheader("📋 Quadro Resumo de Inclusão")
    
    if 'df_alunos' in locals() and not df_alunos.empty:
        # Filtramos quem não é "Nenhum" e ordenamos primeiro por TURMA e depois por NOME
        df_resumo = df_alunos[df_alunos['status_aee'] != "Nenhum"].copy()
        df_resumo = df_resumo.sort_values(by=['turma', 'nome'])
        
        if not df_resumo.empty:
            st.dataframe(df_resumo[['turma', 'nome', 'status_aee', 'cid']], 
                         use_container_width=True, 
                         hide_index=True)
        else:
            st.info("Nenhum aluno em acompanhamento especial no momento.")
