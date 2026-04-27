import streamlit as st
import pandas as pd
import io
import math

# --- FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE ---
def arredondar_siepe(nota):
    if pd.isna(nota): return nota
    nota = float(nota)
    inteiro = math.floor(nota)
    decimal = round((nota - inteiro) * 10)
    if decimal in [0, 1]: return float(inteiro)
    elif decimal in [2, 3, 4, 5, 6]: return float(inteiro + 0.5)
    else: return float(inteiro + 1)

def mostrar_tela_analise(supabase, supabase_alunos):
    st.markdown("## 📊 Análise de Dados e Notas")
    
    try:
        # 1. BUSCA DE DADOS MESTRE (Modelos e Alunos)
        res_p_modelos = supabase.table("modelos_prova").select("id, titulo, valor_questao").order("id", desc=True).execute()
        res_alunos_base = supabase_alunos.table("alunos").select("id, turma, nome").execute()
        
        if not res_p_modelos.data:
            st.warning("Nenhuma prova encontrada no banco de dados.")
            return

        # SELETOR DE PROVA
        provas_dict = {p['titulo']: p for p in res_p_modelos.data}
        prova_nome = st.selectbox("🎯 Selecione a Prova para Monitorar:", list(provas_dict.keys()))
        prova_obj = provas_dict[prova_nome]
        id_prova = prova_obj['id']

        # 2. BUSCA DE RESULTADOS (Cálculo antes de mostrar qualquer gráfico)
        res_res = supabase.table("resultados_provas").select("*").eq("prova_id", id_prova).execute()
        
        if not res_res.data or not res_alunos_base.data:
            st.info("ℹ️ Ainda não existem envios para esta prova.")
            return

        # --- PROCESSAMENTO DE DADOS (O Coração do Dashboard) ---
        df_res = pd.DataFrame(res_res.data)
        df_alunos = pd.DataFrame(res_alunos_base.data)
        
        # Ajuste de tipos para o Merge
        df_res['aluno_id'] = df_res['aluno_id'].astype(str)
        df_alunos['id'] = df_alunos['id'].astype(str)

        # Cálculo de pontos e notas
        valor_q = float(prova_obj.get('valor_questao', 1.0))
        df_res['pontos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)
        
        # Agrupa por aluno para somar acertos
        df_notas = df_res.groupby('aluno_id').agg(total_acertos=('pontos', 'sum')).reset_index()
        df_notas['nota_final'] = (df_notas['total_acertos'] * valor_q).apply(arredondar_siepe)
        
        # Criação do dataframe principal (df_final agora existe ANTES dos gráficos)
        df_final = pd.merge(df_alunos, df_notas, left_on="id", right_on="aluno_id")

        if df_final.empty:
            st.warning("Não foi possível cruzar os dados dos alunos com os resultados.")
            return

        # ---------------------------------------------------------
        # 3. ÁREA DE GRÁFICOS (Agora funciona sem erro!)
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("📈 Desempenho e Progresso por Turma")
        
        g1, g2 = st.columns(2)
        
        with g1:
            # Média de notas por turma
            df_media = df_final.groupby('turma')['nota_final'].mean().reset_index()
            st.write("**Média de Notas**")
            st.bar_chart(data=df_media, x='turma', y='nota_final', color="#2b83ba")
            st.caption("Desempenho acadêmico médio de cada turma.")

        with g2:
            # Total de alunos que fizeram por turma
            df_participacao = df_final.drop_duplicates(subset=['aluno_id']).groupby('turma').size().reset_index(name='total')
            st.write("**Total de Participantes**")
            st.bar_chart(data=df_participacao, x='turma', y='total', color="#abdda4")
            st.caption("Quantidade de alunos que concluíram a prova.")

        st.markdown("---")

        # ---------------------------------------------------------
        # 4. DIVISÃO EM COLUNAS (Tabela vs Monitoramento Lateral)
        # ---------------------------------------------------------
        col_tabela, col_monitor = st.columns([2, 1], gap="large")

        with col_tabela:
            st.subheader("📋 Notas Detalhadas")
            st.dataframe(
                df_final[["nome", "turma", "total_acertos", "nota_final"]].sort_values(["turma", "nome"]),
                use_container_width=True,
                height=450,
                column_config={
                    "nome": "Estudante",
                    "turma": "Turma",
                    "total_acertos": "Acertos",
                    "nota_final": st.column_config.NumberColumn("Nota Final (SIEPE)", format="%.1f")
                }
            )
            
            # Exportação Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                for turma in sorted(df_final['turma'].unique()):
                    df_turma = df_final[df_final['turma'] == turma].copy()
                    df_turma.to_excel(writer, sheet_name=f"Turma {turma}", index=False)
            
            st.download_button(
                label="📥 Baixar Relatório Completo (.xlsx)",
                data=output.getvalue(),
                file_name=f"Notas_{prova_nome}.xlsx",
                type="primary"
            )

        with col_monitor:
            st.subheader("👥 Status de Envio")
            # Lista estilizada igual à sua imagem de referência
            stats = df_final.drop_duplicates(subset=['aluno_id']).groupby('turma').size().reset_index(name='qtd')
            
            for _, row in stats.iterrows():
                st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #2b83ba; margin-bottom: 10px;">
                        <span style="color: #6c757d; font-size: 14px;">TURMA {row['turma']}</span><br>
                        <span style="font-size: 22px; font-weight: bold; color: #1e293b;">{row['qtd']} Alunos Concluíram</span>
                    </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ Ocorreu um erro no processamento: {e}")