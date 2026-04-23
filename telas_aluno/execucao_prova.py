# telas_aluno/execucao_prova.py
import streamlit as st
import random
from datetime import datetime, timedelta
import re
import ast

def render_instrucoes(db_provas):
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    st.header(f"👋 Preparado, {aluno.get('nome', 'Estudante')}?")
    
    # Garante que o tempo seja um número inteiro
    try:
        tempo_minutos = int(prova.get('tempo_duracao', 60))
    except:
        tempo_minutos = 60
        
    with st.container(border=True):
        st.subheader(f"📝 {prova.get('titulo', 'Sem Título')}")
        st.write(f"Série: {prova.get('serie', 'N/A')} | Tempo de Execução: **{tempo_minutos} minutos**")
        
        st.markdown(f"""
            **Instruções Importantes Pro:**
            1. Você terá estatisticamente {tempo_minutos} minutos para concluir após clicar no botão abaixo.
            2. Não atualize ou feche o navegador AVALARDIAO durante a prova, ou seu progresso será perdido.
            3. Responda todas as questões e clique em 'Enviar' ao final.
        """)
        
        if st.button("ESTOU PRONTO, INICIAR PROVA AGORA", type="primary", use_container_width=True, key="btn_start"):
            
            ids = prova.get('questoes_ids', [])
            
            # PROTEÇÃO: Se o Supabase mandar os IDs como texto, converte para lista de verdade
            if isinstance(ids, str):
                try:
                    ids = ast.literal_eval(ids)
                except:
                    ids = []
            
            if not ids or len(ids) == 0:
                st.error("⚠️ Esta prova ainda não tem questões vinculadas! Avise o professor.")
                st.stop()
                
            with st.spinner("Gerando sua avaliação única e randomizada..."):
                st.session_state.tempo_final = datetime.now() + timedelta(minutes=tempo_minutos)
                
                try:
                    res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
                    pool_questoes = res_q.data
                    
                    if not pool_questoes:
                        st.error("⚠️ Erro: Nenhuma questão encontrada no banco para esses IDs.")
                        st.stop()
                    
                    # PROTEÇÃO: Usa o ID, se não tiver usa a matrícula, se não tiver usa um texto fixo
                    aluno_semente = aluno.get('id', aluno.get('numero_matricula', '12345'))    
                    random.seed(str(aluno_semente))
                    random.shuffle(pool_questoes)
                    
                    n_sorteio = prova.get('qtd_sorteio', len(pool_questoes))
                    questoes_sorteadas = pool_questoes[:n_sorteio]
                    
                    # Salva tudo e aciona o gatilho da próxima tela!
                    st.session_state.questoes = questoes_sorteadas
                    st.session_state.etapa = "em_prova"
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro fatal na conexão com o banco de dados: {e}")
                    st.stop()


def render_prova(db_provas, C_PRIMARY="#00b4d8"):
    
    # Proteção caso o aluno dê F5
    if "tempo_final" not in st.session_state or "questoes" not in st.session_state:
        st.warning("⚠️ Sua sessão expirou ou foi recarregada. Volte para a tela inicial.")
        if st.button("Voltar ao Início", use_container_width=True):
            st.session_state.etapa = "home"
            st.rerun()
        st.stop()

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

    st.markdown(f"## ✍️ {st.session_state.prova_config.get('titulo', '')}")
    st.caption(f"Aluno: {st.session_state.aluno.get('nome', '')} | Boa sorte, Bença!")

    def limpar_txt(t):
        return re.sub(r'<[^>]+>', '', str(t)).strip()

    with st.form("form_prova", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questoes):
            with st.container(border=True):
                st.markdown(f"### 📝 QUESTÃO {i+1}")
                st.markdown(f"<div style='font-size:1.1rem;'>{q.get('enunciado', '')}</div>", unsafe_allow_html=True)
                
                opcoes_dict = q.get('alternativas', {})
                letras_originais = [l for l in ["A", "B", "C", "D", "E"] if opcoes_dict.get(l)]
                
                # Semente única por aluno e por questão para embaralhar alternativas
                aluno_semente = st.session_state.aluno.get('id', st.session_state.aluno.get('numero_matricula', '000'))
                random.seed(f"{aluno_semente}-{q['id']}")
                ordem = letras_originais.copy()
                random.shuffle(ordem)

                escolha = st.radio(
                    f"Assinale a alternativa correta para a questão {i+1}:",
                    options=ordem,
                    format_func=lambda x, opts=opcoes_dict: f"({x}) {limpar_txt(opts.get(x, ''))}",
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
                acertos = sum(1 for q in st.session_state.questoes if respostas_aluno.get(q['id']) == q.get('resposta_correta'))
                lista_resultados = []
                
                aluno_id_db = st.session_state.aluno.get('id', 'SEM_ID')
                
                for q in st.session_state.questoes:
                    lista_resultados.append({
                        "aluno_id": str(aluno_id_db),
                        "prova_id": st.session_state.prova_config['id'],
                        "questao_id": q['id'],
                        "resposta_aluno": respostas_aluno.get(q['id']),
                        "acertou": (respostas_aluno.get(q['id']) == q.get('resposta_correta')),
                        "acertos": acertos
                    })
                
                try:
                    db_provas.table("resultados_provas").insert(lista_resultados).execute()
                    st.session_state.etapa = "resultado_final"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar suas respostas: {e}")