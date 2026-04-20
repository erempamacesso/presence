import streamlit as st
import pandas as pd
import time

def mostrar_tela_provas_elaboradas(supabase):
    st.title("📂 Gerenciamento de Provas Elaboradas")
    
    # Busca todas as provas cadastradas no banco
    res_m = supabase.table("modelos_prova").select("*").order("id", desc=True).execute()
    
    if res_m.data:
        df_provas = pd.DataFrame(res_m.data)
        st.write(f"Total de provas criadas: **{len(df_provas)}**")
        st.divider()
        
        # Lista cada prova em um "cartão" (container)
        for index, prova in df_provas.iterrows():
            # Define cor e texto do status
            is_ativa = prova.get('ativa', False)
            status_texto = "🟢 ATIVA (Aberta para os alunos)" if is_ativa else "🔴 INATIVA (Fechada)"
            
            # Calcula dados básicos
            questoes_ids = prova.get('questoes_ids')
            # Garante que seja uma lista para contar, mesmo se vier None do banco
            qtd_questoes = len(questoes_ids) if isinstance(questoes_ids, list) else 0 
            
            valor_q = float(prova.get('valor_questao', 0))
            valor_total = qtd_questoes * valor_q
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1.2])
                
                with c1:
                    st.subheader(f"📝 {prova['titulo']}")
                    st.write(f"**Quantidade:** {qtd_questoes} questões | **Por questão:** {valor_q} pts | **Total:** {valor_total:.1f} pts")
                    st.markdown(f"**Status atual:** {status_texto}")
                
                with c2:
                    st.write("") # Espaçamento
                    # Botão para ativar/desativar a prova
                    texto_btn = "⏸️ Desativar" if is_ativa else "▶️ Ativar"
                    if st.button(texto_btn, key=f"tog_{prova['id']}", use_container_width=True):
                        novo_status = not is_ativa
                        try:
                            supabase.table("modelos_prova").update({"ativa": novo_status}).eq("id", prova['id']).execute()
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao mudar status: {e}")
                            
                with c3:
                    st.write("") # Espaçamento
                    # Botão para excluir a prova
                    if st.button("🗑️ Excluir Prova", key=f"del_p_{prova['id']}", type="primary", use_container_width=True):
                        try:
                            # 1. Primeiro apagamos os resultados dessa prova (se houver) para evitar erros de dependência
                            supabase.table("resultados_provas").delete().eq("prova_id", prova['id']).execute()
                            # 2. Depois apagamos o modelo da prova
                            supabase.table("modelos_prova").delete().eq("id", prova['id']).execute()
                            
                            st.success("Prova excluída com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")
    else:
        st.info("Nenhuma prova elaborada ainda. Vá na aba 'Gerar Modelo de Prova' para criar a primeira!")