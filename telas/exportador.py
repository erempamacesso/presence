import streamlit as st
import pandas as pd
import time
from datetime import datetime

# === TENTATIVA ROBUSTA DE IMPORTAÇÃO ===
erro_gerador = None
try:
    from exportador import gerar_prova_word
except ImportError:
    try:
        from telas.exportador import gerar_prova_word
    except Exception as e:
        erro_gerador = str(e)
except Exception as e:
    erro_gerador = str(e)

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
            questoes_ids = prova.get('questoes_ids', [])
            qtd_questoes = len(questoes_ids) if isinstance(questoes_ids, list) else 0 
            valor_q = float(prova.get('valor_questao', 0))
            valor_total = qtd_questoes * valor_q
            
            # Buscando tempo máximo
            tempo_bd = prova.get('tempo_duracao', 60)
            try:
                tempo_max = int(tempo_bd)
            except:
                tempo_max = 60
            
            # --- AJUSTE DAS COLUNAS REAIS ---
            d_inicio_obj = converter_data(prova.get('data_inicio'))
            d_fim_obj = converter_data(prova.get('data_limite'))

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
                
                # ==========================================
                # BOTÃO DE DOWNLOAD (.DOCX) - COLUNA 3
                # ==========================================
                with c3:
                    st.write("")
                    if qtd_questoes > 0:
                        try:
                            # 1. Puxa as questões do banco
                            res_q = supabase.table("questoes").select("*").in_("id", questoes_ids).execute()
                            
                            if not res_q.data:
                                st.error("Erro: Nenhuma questão encontrada no banco.")
                                st.button("📄 Baixar Prova", disabled=True, key=f"d_vaz_{prova['id']}", use_container_width=True)
                            else:
                                # 2. Tenta forçar a importação bem na hora de criar o botão
                                try:
                                    try:
                                        from telas.exportador import gerar_prova_word
                                    except ImportError:
                                        from exportador import gerar_prova_word
                                        
                                    arquivo_docx = gerar_prova_word(prova.get('titulo', 'Prova'), res_q.data)
                                    
                                    st.download_button(
                                        label="📄 Baixar Prova (.docx)",
                                        data=arquivo_docx,
                                        file_name=f"Prova_{prova.get('titulo', 'Impressao')}.docx",
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        key=f"down_word_{prova['id']}",
                                        use_container_width=True
                                    )
                                except Exception as erro_fatal:
                                    # SE DER ERRO NO MOTOR, VAI FICAR VERMELHO AQUI!
                                    st.error(f"Erro fatal no motor: {erro_fatal}")
                                    st.button("📄 Baixar Prova", disabled=True, key=f"d_err_{prova['id']}", use_container_width=True)
                                    
                        except Exception as e:
                            st.error(f"Falha no Supabase: {e}")
                    else:
                        st.button("📄 Baixar Prova", disabled=True, key=f"d_sem_q_{prova['id']}", help="Prova sem questões.", use_container_width=True)