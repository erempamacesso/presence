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
    # Layout de página larga já definido no app.py, mas garantimos aqui
    st.markdown("## 📊 Análise de Dados e Notas")
    
    try:
        # 1. BUSCA DE DADOS INICIAIS
        res_p_modelos = supabase.table("modelos_prova").select("id, titulo, valor_questao").order("id", desc=True).execute()
        res_alunos_base = supabase_alunos.table("alunos").select("id, turma, nome").execute()
        
        if not res_p_modelos.data:
            st.warning("Nenhuma prova encontrada.")
            return

        # SELETOR DE PROVA (Igual à imagem)
        provas_dict = {p['titulo']: p for p in res_p_modelos.data}
        prova_nome = st.selectbox("🎯 Selecione a Prova para Monitorar:", list(provas_dict.keys()))
        prova_obj = provas_dict[prova_nome]
        id_prova = prova_obj['id']

        # ---------------------------------------------------------
        # ESPAÇO PARA GRÁFICOS (Largura Total)
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # ESPAÇO PARA GRÁFICOS (Agora com Lógica Real)
        # ---------------------------------------------------------
        st.markdown("---")
        container_graficos = st.container()
        with container_graficos:
            if not df_final.empty:
                st.subheader("📈 Desempenho Comparativo entre Turmas")
                
                # Criamos duas colunas para os gráficos ficarem lado a lado
                g1, g2 = st.columns(2)
                
                with g1:
                    # Gráfico 1: Média de Nota Final por Turma
                    media_notas = df_final.groupby('turma')['nota_final'].mean().reset_index()
                    st.write("**Média de Notas (0 a 10)**")
                    st.bar_chart(data=media_notas, x='turma', y='nota_final', color="#2b83ba")
                
                with g2:
                    # Gráfico 2: Média de Acertos por Turma
                    media_acertos = df_final.groupby('turma')['total_acertos'].mean().reset_index()
                    st.write("**Média de Acertos (Quantidade)**")
                    st.area_chart(data=media_acertos, x='turma', y='total_acertos', color="#abdda4")
            else:
                st.info("Gráficos ficarão disponíveis assim que houver dados de alunos.")
        st.markdown("---")

        # ---------------------------------------------------------
        # DIVISÃO EM COLUNAS (Notas vs Monitoramento)
        # ---------------------------------------------------------
        col_tabela, col_monitor = st.columns([2, 1], gap="large")

        # Busca dados de resultados para a prova selecionada
        res_res = supabase.table("resultados_provas").select("*").eq("prova_id", id_prova).execute()
        
        if res_res.data and res_alunos_base.data:
            df_res = pd.DataFrame(res_res.data)
            df_alunos = pd.DataFrame(res_alunos_base.data)
            
            # Garantindo que IDs sejam strings para o merge
            df_res['aluno_id'] = df_res['aluno_id'].astype(str)
            df_alunos['id'] = df_alunos['id'].astype(str)

            # --- PROCESSAMENTO DE NOTAS ---
            valor_q = float(prova_obj.get('valor_questao', 1.0))
            df_res['pontos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)
            df_notas = df_res.groupby('aluno_id').agg(total_acertos=('pontos', 'sum')).reset_index()
            df_notas['nota_final'] = (df_notas['total_acertos'] * valor_q).apply(arredondar_siepe)
            
            # Cruzamento Final
            df_final = pd.merge(df_alunos, df_notas, left_on="id", right_on="aluno_id")

            # COLUNA ESQUERDA: NOTAS DETALHADAS
            with col_tabela:
                st.subheader("📋 Notas Detalhadas")
                st.dataframe(
                    df_final[["nome", "turma", "total_acertos", "nota_final"]].sort_values(["turma", "nome"]),
                    use_container_width=True,
                    height=400,
                    column_config={
                        "nome": "Nome do Aluno",
                        "turma": "Turma",
                        "total_acertos": "Acertos",
                        "nota_final": st.column_config.NumberColumn("Nota Final", format="%.1f")
                    }
                )
                
                # Botão de Relatório logo abaixo da tabela
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    for turma in sorted(df_final['turma'].unique()):
                        df_turma = df_final[df_final['turma'] == turma].copy()
                        df_turma.to_excel(writer, sheet_name=f"Turma {turma}", index=False)
                
                st.download_button(
                    label="📥 Gerar Relatório .XLSX Completo",
                    data=output.getvalue(),
                    file_name=f"Relatorio_{prova_nome}.xlsx",
                    type="secondary"
                )

            # COLUNA DIREITA: MONITORAMENTO DE PARTICIPAÇÃO
            with col_monitor:
                st.subheader("👥 Monitoramento por Turma")
                
                # Agrupa por turma para contar participantes únicos
                df_participantes = df_final.drop_duplicates(subset=['aluno_id'])
                stats_turma = df_participantes.groupby('turma').size().reset_index(name='qtd')
                
                # Estilização da lista de turmas
                for _, row in stats_turma.iterrows():
                    st.markdown(f"""
                        <div style="border-bottom: 1px solid #e6e9ef; padding: 10px 0;">
                            <small style="color: #6c757d;">Turma {row['turma']}</small><br>
                            <span style="font-size: 24px; font-weight: bold;">{row['qtd']} Alunos</span>
                        </div>
                    """, unsafe_allow_html=True)
                
                if stats_turma.empty:
                    st.info("Nenhum registro encontrado.")

        else:
            st.info("Aguardando envios de alunos para esta prova...")

    except Exception as e:
        st.error(f"Erro ao carregar o layout: {e}")