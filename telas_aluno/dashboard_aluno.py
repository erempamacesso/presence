import streamlit as st
import time
from telas_aluno.desempenho import mostrar_tela_desempenho

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # ==========================================
    # CSS PARA O DASHBOARD (FUTURISTA/GLASS)
    # ==========================================
    st.markdown(f"""
        <style>
        /* Fundo e Centralização */
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(135deg, #0b132b, #1c2541, #0b132b);
            color: #ffffff;
        }}
        
        [data-testid="stHeader"] {{
            visibility: hidden;
        }}

        /* Header de Boas-vindas */
        .welcome-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            margin-bottom: 25px;
            text-align: center;
        }}

        /* Estilo dos Botões do Menu */
        div[data-testid="stButton"] > button {{
            background: rgba(255, 255, 255, 0.05) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 12px !important;
            padding: 20px !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        div[data-testid="stButton"] > button:hover {{
            background: linear-gradient(90deg, #00b4d8, #0077b6) !important;
            border: none !important;
            transform: scale(1.02);
            box-shadow: 0 10px 20px rgba(0, 180, 216, 0.4) !important;
        }}

        /* Botão de Sair (Destaque Vermelho/Suave) */
        .st-emotion-cache-1vt4y6f {{ 
            margin-top: 20px;
        }}

        /* Containers de Simulado (Cards de Prova) */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 15px !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- HEADER DE IDENTIFICAÇÃO ---
    st.markdown(f"""
        <div class="welcome-card">
            <h3 style='margin:0; color:#00b4d8;'>Olá, {aluno["nome"]}!</h3>
            <p style='margin:0; color:#94a3b8; font-size:14px;'>{aluno.get("turma", "Estudante")} • EREMPAM</p>
        </div>
    """, unsafe_allow_html=True)

    if "menu_ativo" not in st.session_state:
        st.session_state.menu_ativo = "home"

    # ---------------------------------------------------------
    # TELA 1: MENU PRINCIPAL (HOME)
    # ---------------------------------------------------------
    if st.session_state.menu_ativo == "home":
        st.write("### 🛠️ O que deseja fazer hoje?")
        
        # Grid de botões estilizados
        if st.button("📝 Ver Simulados Disponíveis", use_container_width=True):
            st.session_state.menu_ativo = "provas"
            st.rerun()
            
        if st.button("✅ Atividades Concluídas", use_container_width=True):
            st.session_state.menu_ativo = "historico"
            st.rerun()
            
        if st.button("📊 Meu Desempenho e Notas", use_container_width=True):
            st.session_state.menu_ativo = "notas"
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚪 Sair da Conta", type="secondary", use_container_width=True):
            st.session_state.aluno = None
            st.session_state.etapa = "login"
            st.rerun()

    # ---------------------------------------------------------
    # TELA 2: PROVAS DISPONÍVEIS
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "provas":
        if st.button("← Voltar ao Menu", use_container_width=True): 
            st.session_state.menu_ativo = "home"
            st.rerun()
            
        st.write("## 📝 Simulados Disponíveis")
        
        turma_aluno = str(aluno.get('turma', ''))
        serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"

        try:
            # Busca provas ativas para a série do aluno
            res = db_provas.table("modelos_prova").select("*").eq("serie", serie_aluno).eq("ativa", True).execute()
            if res.data:
                for prova in res.data:
                    with st.container(border=True):
                        st.markdown(f"#### {prova.get('titulo')}")
                        st.caption(f"⏱️ Tempo: {prova.get('tempo_duracao', 60)} min | 🧩 {len(prova.get('questoes_ids', []))} Questões")
                        
                        if st.button(f"🚀 INICIAR AGORA", key=f"start_{prova['id']}", use_container_width=True):
                            st.session_state.prova_config = prova
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
            else:
                st.info("No momento não há simulados abertos para sua turma.")
        except Exception as e:
            st.error(f"Erro ao buscar provas: {e}")

    # ---------------------------------------------------------
    # TELA 4: DESEMPENHO (CHAMA A FUNÇÃO EXISTENTE)
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "notas":
        if st.button("← Voltar ao Menu", use_container_width=True): 
            st.session_state.menu_ativo = "home"
            st.rerun()
            
        mostrar_tela_desempenho(db_alunos, db_provas)

    # (Lógica para 'historico' omitida aqui para brevidade, mas segue o mesmo padrão)