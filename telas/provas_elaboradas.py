import streamlit as st
import pandas as pd
import time
from datetime import datetime

# 👇 Importação do gerador de Word (mantendo sua estrutura original)
try:
    from telas.exportador import gerar_prova_word
except Exception:
    pass

def mostrar_tela_provas_elaboradas(supabase):
    st.title("📂 Gerenciamento de Provas Elaboradas")
    
    # 1. BUSCA TODAS AS PROVAS
    res_m = supabase.table("modelos_prova").select("*").order("id", desc=True).execute()
    
    if not res_m.data:
        st.info("Nenhuma prova elaborada ainda. Vá na aba 'Gerar Modelo de Prova' para criar a primeira!")
        return

    df_provas = pd.DataFrame(res_m.data)
    st.write(f"Total de provas criadas: **{len(df_provas)}**")
    st.divider()
    
    hoje = datetime.now().date()
    
    # Função auxiliar para converter datas do banco
    def converter_data(data_val):
        if pd.isna(data_val) or not str(data_val).strip() or str(data_val).lower() == 'none':
            return None
        try:
            str_data = str(data_val)[:10]
            return datetime.strptime(str_data, "%Y-%m-%d").date()
        except Exception:
            return None

    # 2. LOOP DE EXIBIÇÃO DAS PROVAS
    for _, prova in df_provas.iterrows():
        # Tratamento de valores nulos para evitar erros nos inputs
        valor_q = float(prova.get('valor_questao') or 0.5)
        tempo_max = int(prova.get('tempo_duracao') or 60)
        d_inicio_obj = converter_data(prova.get('data_inicio'))
        d_fim_obj = converter_data(prova.get('data_limite'))
        is_recuperacao = prova.get('recuperacao', False)

        # Container visual da Prova
        with st.container(border=True):
            col_info, col_status = st.columns([3, 1])
            
            with col_info:
                # Badge de Recuperação
                rec_tag = " <span style='background-color:#ef4444; color:white; padding:2px 8px; border-radius:10px; font-size:12px;'>RECUPERAÇÃO</span>" if is_recuperacao else ""
                st.markdown(f"### {prova['titulo']}{rec_tag}", unsafe_allow_html=True)
                st.caption(f"🆔 ID: {prova['id']} | ⏱️ {tempo_max}min | 💎 Valor/Q: {valor_q}")
                st.write(f"📅 **Período:** {d_inicio_obj.strftime('%d/%m/%Y') if d_inicio_obj else '??'} até {d_fim_obj.strftime('%d/%m/%Y') if d_fim_obj else '??'}")

            # --- ÁREA DE EDIÇÃO (EXPANDER) ---
            with st.expander("✏️ Editar Configurações e Datas"):
                with st.form(f"form_edit_{prova['id']}"):
                    c1, c2, c3 = st.columns([2.5, 1, 1.5])
                    novo_titulo = c1.text_input("Título da Prova", value=prova['titulo'])
                    novo_valor = c2.number_input("Valor/Questão", min_value=0.1, value=valor_q, step=0.1)
                    
                    # O Checkbox de Recuperação
                    novo_is_rec = c3.checkbox("É RECUPERAÇÃO? 🎓", value=is_recuperacao, help="Se marcado, apenas alunos com média < 6.0 poderão ver.")

                    d1, d2, d3 = st.columns(3)
                    nova_d_inicio = d1.date_input("Início", value=d_inicio_obj if d_inicio_obj else hoje)
                    nova_d_fim = d2.date_input("Término", value=d_fim_obj if d_fim_obj else hoje)
                    novo_tempo = d3.number_input("Tempo (min)", min_value=10, value=tempo_max)
                    
                    if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                        dados_update = {
                            "titulo": novo_titulo,
                            "valor_questao": float(novo_valor),
                            "data_inicio": nova_d_inicio.strftime("%Y-%m-%d"),
                            "data_limite": nova_d_fim.strftime("%Y-%m-%d"),
                            "tempo_duracao": novo_tempo,
                            "recuperacao": novo_is_rec
                        }
                        try:
                            supabase.table("modelos_prova").update(dados_update).eq("id", prova['id']).execute()
                            st.success("✅ Atualizado!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

            # --- BOTÕES DE AÇÃO ---
            col_b1, col_b2 = st.columns(2)
            
            # Botão para Exportar Word (se a função existir)
            try:
                with col_b1:
                    if st.button(f"📄 Gerar Word (ID {prova['id']})", use_container_width=True):
                        # Chamada para sua função de exportação
                        # gerar_prova_word(supabase, prova['id'])
                        st.info("Função de exportação acionada.")
            except:
                pass

            with col_b2:
                if st.button(f"🗑️ Excluir Prova", key=f"del_{prova['id']}", type="secondary", use_container_width=True):
                    if st.confirm("Tem certeza que deseja apagar esta prova permanentemente?"):
                        supabase.table("modelos_prova").delete().eq("id", prova['id']).execute()
                        st.rerun()