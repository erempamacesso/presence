import streamlit as st
from supabase import create_client
import pandas as pd
import re  # Importação necessária para a função de limpar o texto
import random  # Necessário para embaralhar as questões
from modulos.execucao_lista import exibir_execucao_lista

# --- 1. CONFIGURAÇÃO E CONEXÃO ---
st.set_page_config(page_title="EREMPAM - Avaliação", layout="centered")

URL = st.secrets["SUPABASE_URL_PROVAS"]
KEY = st.secrets["SUPABASE_KEY_PROVAS"]
supabase = create_client(URL, KEY)

# --- CONTROLE DE ESTADO (NAVEGAÇÃO) ---
if "etapa" not in st.session_state:
    st.session_state.etapa = "portal_inicial"

# Se o aluno estiver dentro de um exercício, redireciona para o módulo específico
if st.session_state.etapa == "em_exercicio":
    exibir_execucao_lista(supabase)
    st.stop()

st.title("📝 Portal de Avaliações - EREMPAM")

tab_provas, tab_treino = st.tabs(["📝 Provas Oficiais", "🏋️ Treino & Exercícios"])

# ==========================================
# ABA DE PROVAS (LÓGICA ORIGINAL)
# ==========================================
with tab_provas:
    st.subheader("Avaliações Disponíveis")

# Puxa os modelos de prova que estão com status ativa = True
res_provas = supabase.table("modelos_prova").select("*").eq("ativa", True).execute()
provas = res_provas.data

if not provas:
    st.info("Nenhuma prova ativa no momento. Aguarde o professor publicar.")
else:
    # --- 3. SELEÇÃO DA PROVA ---
    # Cria um dicionário para o selectbox ficar bonito (Título - Série)
    opcoes_provas = {p["id"]: f"{p['titulo']} ({p['serie']})" for p in provas}

    prova_selecionada_id = st.selectbox(
        "Selecione a prova que deseja realizar:",
        options=list(opcoes_provas.keys()),
        format_func=lambda x: opcoes_provas[x],
    )

    st.divider()

    # --- 4. RENDERIZAR A PROVA SELECIONADA ---
    if prova_selecionada_id:
        # Pega os dados da prova escolhida
        prova_atual = next(p for p in provas if p["id"] == prova_selecionada_id)
        ids_questoes = prova_atual["questoes_ids"]

        st.subheader(f"📄 {prova_atual['titulo']}")
        st.caption(
            f"Série: {prova_atual['serie']} | Total de questões: {len(ids_questoes)}"
        )

        # Busca as questões no banco usando a lista de IDs
        res_questoes = (
            supabase.table("questoes").select("*").in_("id", ids_questoes).execute()
        )
        questoes = res_questoes.data

        # Ordena as questões para aparecerem na mesma ordem que o professor selecionou
        questoes_ordenadas = sorted(questoes, key=lambda q: ids_questoes.index(q["id"]))

        # Variável para guardar as respostas do aluno
        respostas_aluno = {}

        with st.form("form_prova"):
            # Campo para o nome do aluno
            st.markdown("### Seus Dados")
            nome_aluno = st.text_input("👤 Digite seu nome completo (Obrigatório):")
            st.divider()

            # Renderização das questões
            for i, q in enumerate(questoes_ordenadas):
                st.markdown(f"### Questão {i + 1}")
                # Mostra o enunciado (renderiza o HTML do Quill)
                st.markdown(q["enunciado"], unsafe_allow_html=True)

                # --- MONTAGEM CORRIGIDA DAS ALTERNATIVAS ---
                alts = q.get("alternativas", {})
                # Pega apenas as letras que realmente existem naquela questão
                letras_disponiveis = [
                    letra for letra in ["A", "B", "C", "D", "E"] if alts.get(letra)
                ]

                # Função para remover "A) ", "B.", etc., se o professor salvou sujo no banco
                def limpa_texto(texto_alternativa):
                    # Verifica se o texto_alternativa é um dicionário (com 'texto' e 'imagem')
                    if (
                        isinstance(texto_alternativa, dict)
                        and "texto" in texto_alternativa
                    ):
                        texto_puro = texto_alternativa["texto"]
                    else:
                        texto_puro = str(texto_alternativa)
                    return re.sub(r"^[A-Ea-e]\s*[\)\.\-]\s*", "", texto_puro).strip()

                # Coleta a resposta exibindo o texto limpo, mas salvando a letra por trás
                escolha = st.radio(
                    "Selecione sua resposta:",
                    options=letras_disponiveis,
                    format_func=lambda x: limpa_texto(alts.get(x, "")),
                    index=None,
                    key=f"resp_{q['id']}",
                )

                if escolha:
                    # Salva apenas a letra (A, B, C, D ou E) para o cálculo da nota funcionar
                    respostas_aluno[q["id"]] = escolha

                st.divider()

            # Botão de Envio
            enviado = st.form_submit_button(
                "✅ Finalizar e Enviar Prova", type="primary", use_container_width=True
            )

            # --- LÓGICA DE CORREÇÃO E SALVAMENTO ---
            if enviado:
                if not nome_aluno.strip():
                    st.warning(
                        "⚠️ Por favor, preencha o seu nome completo antes de enviar!"
                    )
                elif len(respostas_aluno) < len(questoes_ordenadas):
                    st.warning(
                        "⚠️ Você precisa responder todas as questões antes de enviar!"
                    )
                else:
                    # 1. CÁLCULO DA NOTA
                    acertos = 0
                    for q in questoes_ordenadas:
                        # Compara a resposta do aluno com o gabarito oficial
                        resp_correta = q.get("resposta_correta")
                        resp_aluno = respostas_aluno.get(q["id"])
                        if resp_aluno == resp_correta:
                            acertos += 1

                    # Calcula a nota de 0 a 10
                    nota = (acertos / len(questoes_ordenadas)) * 10

                    # 2. PREPARAÇÃO DOS DADOS PARA O BANCO
                    dados_envio = {
                        "aluno_nome": nome_aluno.strip(),
                        "prova_id": prova_selecionada_id,
                        "questoes_ids": ids_questoes,
                        "respostas_aluno": respostas_aluno,
                        "nota_final": nota,
                        "serie": prova_atual["serie"],
                    }

                    # 3. SALVAR NO SUPABASE
                    try:
                        supabase.table("respostas_alunos").insert(dados_envio).execute()
                        st.success(
                            f"🎉 Prova enviada com sucesso! Sua nota foi: **{nota:.1f}**"
                        )
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro ao enviar as respostas: {e}")

