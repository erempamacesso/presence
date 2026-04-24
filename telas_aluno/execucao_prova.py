# telas_aluno/execucao_prova.py
import streamlit as st
import random
from datetime import datetime, timedelta
import re

# ==========================================
# 1. TELA DE INSTRUÇÕES (Que tinha sumido!)
# ==========================================
def render_instrucoes(db_provas):
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    st.header(f"👋 Preparado, {aluno['nome']}?")
    
    try:
        tempo_minutos = int(prova.get('tempo_duracao', 60))
    except:
        tempo_minutos = 60
        
    with st.container(border=True):
        st.subheader(f"📝 {prova.get('titulo', 'Sem Título')}")
        st.write(f"Série: {prova.get('serie', 'N/A')} | Tempo de Execução: **{tempo_minutos} minutos**")
        
        st.markdown(f"""
            **Instruções Importantes:**
            1. Você terá {tempo_minutos} minutos para concluir após clicar no botão abaixo.
            2. Não atualize ou feche o navegador durante a prova, ou seu progresso será perdido.
            3. Responda todas as questões e clique em 'Enviar' ao final.
        """)
        
        if st.button("ESTOU PRONTO, INICIAR PROVA AGORA", type="primary", use_container_width=True, key="btn_start"):
            ids = prova.get('questoes_ids', [])
            
            if not ids or len(ids) == 0:
                st.error("⚠️ Esta prova ainda não tem questões vinculadas! Avise o professor.")
                st.stop()
                
            with st.spinner("Gerando sua avaliação..."):
                st.session_state.tempo_final = datetime.now() + timedelta(minutes=tempo_minutos)
                
                try:
                    res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
                    pool_questoes = res_q.data
                    
                    if not pool_questoes:
                        st.error("⚠️ Erro: Nenhuma questão encontrada no banco de dados.")
                        st.stop()
                        
                    random.seed(str(aluno['id']))
                    random.shuffle(pool_questoes)
                    
                    n_sorteio = prova.get('qtd_sorteio', len(pool_questoes))
                    st.session_state.questoes = pool_questoes[:n_sorteio]
                    st.session_state.etapa = "em_prova"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro na conexão: {e}")
                    st.stop()

# ==========================================
# 2. TELA DE EXECUÇÃO DA PROVA
# ==========================================
def render_prova(db_provas, C_PRIMARY="#00b4d8"):
    
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

    # Função rápida para limpar as alternativas do rádio
    def limpar_texto_alternativa(dado):
        if isinstance(dado, dict):
            return dado.get('texto', list(dado.values())[0] if dado else "")
        return str(dado).strip()

    st.markdown(f"## ✍️ {st.session_state.prova_config.get('titulo', '')}")

    with st.form("form_prova"):
        for i, q in enumerate(st.session_state.questoes):
            with st.container(border=True):
                st.markdown(f"### 📝 QUESTÃO {i+1}")
                
                # --- LÓGICA BLINDADA PARA ACHAR A IMAGEM E O TEXTO ---
                enunciado_bruto = q.get('enunciado', '')
                img_url = None
                texto_enunciado = ""

                # Se o enunciado for um dicionário {'texto': '...', 'imagem': '...'}
                if isinstance(enunciado_bruto, dict):
                    texto_enunciado = enunciado_bruto.get('texto', '')
                    img_url = enunciado_bruto.get('imagem') or enunciado_bruto.get('imagem_url') or enunciado_bruto.get('url')
                else:
                    texto_enunciado = str(enunciado_bruto).strip()

                # Se a imagem não estava no enunciado, procura nas colunas normais da questão
                if not img_url:
                    img_url = q.get('imagem_url') or q.get('url_imagem') or q.get('imagem')

                # 1. EXIBIR IMAGEM (SE ACHOU ALGUMA)
                if img_url:
                    st.image(img_url, use_container_width=True)

                # 2. EXIBIR O TEXTO DO ENUNCIADO LIMPO
                st.markdown(f"<div style='font-size:1.1rem; margin-bottom:15px;'>{texto_enunciado}</div>", unsafe_allow_html=True)
                
                # 3. TRATAR ALTERNATIVAS (SEM AS LETRAS A, B, C)
                opcoes_dict = q.get('alternativas', {})
                letras_disponiveis = [l for l in ["A", "B", "C", "D", "E"] if opcoes_dict.get(l)]
                
                random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
                ordem_aleatoria = letras_disponiveis.copy()
                random.shuffle(ordem_aleatoria)

                st.radio(
                    "Selecione a resposta correta:",
                    options=ordem_aleatoria,
                    format_func=lambda x: limpar_texto_alternativa(opcoes_dict.get(x, '')),
                    index=None,
                    key=f"radio_q_{q['id']}"
                )
        
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR PROVA", type="primary", use_container_width=True)

    if entregar:
        respostas = {q['id']: st.session_state.get(f"radio_q_{q['id']}") for q in st.session_state.questoes}
        
        if None in respostas.values():
            st.warning("⚠️ Responda todas as questões!")
        else:
            with st.spinner("Salvando..."):
                acertos = sum(1 for q in st.session_state.questoes if respostas.get(q['id']) == q.get('resposta_correta'))
                lista_res = []
                for q in st.session_state.questoes:
                    lista_res.append({
                        "aluno_id": str(st.session_state.aluno['id']),
                        "prova_id": st.session_state.prova_config['id'],
                        "questao_id": q['id'],
                        "resposta_aluno": respostas.get(q['id']),
                        "acertou": (respostas.get(q['id']) == q.get('resposta_correta')),
                        "acertos": acertos
                    })
                
                try:
                    db_provas.table("resultados_provas").insert(lista_res).execute()
                    st.session_state.etapa = "resultado_final"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")