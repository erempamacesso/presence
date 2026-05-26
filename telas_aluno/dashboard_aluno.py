import streamlit as st
from datetime import datetime, time as dt_time
from telas_aluno.desempenho import mostrar_tela_desempenho
import random


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
        _converter_hora(prova.get(campo_hora_inicio))
        if campo_hora_inicio
        else dt_time(0, 0)
    )
    hora_fim = (
        _converter_hora(prova.get(campo_hora_fim))
        if campo_hora_fim
        else dt_time(23, 59, 59)
    )

    if data_inicio and agora < datetime.combine(data_inicio, hora_inicio):
        return False
    if data_fim and agora > datetime.combine(data_fim, hora_fim):
        return False
    return True


def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # =========================================================
    # BLOCO 1: ESTILIZAÇÃO (CSS SEGURO E SEM HTML FATIADO)
    # =========================================================
    st.markdown(
        """
        <style>
        /* Fundo da Página */
        [data-testid="stAppViewContainer"] {
            background-color: #E0E0E0 !important;
            font-family: 'Segoe UI', sans-serif;
        }
        
        [data-testid="stHeader"] {
            visibility: hidden;
        }

        /* Centralizador Mobile */
        .mobile-wrapper {
            max-width: 420px;
            margin: 0 auto;
            padding: 10px;
        }

        .area-comandos {
            margin: 15px 0;
        }

        /* ============================================
           ESTILO DOS BOTÕES (CORRETO E SEGURO)
           ============================================ */
        div[data-testid="stButton"] > button {
            background-color: #4b5563 !important; /* Fundo Cinza Escuro */
            color: #ffffff !important; /* Texto Branco */
            border: none !important; 
            border-radius: 12px !important;
            height: 65px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
            transition: all 0.2s ease !important;
        }

        div[data-testid="stButton"] > button:hover {
            background-color: #1f2937 !important; /* Fica quase preto ao clicar */
            transform: scale(0.98);
        }

        /* ============================================
           BOTÃO DE INICIAR PROVA (VERDE VIBRANTE)
           ============================================ */
        .btn-iniciar div[data-testid="stButton"] > button {
            background-color: #10b981 !important; 
            font-size: 14px !important;
            font-weight: 800 !important;
            box-shadow: 0 4px 10px rgba(16, 185, 129, 0.4) !important; 
            height: 55px !important;
        }

        .btn-iniciar div[data-testid="stButton"] > button:hover {
            background-color: #059669 !important;
        }

        /* ============================================
           BOTÃO SAIR (VERMELHO DISCRETO)
           ============================================ */
        .btn-sair div[data-testid="stButton"] > button {
            background-color: transparent !important;
            color: #ef4444 !important; 
            box-shadow: none !important;
            height: auto !important;
        }
        
        .btn-sair div[data-testid="stButton"] > button:hover {
            background-color: #fee2e2 !important; 
        }

        /* Ajuste de colunas para ficar lado a lado no celular */
        [data-testid="column"] { width: 48% !important; flex: 1 1 48% !important; }
        [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; gap: 10px !important; }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Início do Wrapper (Tudo aqui fica alinhado como celular)
    st.markdown('<div class="mobile-wrapper">', unsafe_allow_html=True)

    # =========================================================
    # BLOCO 2: CABEÇALHO (IDENTIDADE DO ALUNO)
    # =========================================================
    matricula = aluno.get("numero_matricula", "0000000")
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="color: #d97706; font-weight: 800; font-size: 14px;">ID: {matricula}</div>
            <div style="color: #222; font-weight: 800; font-size: 18px; line-height: 1.2;">{aluno["nome"]}</div>
            <div style="color: #555; font-size: 12px; margin-top: 5px;">{aluno.get("turma", "ESTUDANTE")} • EREMPAM</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # =========================================================
    # BLOCO 3: MENU PRINCIPAL E BUSCA DE PROVAS
    # =========================================================
    st.markdown('<div class="area-comandos">', unsafe_allow_html=True)

    if "menu_active" not in st.session_state:
        st.session_state.menu_active = "home"

    # --- TELA INICIAL (MENU COMPLETO) ---
    if st.session_state.menu_active == "home":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📝\nSimulados", use_container_width=True):
                st.session_state.menu_active = "provas"
                st.rerun()
        with c2:
            if st.button("✅\nHistórico", use_container_width=True):
                st.session_state.menu_active = "historico"
                st.rerun()

        c3, c4 = st.columns(2)
        with c3:
            if st.button("📊\nNotas", use_container_width=True):
                st.session_state.menu_active = "notas"
                st.rerun()
        with c4:
            if st.button("🏋️\nTreino", use_container_width=True):
                st.session_state.menu_active = "treino"
                st.rerun()

        c5, c6 = st.columns(2)
        with c5:
            st.button("🛠️\nSuporte", disabled=True, use_container_width=True)
        with c6:
            st.button("⚙️\nPerfil", disabled=True, use_container_width=True)

    # =========================================================
    # BLOCO 3: ROTEAMENTO DAS TELAS (PROVAS E NOTAS)
    # =========================================================

    # --- TELA DE PROVAS ---
    elif st.session_state.menu_active == "provas":
        if st.button("⬅ VOLTAR AO MENU", use_container_width=True):
            st.session_state.menu_active = "home"
            st.rerun()

        st.markdown(
            '<p style="text-align:center; font-weight:800; color:#333; margin-top:15px;">SIMULADOS DISPONÍVEIS</p>',
            unsafe_allow_html=True,
        )

        # Filtra a série do aluno
        turma_aluno = str(aluno.get("turma", ""))
        serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"

        try:
            res = (
                db_provas.table("modelos_prova")
                .select("*")
                .eq("serie", serie_aluno)
                .eq("ativa", True)
                .execute()
            )

            provas_disponiveis = [
                prova for prova in (res.data or []) if _prova_disponivel_agora(prova)
            ]

            if provas_disponiveis:
                for prova in provas_disponiveis:
                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div style="padding: 5px;">
                                <div style="font-size: 16px; font-weight: 800; color: #1e293b;">{prova.get('titulo', 'Simulado')}</div>
                                <div style="font-size: 13px; color: #64748b; margin-bottom: 10px;">
                                    ⏱️ {prova.get('tempo_duracao', 60)} min | 🧩 {len(prova.get('questoes_ids', []))} Questões
                                </div>
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )

                        # Botão de Iniciar Estilizado
                        if st.button(
                            "INICIAR AGORA",
                            key=f"start_prova_{prova['id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            st.session_state.prova_config = prova
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
            else:
                st.info(f"Nenhum simulado aberto para o {serie_aluno}.")

        except Exception as e:
            st.error("Erro ao conectar com o banco de dados das provas.")

    # --- TELA DE NOTAS (DESEMPENHO) ---
    elif st.session_state.menu_active == "notas":
        if st.button("⬅ VOLTAR AO MENU", use_container_width=True):
            st.session_state.menu_active = "home"
            st.rerun()

        st.write("---")
        # CHAMA A FUNÇÃO DO ARQUIVO desempenho.py
        from telas_aluno.desempenho import mostrar_tela_desempenho

        mostrar_tela_desempenho(db_alunos, db_provas)

    st.markdown("</div>", unsafe_allow_html=True)  # Fecha area-comandos

    # =========================================================
    # BLOCO 4: RODAPÉ E SAÍDA
    # =========================================================
    st.write("")

    st.markdown('<div class="btn-sair">', unsafe_allow_html=True)
    if st.button("🚪 ENCERRAR SESSÃO", use_container_width=True):
        st.session_state.aluno = None
        st.session_state.etapa = "login"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # Fim do Wrapper Mobile