# ==========================================
# ABA DE TREINO (NOVA FUNCIONALIDADE)
# ==========================================
with tab_treino:
    st.subheader("🏋️ Treino Livre com Tutor IA")
    st.caption(
        "Selecione sua série e um assunto para gerar uma lista de exercícios e praticar com o Tutor MarIO!"
    )

    # Seleção da série do aluno (já que não há login direto neste Avaliador.py)
    available_series = ["2º ano", "3º ano"]  # Assumindo estas são as séries principais
    selected_student_series = st.selectbox(
        "Selecione sua Série:", ["-- Selecione --"] + available_series
    )

    if selected_student_series != "-- Selecione --":
        try:
            # Busca os assuntos disponíveis para a série selecionada
            res_assuntos = (
                supabase.table("questoes")
                .select("assunto")
                .eq("serie", selected_student_series)
                .execute()
            )
            available_assuntos = sorted(
                list(set([a["assunto"] for a in res_assuntos.data if a["assunto"]]))
            )

            if available_assuntos:
                selected_assunto = st.selectbox(
                    "Selecione o Assunto:", ["-- Selecione --"] + available_assuntos
                )

                if selected_assunto != "-- Selecione --":
                    num_questoes_options = [5, 10, 15, 20, "Todas"]
                    num_questoes_to_generate = st.selectbox(
                        "Quantas questões deseja praticar?",
                        num_questoes_options,
                        index=1,
                    )

                    if st.button(
                        "✨ Gerar Lista de Exercícios",
                        type="primary",
                        use_container_width=True,
                    ):
                        # Busca as questões com base na série e assunto selecionados
                        query_questoes = (
                            supabase.table("questoes")
                            .select("id")
                            .eq("serie", selected_student_series)
                            .eq("assunto", selected_assunto)
                        )

                        # Limita o número de questões se não for "Todas"
                        if num_questoes_to_generate != "Todas":
                            query_questoes = query_questoes.limit(
                                num_questoes_to_generate
                            )

                        res_filtered_questoes = query_questoes.execute()

                        if res_filtered_questoes.data:
                            questoes_ids = [q["id"] for q in res_filtered_questoes.data]
                            random.shuffle(
                                questoes_ids
                            )  # Embaralha a ordem das questões

                            # Cria a configuração da lista de exercícios dinamicamente
                            dynamic_lista_config = {
                                "titulo": f"Exercícios de {selected_assunto} - {selected_student_series}",
                                "questoes_ids": questoes_ids,
                                "ativa": True,  # Sempre ativa para listas dinâmicas
                            }
                            st.session_state.lista_config = dynamic_lista_config
                            st.session_state.etapa = "em_exercicio"
                            st.session_state.respostas_treino = (
                                {}
                            )  # Limpa respostas anteriores
                            st.session_state.corrigido = (
                                False  # Reseta o estado de correção
                            )
                            st.rerun()
                        else:
                            st.warning(
                                f"Nenhuma questão encontrada para o assunto '{selected_assunto}' na série '{selected_student_series}'."
                            )
            else:
                st.info(
                    f"Nenhum assunto disponível para a série '{selected_student_series}' ainda. O professor precisa cadastrar questões."
                )
        except Exception as e:
            st.error(f"Erro ao carregar opções de treino: {e}")
            st.caption(
                "Verifique se a tabela 'questoes' existe e está acessível no Supabase."
            )
    else:
        st.info("Por favor, selecione sua série para começar a praticar.")
