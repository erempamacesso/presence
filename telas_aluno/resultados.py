# telas_aluno/resultados.py
import streamlit as st

# Alteramos a assinatura para aceitar o db_provas e ter cores padrão (default)
def render_suspense(db_provas=None, C_PRIMARY="#00b4d8", C_TEXT_MUTED="#6c757d", C_SECONDARY="#0077b6", C_TEXT="#1e293b"):
    # Garante que o aluno esteja na sessão para não dar erro de chave
    if "aluno" not in st.session_state:
        st.error("Sessão perdida. Por favor, faça login novamente.")
        st.stop()

    aluno = st.session_state.aluno
    st.balloons() 
    st.markdown(f"""
        <div style="text-align: center; margin-top: 3rem;">
            <h1 style="color: {C_PRIMARY}; font-size: 40px; font-weight: bold;">🎉 Avaliação Concluída!</h1>
            <p style="color: {C_TEXT_MUTED}; font-size: 18px; margin-top: 10px;">Parabéns, {aluno['nome']}. Suas respostas foram enviadas e salvas com sucesso!</p>
        </div>
    """, unsafe_allow_html=True)
    st.divider()

    with st.container(border=True):
        st.markdown(f"""
            <div style="text-align: center; padding: 20px;">
                <h2 style="color: {C_SECONDARY}; margin-bottom: 15px; font-size: 26px;">🤫 A nota só é liberada depois, viu Bença!</h2>
                <p style="color: {C_TEXT}; font-size: 18px; line-height: 1.6;">
                    Para manter o suspense e evitar <em>spoilers</em> para os colegas que ainda farão a prova, 
                    <strong>sua nota, o gabarito e o feedback personalizado do Mestre Lardião</strong> 
                    só serão liberados após o encerramento do prazo desta atividade.
                </p>
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    if st.button("⬅️ Voltar para o Portal Pro", type="secondary", use_container_width=True):
        # Em vez de clear (que desloga o aluno), voltamos para a home
        st.session_state.etapa = "home" 
        st.rerun()

def render_revisao(db_provas):
    aluno = st.session_state.aluno
    # Usamos prova_config que é o padrão que o dashboard define
    prova = st.session_state.get('prova_resultado') or st.session_state.get('prova_config')

    if not prova:
        st.error("Dados da prova não encontrados.")
        return

    try:
        res_status = db_provas.table("modelos_prova").select("notas_liberadas").eq("id", prova['id']).single().execute()
        notas_liberadas = res_status.data.get('notas_liberadas', False) if res_status.data else False
    except:
        notas_liberadas = False

    if not notas_liberadas:
        st.subheader(f"✅ Prova Enviada: {prova.get('titulo', 'Simulado')}")
        st.balloons()
        st.markdown(f"""
            <div style="background-color: #f0f7ff; border-left: 5px solid #007bff; border-radius: 10px; padding: 25px; margin-top: 20px;">
                <h3 style="color: #0056b3; margin-top: 0;">🧙‍♂️ O Mestre Lardião está analisando...</h3>
                <p style="font-size: 18px; color: #333;">Suas respostas foram salvas com sucesso no pergaminho sagrado!</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("⬅️ Voltar para Atividades", use_container_width=True):
            st.session_state.etapa = "home"
            st.rerun()
    else:
        # O restante do seu código de revisão está correto e foi mantido
        st.subheader(f"📊 Desempenho: {prova['titulo']}")
        with st.spinner("Carregando sua correção comentada..."):
            try:
                res_detalhes = db_provas.table("resultados_provas").select("*").eq("aluno_id", str(aluno['id'])).eq("prova_id", prova['id']).execute()
                acertos = sum(1 for r in res_detalhes.data if r.get('acertou') == True)
                valor_cada = prova.get('valor_questao', 1.0)
                nota_final = acertos * valor_cada
                
                res_fb = db_provas.table("feedback_ia_alunos").select("diagnostico_pedagogico").eq("aluno_id", str(aluno['id'])).eq("prova_id", prova['id']).execute()
                feedback = res_fb.data[0]['diagnostico_pedagogico'] if res_fb.data else None

                col_nota, col_acerto, col_fb = st.columns([1, 1, 3])
                with col_nota: st.metric("Sua Nota", f"{nota_final:.1f}")
                with col_acerto: st.metric("Acertos", f"{acertos}")
                with col_fb:
                    if feedback: st.info(f"**🧙‍♂️ Mestre Lardião diz:** {feedback}")
                    else: st.caption("Feedback pedagógico sendo processado.")
                st.divider()

                erradas = [r for r in res_detalhes.data if r.get('acertou') == False]
                if not erradas:
                    st.success("✨ **Excepcional! Você gabaritou esta avaliação.**")
                else:
                    st.markdown("#### 🔍 Revisão de Pontos Críticos:")
                    q_ids = [r['questao_id'] for r in erradas]
                    res_questoes = db_provas.table("questoes").select("*").in_("id", q_ids).execute()
                    questoes_dict = {q['id']: q for q in res_questoes.data}

                    for erro in erradas:
                        q = questoes_dict.get(erro['questao_id'])
                        if q:
                            texto_puro = q.get('enunciado', 'Questão sem texto')
                            # Limpeza básica de HTML se houver
                            import re
                            texto_limpo = re.sub('<[^<]+?>', '', str(texto_puro))
                            resumo = (texto_limpo[:65] + '...') if len(texto_limpo) > 65 else texto_limpo
                            
                            with st.expander(f"❌ Erro em: {resumo}", expanded=False):
                                st.write(q.get('enunciado', ''), unsafe_allow_html=True)
                                letra_aluno = erro.get('resposta_aluno') or "?"
                                letra_correta = q.get('resposta_correta', '')

                                c1, c2 = st.columns(2)
                                with c1: st.markdown(f"<span style='color:#d9534f'>❌ **Você marcou:** ({letra_aluno})</span>", unsafe_allow_html=True)
                                with c2: st.markdown(f"<span style='color:#5cb85c'>✅ **O correto era:** ({letra_correta})</span>", unsafe_allow_html=True)

                                just = q.get('justificativas')
                                if just:
                                    if isinstance(just, dict):
                                        txt_erro = str(just.get(letra_aluno, "")).replace("Diagnóstico: ", "")
                                        txt_certa = str(just.get(letra_correta, "")).replace("Diagnóstico: ", "")
                                        msg = f"<b>Por que a ({letra_aluno}) está incorreta:</b> {txt_erro}<br><br><b>Sobre a correta ({letra_correta}):</b> {txt_certa}" if txt_erro else f"<b>Explicação da correta ({letra_correta}):</b> {txt_certa}"
                                    else:
                                        msg = str(just).replace("Diagnóstico: ", "")
                                    st.markdown(f"<div style='background-color: #e7f3fe; border-left: 5px solid #2196F3; padding: 15px; border-radius: 5px; color: #0c5460;'>💡 {msg}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Erro ao processar correção: {e}")
                
        if st.button("⬅️ Voltar para Atividades", use_container_width=True):
            st.session_state.etapa = "home"
            st.rerun()