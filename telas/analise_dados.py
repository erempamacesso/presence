import streamlit as st
import pandas as pd
import io

def mostrar_tela_analise(supabase, supabase_alunos):
    st.title("📊 Análise de Dados e Notas")
    
    # --- VISÃO GERAL ---
    try:
        res_raw = supabase.table("resultados_provas").select("aluno_id, questao_id, acertou").execute()
        res_alunos_base = supabase_alunos.table("alunos").select("id, turma, nome").execute()
        
        if res_raw.data and res_alunos_base.data:
            df_raw = pd.DataFrame(res_raw.data)
            df_alunos_base = pd.DataFrame(res_alunos_base.data)
            df_raw['aluno_id'] = df_raw['aluno_id'].astype(str)
            df_alunos_base['id'] = df_alunos_base['id'].astype(str)
            
            st.subheader("🎯 Visão Geral")
            col_k1, col_k2 = st.columns(2)
            col_k1.metric("Total de Respostas", len(df_raw))
            col_k2.metric("Alunos Participantes", df_raw['aluno_id'].nunique())
    except Exception as e:
        st.info(f"Aguardando dados de respostas... ({e})")

    st.divider()
    
    # --- DESEMPENHO POR ALUNO E RELATÓRIOS ---
    st.subheader("🏆 Desempenho por Aluno e Relatórios")
    
    try:
        res_p_modelos = supabase.table("modelos_prova").select("id, titulo, valor_questao, questoes_ids").order("id", desc=True).execute()
        
        if res_p_modelos.data:
            provas_dict = {p['titulo']: p for p in res_p_modelos.data}
            prova_nome = st.selectbox("Selecione a Prova para detalhar:", list(provas_dict.keys()))
            
            if prova_nome:
                prova_obj = provas_dict[prova_nome]
                id_prova = prova_obj['id']
                
                # Prevenção de erro caso 'valor_questao' venha vazio (None) do banco
                valor_q_raw = prova_obj.get('valor_questao')
                valor_q = float(valor_q_raw) if valor_q_raw is not None else 1.0

                res_res = supabase.table("resultados_provas").select("*").eq("prova_id", id_prova).execute()
                
                if res_res.data:
                    df_res = pd.DataFrame(res_res.data)
                    df_res['aluno_id'] = df_res['aluno_id'].astype(str)
                    
                    # Converte booleano de acerto para pontuação (1 ou 0)
                    df_res['pontos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)
                    
                    # Agrupa os acertos por aluno
                    df_notas = df_res.groupby('aluno_id').agg(total_acertos=('pontos', 'sum')).reset_index()
                    
                    # Calcula a nota final
                    df_notas['nota_final'] = df_notas['total_acertos'] * valor_q
                    
                    # Busca TODOS os alunos de uma vez (Evita erro de limitação ou tipo no Supabase)
                    res_al = supabase_alunos.table("alunos").select("id, nome, turma").execute()
                    
                    if res_al.data:
                        df_alunos_nomes = pd.DataFrame(res_al.data)
                        df_alunos_nomes['id'] = df_alunos_nomes['id'].astype(str)
                        
                        # Mescla as notas com os dados dos alunos baseados no ID
                        df_tela = pd.merge(df_alunos_nomes, df_notas, left_on="id", right_on="aluno_id")
                        
                        if not df_tela.empty:
                            # Exibe a Tabela na tela
                            st.dataframe(df_tela[["nome", "turma", "total_acertos", "nota_final"]].sort_values("nome"), use_container_width=True)

                            # Exportação para Excel
                            if st.button("📊 Gerar Relatório .XLSX Completo"):
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                    # Cria uma aba no Excel para cada turma
                                    for turma in sorted(df_tela['turma'].unique()):
                                        df_turma = df_tela[df_tela['turma'] == turma].copy()
                                        df_turma.to_excel(writer, sheet_name=f"Turma {turma}", index=False)
                                
                                st.download_button(
                                    label="📥 Baixar Excel", 
                                    data=output.getvalue(), 
                                    file_name=f"Relatorio_{prova_nome}.xlsx",
                                    type="primary"
                                )
                        else:
                            st.warning("Nenhum cruzamento encontrado. Verifique se os alunos desta prova ainda estão matriculados.")
                    else:
                        st.warning("Base de alunos indisponível.")
                else:
                    st.info("Sem respostas para esta avaliação.")
        else:
            st.warning("Nenhuma prova elaborada encontrada.")
            
    except Exception as e:
        st.error(f"⚠️ Ocorreu um erro ao processar a tabela: {e}")