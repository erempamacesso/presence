# telas_aluno/execucao_prova.py
import streamlit as st
import random
from datetime import datetime, timedelta
import re

def render_instrucoes(db_provas):
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    st.header(f"👋 Preparado, {aluno['nome']}?")
    
    with st.container(border=True):
        st.subheader(f"📝 {prova['titulo']}")
        st.write(f"Série: {prova['serie']} | Tempo de Execução: **{prova['tempo_duracao']} minutos**")
        
        st.markdown(f"""
            **Instruções Importantes Pro:**
            1. Você terá estatisticamente {prova['tempo_duracao']} minutos para concluir após clicar no botão abaixo.
            2. Não atualize ou feche o navegador AVALARDIAO durante a prova, ou seu progresso será perdido.
            3. Responda todas as questões e clique em 'Enviar' ao final.
        """)
        
        if st.button("ESTOU PRONTO, INICIAR PROVA AGORA", type="primary", use_container_width=True, key="btn_start"):
            with st.spinner("Gerando sua avaliação única e randomizada..."):
                st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
                
                ids = prova.get('questoes_ids', [])
                res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
                pool_questoes = res_q.data
                
                random.seed(str(aluno['id']))
                random.shuffle(pool_questoes)
                
                n_sorteio = prova.get('qtd_sorteio', len(pool_questoes))
                questoes_sorteadas = pool_questoes[:n_sorteio]
                
                st.session_state.questoes = questoes_sorteadas
                st.session_state.etapa = "em_prova"
                st.rerun()

def render_prova(db_provas, C_PRIMARY):
    @st.fragment(run_every="1s")
    def render_cronometro():
        restante = st.session_state.tempo_final - datetime.now()
        segs = int(restante.total_seconds())
        if segs <= 0:
            st.error("⌛ TEMPO ESGOTADO!")
            st.stop()
        mins, secs = divmod(segs, 60)
        cor = "#FF4B4B" if segs < 300 else C_PRIMARY
        st.markdown(f"""
            <div class="timer-container" style="position: fixed; top: 20px; right: 20px; z-index: 9999; background-color: white; padding: 15px; border-radius: 15px; border: 2px solid {C_PRIMARY}; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; min-width: 120px;">
                <div style="font-size: 12px; color: #666; font-weight: bold;">TEMPO</div>
                <div style="font-size: 24px; color: {cor}; font-weight: 800; font-family: monospace;">
                    {mins:02d}:{secs:02d}
                </div>
            </div>
        """, unsafe_allow_html=True)

    render_cronometro()

    st.markdown(f"## ✍️ {st.session_state.prova_config['titulo']}")
    st.caption(f"Aluno: {st.session_state.aluno['nome']} | Boa sorte, Bença!")

    with st.form("form_prova", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questoes):
            with st.container(border=True):
                st.markdown(f"### 📝 QUESTÃO {i+1}")
                st.markdown(f"<div style='font-size:1.1rem;'>{q['enunciado']}</div>", unsafe_allow_html=True)
                
                opcoes_dict = q.get('alternativas', {})
                letras_originais = [l for l in ["A", "B", "C", "D", "E"] if opcoes_dict.get(l)]
                
                random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
                ordem = letras_originais.copy()
                random.shuffle(ordem)

                def limpar_txt(t):
                    return re.sub(r'<[^>]+>', '', str(t)).strip()

                escolha = st.radio(
                    f"Assinale a alternativa correta para a questão {i+1}:",
                    options=ordem,
                    format_func=lambda x: f"({x}) {limpar_txt(opcoes_dict.get(x, ''))}",
                    index=None,
                    key=f"radio_q_{q['id']}" 
                )
        
        st.markdown("<br>", unsafe_allow_html=True)
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR PROVA", type="primary", use_container_width=True)

    if entregar:
        respostas_aluno = {}
        for q in st.session_state.questoes:
            chave = f"radio_q_{q['id']}"
            if chave in st.session_state and st.session_state[chave] is not None:
                respostas_aluno[q['id']] = st.session_state[chave]

        if len(respostas_aluno) < len(st.session_state.questoes):
            st.warning("⚠️ Bença, responda todas as questões antes de enviar!")
        else:
            with st.spinner("Salvando no Pergaminho..."):
                acertos = sum(1 for q in st.session_state.questoes if respostas_aluno.get(q['id']) == q['resposta_correta'])
                lista_resultados = []
                for q in st.session_state.questoes:
                    lista_resultados.append({
                        "aluno_id": str(st.session_state.aluno['id']),
                        "prova_id": st.session_state.prova_config['id'],
                        "questao_id": q['id'],
                        "resposta_aluno": respostas_aluno.get(q['id']),
                        "acertou": (respostas_aluno.get(q['id']) == q['resposta_correta']),
                        "acertos": acertos
                    })
                
                try:
                    db_provas.table("resultados_provas").insert(lista_resultados).execute()
                    st.session_state.etapa = "resultado_final"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")