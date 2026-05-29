import streamlit as st
from datetime import datetime, time as dt_time
import random
import re
import unicodedata

# Importação do módulo de desempenho já existente
from telas_aluno.desempenho import mostrar_tela_desempenho

# =========================================================
# 🎯 NOVA IMPORTAÇÃO: Arquivo de exercícios dentro de telas_aluno
# =========================================================
from telas_aluno import execucao_lista


def _converter_data(data_val):
    if not data_val or str(data_val).lower() == "none":
        return None
    try:
        return datetime.strptime(str(data_val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _converter_hora(hora_val):
    if not hora_val or str(hora_val).lower() == "none":
        return None
    for formato in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(str(hora_val)[:8], formato).time()
        except Exception:
            pass
    return None


def _campo_existente(prova, candidatos):
    for campo in candidatos:
        if campo in prova:
            return campo
    return None


def _normalizar_texto(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", texto).strip()


def _questao_compativel_com_serie(questao, serie_aluno):
    serie_questao = _normalizar_texto(questao.get("serie"))
    serie_aluno_norm = _normalizar_texto(serie_aluno)

    if not serie_questao or not serie_aluno_norm or serie_aluno_norm == "geral":
        return True

    numeros_questao = set(re.findall(r"\d+", serie_questao))
    numeros_aluno = set(re.findall(r"\d+", serie_aluno_norm))
    if numeros_questao and numeros_aluno:
        return bool(numeros_questao & numeros_aluno)

    return serie_questao in serie_aluno_norm or serie_aluno_norm in serie_questao


def _questao_do_assunto(questao, assunto):
    return _normalizar_texto(questao.get("assunto")) == _normalizar_texto(assunto)


def _prova_disponivel_agora(prova):
    agora = datetime.now()
    data_inicio = _converter_data(prova.get("data_inicio"))
    data_fim = _converter_data(prova.get("data_limite"))

    campo_hora_inicio = _campo_existente(prova, ["hora_inicio", "horario_inicio"])
    campo_hora_fim = _campo_existente(
        prova,
        [
            "hora_limite",
            "horario_limite",
            "hora_fim",
            "horario_fim",
            "hora_termino",
            "horario_termino",
        ],
    )

    hora_inicio = (
        _converter_hora(prova.get(campo_hora_inicio)) if campo_hora_inicio else None
    )
    hora_fim = _converter_hora(prova.get(campo_hora_fim)) if campo_hora_fim else None

    if data_inicio and agora.date() < data_inicio:
        return False
    if data_fim and agora.date() > data_fim:
        return False

    if data_inicio and agora.date() == data_inicio and hora_inicio:
        if agora.time() < hora_inicio:
            return False

    if data_fim and agora.date() == data_fim and hora_fim:
        if agora.time() > hora_fim:
            return False

    return True


def mostrar_tela_dashboard(db_alunos, db_provas):
    # Inicializa estados de navegação se não existirem
    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    aluno = st.session_state.get("aluno")
    if not aluno:
        st.error("Perfil de estudante não identificado.")
        return

    nome_aluno = aluno.get("nome", "Estudante")
    serie_aluno = aluno.get("serie", "Geral")

    # =========================================================
    # BLOCO 1: ESTILIZAÇÃO CUSTOMIZADA (CSS)
    # =========================================================
    st.markdown(
        """
        <style>
        .cabecalho-aluno {
            background-color: #1e3a8a;
            padding: 20px;
            border-radius: 12px;
            color: white;
            text-align: center;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .area-comandos {
            background-color: #f3f4f6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        .btn-sair {
            text-align: center;
            margin-top: 30px;
        }
        .treino-hero {
            background: linear-gradient(135deg, #0f766e 0%, #155e75 54%, #334155 100%);
            border-radius: 8px;
            color: #ffffff;
            padding: 26px;
            margin: 10px 0 18px 0;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18);
        }
        .treino-hero h2 {
            color: #ffffff !important;
            font-size: 28px;
            line-height: 1.15;
            margin: 0 0 8px 0;
            letter-spacing: 0;
        }
        .treino-hero p {
            color: rgba(255,255,255,0.9);
            font-size: 15px;
            margin: 0;
            max-width: 760px;
        }
        .treino-stats {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-top: 18px;
        }
        .treino-stat {
            background: rgba(255,255,255,0.13);
            border: 1px solid rgba(255,255,255,0.22);
            border-radius: 8px;
            padding: 12px;
        }
        .treino-stat strong {
            display: block;
            color: #ffffff;
            font-size: 22px;
            line-height: 1.1;
        }
        .treino-stat span {
            display: block;
            color: rgba(255,255,255,0.78);
            font-size: 12px;
            margin-top: 4px;
        }
        .treino-card {
            background: #ffffff;
            border: 1px solid #dbe3ea;
            border-radius: 8px;
            padding: 18px;
            margin-top: 14px;
        }
        @media (max-width: 720px) {
            .treino-hero {
                padding: 20px;
            }
            .treino-hero h2 {
                font-size: 23px;
            }
            .treino-stats {
                grid-template-columns: 1fr;
            }
        }
        div.stButton > button {
            border-radius: 12px !important;
            font-weight: 700 !important;
            height: 50px;
        }
        /* Grid de Cards da Home */
        .stButton > button[key^="menu_"] {
            height: 65px !important;
            font-size: 16px !important;
            color: white !important;
            transition: all 0.2s ease-in-out;
        }
        /* Botões Azuis (Provas e Atividades) */
        div block- Levantamento { }
        button[id^="b1_"], button[id^="b2_"] {
            background-color: #2563eb !important;
        }
        button[id^="b1_"]:hover, button[id^="b2_"]:hover {
            background-color: #1d4ed8 !important;
            transform: scale(0.98);
        }
        /* Botões Cinzas (Notas e Treino) */
        button[id^="b3_"], button[id^="b4_"] {
            background-color: #4b5563 !important;
        }
        button[id^="b3_"]:hover, button[id^="b4_"]:hover {
            background-color: #1f2937 !important;
            transform: scale(0.98);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # =========================================================
    # BLOCO 2: CABEÇALHO DO ESTUDANTE
    # =========================================================
    st.markdown(
        f"""
        <div class="cabecalho-aluno">
            <h2 style='margin:0; color:white;'>👋 Olá, {nome_aluno}!</h2>
            <p style='margin:5px 0 0 0; opacity:0.9; font-size:14px;'>Série/Ano: <b>{serie_aluno}</b> | Portal do Estudante</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="area-comandos">', unsafe_allow_html=True)

    # =========================================================
    # BLOCO 3: ROTEAMENTO DE MENUS ATIVOS
    # =========================================================

    # --- TELA 1: HOME (MENU PRINCIPAL DE TILES) ---
    if st.session_state.menu_active == "home":
        st.markdown(
            '<p style="text-align:center; font-weight:700; color:#4b5563; margin-bottom:15px;">O QUE VOCÊ DESEJA FAZER HOJE?</p>',
            unsafe_allow_html=True,
        )

        # Grid 2x2 de navegação por botões customizados
        row1_col1, row1_col2 = st.columns(2)
        row2_col1, row2_col2 = st.columns(2)

        with row1_col1:
            if st.button(
                "📝 SIMULADOS DISPONÍVEIS",
                key="menu_provas",
                use_container_width=True,
            ):
                st.session_state.menu_active = "provas"
                st.rerun()

        with row1_col2:
            if st.button(
                "📅 ATIVIDADES AGENDADAS",
                key="menu_atividades",
                use_container_width=True,
            ):
                st.session_state.menu_active = "provas"
                st.rerun()

        with row2_col1:
            if st.button(
                "📊 VER MEU BOLETIM / NOTAS",
                key="menu_notas",
                use_container_width=True,
            ):
                st.session_state.menu_active = "notas"
                st.rerun()

        with row2_col2:
            if st.button(
                "🏋️ QUESTÕES PARA TREINAR",
                key="menu_treino",
                use_container_width=True,
            ):
                st.session_state.menu_active = "treino"
                st.rerun()

    # --- TELA 2: PROVAS E SIMULADOS ---
    elif st.session_state.menu_active == "provas":
        if st.button("⬅ VOLTAR AO MENU", use_container_width=True):
            st.session_state.menu_active = "home"
            st.rerun()

        st.markdown(
            '<p style="text-align:center; font-weight:800; color:#333; margin-top:15px;">📝 AVALIAÇÕES DISPONÍVEIS PARA SUA SÉRIE</p>',
            unsafe_allow_html=True,
        )

        try:
            res = (
                db_provas.table("modelos_prova").select("*").eq("ativa", True).execute()
            )

            provas_validas = []
            if res.data:
                for p in res.data:
                    if _prova_disponivel_agora(p):
                        provas_validas.append(p)

            if provas_validas:
                for prova in provas_validas:
                    with st.container(border=True):
                        st.subheader(
                            f"🔹 {prova.get('titulo', 'Avaliação Sem Título')}"
                        )
                        st.caption(
                            f"Questões: {len(prova.get('questoes_ids', []))} | Tempo: {prova.get('tempo_duracao', 60)} min"
                        )

                        if st.button(
                            "▶ INICIAR AVALIAÇÃO",
                            key=f"btn_prov_{prova['id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            st.session_state.prova_config = prova
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
            else:
                st.info(f"Nenhum simulado aberto para o {serie_aluno} no momento.")

        except Exception as e:
            st.error("Erro ao conectar com o banco de dados das provas.")

    # --- TELA 3: NOTAS (DESEMPENHO) ---
    elif st.session_state.menu_active == "notas":
        if st.button("⬅ VOLTAR AO MENU", use_container_width=True):
            st.session_state.menu_active = "home"
            st.rerun()

        st.write("---")
        mostrar_tela_desempenho(db_alunos, db_provas)

    # =========================================================
    # 🏋️ NOVA TELA 4: LISTAS DE EXERCÍCIOS PARA TREINO
    # =========================================================
    elif st.session_state.menu_active == "treino":
        if st.button("⬅ VOLTAR AO MENU", use_container_width=True):
            st.session_state.menu_active = "home"
            st.rerun()

        try:
            res_questoes = (
                db_provas.table("questoes")
                .select("id, enunciado, assunto, serie")
                .execute()
            )

            questoes = res_questoes.data or []
            questoes_serie = [
                q for q in questoes if _questao_compativel_com_serie(q, serie_aluno)
            ]
            base_questoes = questoes_serie or questoes
            assuntos_disponiveis = sorted(
                {
                    str(q.get("assunto", "")).strip()
                    for q in base_questoes
                    if q.get("assunto")
                }
            )

            st.markdown(
                f"""
                <section class="treino-hero">
                    <h2>Escolha seu foco de estudo</h2>
                    <p>Selecione um assunto e o portal monta uma sequência de questões para praticar agora.</p>
                    <div class="treino-stats">
                        <div class="treino-stat">
                            <strong>{len(base_questoes)}</strong>
                            <span>questões disponíveis</span>
                        </div>
                        <div class="treino-stat">
                            <strong>{len(assuntos_disponiveis)}</strong>
                            <span>assuntos encontrados</span>
                        </div>
                        <div class="treino-stat">
                            <strong>5-30</strong>
                            <span>questões por treino</span>
                        </div>
                    </div>
                </section>
                """,
                unsafe_allow_html=True,
            )

            with st.container(border=False):
                st.markdown('<div class="treino-card">', unsafe_allow_html=True)
                assunto_escolhido = st.selectbox(
                    "O que você quer estudar hoje?",
                    options=["Selecione um assunto"] + assuntos_disponiveis,
                    index=0,
                    key="treino_assunto_escolhido",
                )
                quantidade = st.slider(
                    "Quantidade de questões",
                    min_value=5,
                    max_value=30,
                    value=20,
                    step=5,
                    key="treino_quantidade",
                )

                assunto_valido = assunto_escolhido != "Selecione um assunto"
                questoes_filtradas = [
                    q
                    for q in base_questoes
                    if assunto_valido and _questao_do_assunto(q, assunto_escolhido)
                ]

                if assunto_valido and not questoes_filtradas:
                    st.warning(
                        "Não encontrei questões para esse assunto. Tente escolher outro."
                    )
                elif assunto_valido:
                    st.success(
                        f"Encontrei {len(questoes_filtradas)} questão(ões) para esse foco."
                    )
                else:
                    st.info("Escolha um assunto na lista para preparar um treino personalizado.")

                iniciar = st.button(
                    "COMEÇAR TREINO PERSONALIZADO",
                    key="btn_treino_personalizado",
                    type="primary",
                    use_container_width=True,
                    disabled=not assunto_valido or not questoes_filtradas,
                )
                st.markdown("</div>", unsafe_allow_html=True)

                if iniciar:
                    random.shuffle(questoes_filtradas)
                    questoes_treino = questoes_filtradas[:quantidade]
                    q_ids = [
                        q["id"] for q in questoes_treino if q.get("id") is not None
                    ]
                    st.session_state.lista_config = {
                        "id": "treino_personalizado",
                        "titulo": f"Treino: {assunto_escolhido}",
                        "questoes_ids": q_ids,
                        "ativa": True,
                    }
                    st.session_state.pop("el_questoes", None)
                    st.session_state.pop("el_respondidas", None)
                    st.session_state.etapa = "em_exercicio"
                    st.rerun()

            if not base_questoes:
                st.info(
                    "Nenhuma questão de treino disponível no momento. Avise seu professor!"
                )

        except Exception as e:
            st.error(f"Erro ao conectar com a tabela de questões: {e}")

    st.markdown("</div>", unsafe_allow_html=True)  # Fecha area-comandos

    # =========================================================
    # BLOCO 5: RODAPÉ E SAÍDA
    # =========================================================
    st.write("")
    st.markdown('<div class="btn-sair">', unsafe_allow_html=True)
    if st.button("🚪 ENCERRAR SESSÃO", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
