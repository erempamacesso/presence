import streamlit as st
import pandas as pd
import plotly.express as px

def mostrar_tela_analise(supabase, supabase_alunos):
    st.title("🏆 Desempenho por Aluno e Relatórios")

    # 1. Busca modelos de prova
    res_p = supabase.table("modelos_prova").select("id, titulo, valor_questao").execute()
    
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        prova_selecionada = st.selectbox("Selecione a Prova para Análise:", df_p['titulo'].tolist())
        
        prova_id = df_p[df_p['titulo'] == prova_selecionada]['id'].values[0]
        valor_q = float(df_p[df_p['titulo'] == prova_selecionada]['valor_questao'].values[0])

        # 2. Busca resultados
        res_r = supabase.table("resultados_provas").select("*").eq("prova_id", prova_id).execute()

        if res_r.data:
            df_res = pd.DataFrame(res_r.data)
            df_res['pontos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)

            # --- CÁLCULO DAS NOTAS COM ARREDONDAMENTO 0.5 ---
            df_notas = df_res.groupby('aluno_id').agg(total_acertos=('pontos', 'sum')).reset_index()
            df_notas['nota_final'] = df_notas['total_acertos'] * valor_q
            
            # A Mágica do Arredondamento aplicada aqui!
            df_notas['nota_final'] = (df_notas['nota_final'] * 2).round() / 2

            # 3. Busca nomes dos alunos para exibir na tabela
            res_al = supabase_alunos.table("alunos").select("id, nome, turma").in_("id", df_notas['aluno_id'].tolist()).execute()
            
            if res_al.data:
                df_al = pd.DataFrame(res_al.data)
                df_final = pd.merge(df_notas, df_al, left_on='aluno_id', right_on='id')

                # Exibição dos Gráficos
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Distribuição de Notas")
                    fig_hist = px.histogram(df_final, x="nota_final", nbins=10, 
                                          title="Frequência de Notas",
                                          labels={'nota_final': 'Nota'},
                                          color_discrete_sequence=['#00CC96'])
                    st.plotly_chart(fig_hist, use_container_width=True)

                with col2:
                    st.subheader("Média por Turma")
                    df_media_turma = df_final.groupby('turma')['nota_final'].mean().reset_index()
                    fig_bar = px.bar(df_media_turma, x='turma', y='nota_final', 
                                    title="Média de Notas por Turma",
                                    labels={'nota_final': 'Média'},
                                    color='turma')
                    st.plotly_chart(fig_bar, use_container_width=True)

                # Tabela Final
                st.subheader("Quadro de Notas Detalhado")
                st.dataframe(
                    df_final[['nome', 'turma', 'total_acertos', 'nota_final']].sort_values(by='nome'),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.warning("Ainda não há respostas registradas para esta prova.")
    else:
        st.info("Nenhum modelo de prova encontrado no banco.")