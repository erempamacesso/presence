import streamlit as st
import pandas as pd
import time
from datetime import datetime

def mostrar_tela_provas_elaboradas(supabase):
    st.title("📂 Gerenciamento de Provas Elaboradas")
    
    # Busca todas as provas cadastradas no banco
    res_m = supabase.table("modelos_prova").select("*").order("id", desc=True).execute()
    
    if res_m.data:
        df_provas = pd.DataFrame(res_m.data)
        st.write(f"Total de provas criadas: **{len(df_provas)}**")
        st.divider()
        
        hoje = datetime.now().date()
        
        # Função ROBUSTA para converter a data vinda do banco e evitar o "Não definida"
        def converter_data(data_val):
            if pd.isna(data_val) or not str(data_val).strip() or str(data_val).lower() == 'none':
                return None
            try:
                # Pega os primeiros 10 caracteres (YYYY-MM-DD)
                str_data = str(data_val)[:10]
                return datetime.strptime(str_data, "%Y-%m-%d").date()
            except Exception:
                return None
        
        # Lista cada prova em um "cartão" (container)
        for index, prova in df_provas.iterrows():
            is_ativa = prova.get('ativa', False)
            status_texto = "🟢 ATIVA (Aberta para os alunos)" if is_ativa else "🔴 INATIVA (Fechada)"
            
            # Cálculos básicos
            questoes_ids = prova.get('questoes_ids')
            qtd_questoes = len(questoes_ids) if isinstance(questoes_ids, list) else 0 
            valor_q = float(prova.get('valor_questao', 0))
            valor_total = qtd_questoes * valor_q
            
            # Buscando tempo máximo
            tempo_bd = prova.get('tempo_maximo', 60)
            try:
                tempo_max = int(tempo_bd)
            except:
                tempo_max = 60
            
            # --- AJUSTE DAS COLUNAS REAIS ---
            # Lendo 'data_inicio' e 'data_limite' conforme sua tabela
            d_inicio_obj = converter_data(prova.get('data_inicio'))
            d_fim_obj = converter_data(prova.get('data_limite'))

            # Formatação BR para exibição no Card
            str_inicio_br = d_inicio_obj.strftime("%d/%m/%Y") if d_inicio_obj else "Não definida"
            str_fim_br = d_fim_obj.strftime("%d/%m/%Y") if d_fim_obj else "Não definida"

            with st.container(border=True):
                st.subheader(f"📝 {prova.get('titulo', 'Sem título')}")
                
                # Exibição de Informações
                c_info1, c_info2 = st.columns(2)
                with c_info1:
                    st.write(f"**Status:** {status_texto}")
                    st.write(f"**Questões:** {qtd_questoes}  |  **Valor de cada:** {valor_q:.2f}  |  **Valor Total:** {valor_total:.2f}")
                with c_info2:
                    st.write(f"📅 **Início:** {str_inicio_br}")
                    st.write(f"📅 **Término:** {str_fim_br}")
                    st.write(f"⏱️ **Tempo Máximo:** {tempo_max} minutos")

                # Botões de Ação Rápida
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.write("") 
                    btn_status = "🔴 Desativar Prova" if is_ativa else "🟢 Ativar Prova"
                    if st.button(btn_status, key=f"btn_s_{prova['id']}", use_container_width=True):
                        novo_status = not is_ativa
                        try:
                            supabase.table("modelos_prova").update({"ativa": novo_status}).eq("id", prova['id']).execute()
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao mudar status: {e}")
                            
                with c2:
                    st.write("") 
                    if st.button("🗑️ Excluir Prova", key=f"del_p_{prova['id']}", type="primary", use_container_width=True):
                        try:
                            supabase.table("resultados_provas").delete().eq("prova_id", prova['id']).execute()
                            supabase.table("modelos_prova").delete().eq("id", prova['id']).execute()
                            st.success("Prova excluída com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")
                
                # --- ÁREA DE EDIÇÃO (SANFONA) ---
                with st.expander("✏️ Editar Configurações da Prova"):
                    with st.form(f"form_edit_{prova['id']}"):
                        col_t1, col_t2 = st.columns([3, 1])
                        novo_titulo = col_t1.text_input("Título da Prova", value=prova.get('titulo', ''))
                        novo_valor = col_t2.number_input("Valor por Questão", min_value=0.1, value=valor_q, step=0.1)
                        
                        col_d1, col_d2, col_d3 = st.columns(3)
                        
                        nova_d_inicio = col_d1.date_input("Data de Início", value=d_inicio_obj if d_inicio_obj else hoje, format="DD/MM/YYYY")
                        nova_d_fim = col_d2.date_input("Data de Término", value=d_fim_obj if d_fim_obj else hoje, format="DD/MM/YYYY")
                        novo_tempo = col_d3.number_input("Tempo Máx (minutos)", min_value=10, value=tempo_max, step=5)
                        
                        submit_edit = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
                        
                        if submit_edit:
                            # --- SALVANDO COM OS NOMES CORRETOS DAS COLUNAS ---
                            dados_update = {
                                "titulo": novo_titulo,
                                "valor_questao": float(novo_valor),
                                "data_inicio": nova_d_inicio.strftime("%Y-%m-%d"),
                                "data_limite": nova_d_fim.strftime("%Y-%m-%d"),
                                "tempo_maximo": novo_tempo
                            }
                            try:
                                supabase.table("modelos_prova").update(dados_update).eq("id", prova['id']).execute()
                                st.success("✅ Configurações atualizadas com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao atualizar: {e}")
    else:
        st.info("Nenhuma prova elaborada ainda. Vá na aba 'Gerar Modelo de Prova' para criar a primeira!")