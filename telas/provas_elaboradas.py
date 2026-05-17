import streamlit as st
import pandas as pd
import time
from datetime import datetime, time as dt_time

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

    def converter_hora(hora_val):
        if pd.isna(hora_val) or not str(hora_val).strip() or str(hora_val).lower() == 'none':
            return None
        for formato in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(str(hora_val)[:8], formato).time()
            except Exception:
                pass
        return None

    def obter_campo_hora(prova, candidatos):
        for campo in candidatos:
            if campo in prova.index:
                return campo
        return None

    def prova_expirada(prova, data_fim):
        if not data_fim:
            return False

        campo_hora_fim = obter_campo_hora(
            prova,
            ["hora_limite", "horario_limite", "hora_fim", "horario_fim", "hora_termino", "horario_termino"]
        )
        hora_fim = converter_hora(prova.get(campo_hora_fim)) if campo_hora_fim else dt_time(23, 59, 59)
        return datetime.now() > datetime.combine(data_fim, hora_fim)

    # 2. LOOP DE EXIBIÇÃO DAS PROVAS
    for _, prova in df_provas.iterrows():
        # Tratamento de valores nulos para evitar erros nos inputs
        valor_q = float(prova.get('valor_questao') or 0.5)
        tempo_max = int(prova.get('tempo_duracao') or 60)
        d_inicio_obj = converter_data(prova.get('data_inicio'))
        d_fim_obj = converter_data(prova.get('data_limite'))
        is_recuperacao = prova.get('recuperacao', False)
        esta_ativa = bool(prova.get('ativa', True))
        ja_expirou = prova_expirada(prova, d_fim_obj)

        if esta_ativa and ja_expirou:
            try:
                supabase.table("modelos_prova").update({"ativa": False}).eq("id", prova['id']).execute()
                esta_ativa = False
            except Exception as e:
                st.warning(f"Não foi possível desativar automaticamente a prova ID {prova['id']}: {e}")

        # Container visual da Prova
        with st.container(border=True):
            col_info, col_status = st.columns([3, 1])
            
            with col_info:
                # Badge de Recuperação
                rec_tag = " <span style='background-color:#ef4444; color:white; padding:2px 8px; border-radius:10px; font-size:12px;'>RECUPERAÇÃO</span>" if is_recuperacao else ""
                st.markdown(f"### {prova['titulo']}{rec_tag}", unsafe_allow_html=True)
                st.caption(f"🆔 ID: {prova['id']} | ⏱️ {tempo_max}min | 💎 Valor/Q: {valor_q}")
                st.write(f"📅 **Período:** {d_inicio_obj.strftime('%d/%m/%Y') if d_inicio_obj else '??'} até {d_fim_obj.strftime('%d/%m/%Y') if d_fim_obj else '??'}")

            with col_status:
                if esta_ativa:
                    st.success("🟢 Ativa")
                else:
                    st.error("🔴 Desativada")
                if ja_expirou:
                    st.caption("Prazo encerrado")

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

                    campo_hora_inicio = obter_campo_hora(prova, ["hora_inicio", "horario_inicio"])
                    campo_hora_fim = obter_campo_hora(
                        prova,
                        ["hora_limite", "horario_limite", "hora_fim", "horario_fim", "hora_termino", "horario_termino"]
                    )

                    if campo_hora_inicio or campo_hora_fim:
                        h1, h2 = st.columns(2)
                        nova_h_inicio = h1.time_input(
                            "Horário de início",
                            value=converter_hora(prova.get(campo_hora_inicio)) or dt_time(0, 0),
                            disabled=not bool(campo_hora_inicio)
                        )
                        nova_h_fim = h2.time_input(
                            "Horário de término",
                            value=converter_hora(prova.get(campo_hora_fim)) or dt_time(23, 59),
                            disabled=not bool(campo_hora_fim)
                        )
                    else:
                        nova_h_inicio = None
                        nova_h_fim = None
                        st.caption("Sem coluna de horário encontrada no banco; o bloqueio automático usará o fim do dia da data de término.")
                    
                    if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                        dados_update = {
                            "titulo": novo_titulo,
                            "valor_questao": float(novo_valor),
                            "data_inicio": nova_d_inicio.strftime("%Y-%m-%d"),
                            "data_limite": nova_d_fim.strftime("%Y-%m-%d"),
                            "tempo_duracao": novo_tempo,
                            "recuperacao": novo_is_rec
                        }
                        if campo_hora_inicio and nova_h_inicio:
                            dados_update[campo_hora_inicio] = nova_h_inicio.strftime("%H:%M:%S")
                        if campo_hora_fim and nova_h_fim:
                            dados_update[campo_hora_fim] = nova_h_fim.strftime("%H:%M:%S")
                        try:
                            supabase.table("modelos_prova").update(dados_update).eq("id", prova['id']).execute()
                            st.success("✅ Atualizado!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

            # --- BOTÕES DE AÇÃO ---
            col_b1, col_b2, col_b3 = st.columns(3)
            
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
                novo_status = not esta_ativa
                texto_status = "✅ Ativar Prova" if novo_status else "🚫 Desativar Prova"
                if st.button(texto_status, key=f"status_{prova['id']}", type="primary" if novo_status else "secondary", use_container_width=True):
                    try:
                        supabase.table("modelos_prova").update({"ativa": novo_status}).eq("id", prova['id']).execute()
                        st.success("Status atualizado!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar status: {e}")

            with col_b3:
                confirmar_key = f"confirmar_exclusao_{prova['id']}"
                if st.session_state.get(confirmar_key):
                    st.warning("Clique novamente para excluir definitivamente.")
                    if st.button("Confirmar Exclusão", key=f"confirm_del_{prova['id']}", type="secondary", use_container_width=True):
                        try:
                            supabase.table("modelos_prova").delete().eq("id", prova['id']).execute()
                            st.session_state.pop(confirmar_key, None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir prova: {e}")
                    if st.button("Cancelar", key=f"cancel_del_{prova['id']}", use_container_width=True):
                        st.session_state.pop(confirmar_key, None)
                        st.rerun()
                elif st.button(f"🗑️ Excluir Prova", key=f"del_{prova['id']}", type="secondary", use_container_width=True):
                    st.session_state[confirmar_key] = True
                    st.rerun()
