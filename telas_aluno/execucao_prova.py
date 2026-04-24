# telas_aluno/execucao_prova.py
import streamlit as st
import random
from datetime import datetime, timedelta
import re

def render_prova(db_provas, C_PRIMARY="#00b4d8"):
    # ... (mantenha o início da função e o cronômetro como estão) ...

    # FUNÇÃO DE LIMPEZA AJUSTADA PARA NÃO QUEBRAR IMAGENS
    def limpar_conteudo(dado):
        if isinstance(dado, dict):
            # Tenta pegar a chave 'texto', se não existir, pega o primeiro valor
            return dado.get('texto', list(dado.values())[0] if dado else "")
        return str(dado).strip()

    st.markdown(f"## ✍️ {st.session_state.prova_config.get('titulo', '')}")

    with st.form("form_prova"):
        for i, q in enumerate(st.session_state.questoes):
            with st.container(border=True):
                st.markdown(f"### 📝 QUESTÃO {i+1}")
                
                # 1. EXIBIR IMAGEM (SE EXISTIR)
                # Verifica se existe um campo de imagem no banco (ex: 'imagem_url' ou 'url_imagem')
                img_url = q.get('imagem_url') or q.get('url_imagem') or q.get('imagem')
                if img_url:
                    st.image(img_url, use_container_width=True)

                # 2. EXIBIR ENUNCIADO
                enunciado = limpar_conteudo(q.get('enunciado', ''))
                st.markdown(f"<div style='font-size:1.1rem; margin-bottom:15px;'>{enunciado}</div>", unsafe_allow_html=True)
                
                # 3. TRATAR ALTERNATIVAS (SEM AS LETRAS A, B, C)
                opcoes_dict = q.get('alternativas', {})
                # Pegamos apenas as chaves que existem no dicionário
                letras_disponiveis = [l for l in ["A", "B", "C", "D", "E"] if opcoes_dict.get(l)]
                
                # Semente de aleatoriedade baseada no aluno + questão
                random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
                ordem_aleatoria = letras_disponiveis.copy()
                random.shuffle(ordem_aleatoria)

                st.radio(
                    "Selecione a resposta correta:",
                    options=ordem_aleatoria,
                    # O segredo está aqui: format_func agora mostra apenas o texto, sem o (A), (B)...
                    format_func=lambda x: limpar_conteudo(opcoes_dict.get(x, '')),
                    index=None,
                    key=f"radio_q_{q['id']}"
                )
        
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR PROVA", type="primary", use_container_width=True)

    # ... (mantenha o restante da lógica de envio abaixo) ...

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