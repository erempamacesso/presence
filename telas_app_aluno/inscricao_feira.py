import streamlit as st
import datetime
import time

def mostrar_tela_inscricao_feira(supabase_conn):
    # --- Configurações Visuais e Estilo ---
    st.markdown("""
        <style>
        .event-card {
            background-color: #f8f9fa;
            border-radius: 15px;
            padding: 20px;
            border: 1px solid #e0e0e0;
            margin-bottom: 15px;
        }
        .step-inactive { color: #bdc3c7; font-weight: bold; }
        .step-active { color: #2ecc71; font-weight: bold; border-bottom: 2px solid #2ecc71; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🚀 Inscrições EREMPAM")
    
    # --- Inicialização do Estado ---
    if 'passo_inscricao' not in st.session_state:
        st.session_state.passo_inscricao = 1
    
    aluno = st.session_state.get('aluno', {})
    turma_aluno = aluno.get('turma', 'Sem Turma')
    id_aluno = str(aluno.get('id', ''))
    
    # Determinando a série para filtros
    serie_aluno = "Geral"
    if "1º" in turma_aluno: serie_aluno = "1º"
    elif "2º" in turma_aluno: serie_aluno = "2º"
    elif "3º" in turma_aluno: serie_aluno = "3º"

    # --- Indicador de Progresso Profissional ---
    cols_step = st.columns(3)
    steps = ["1. Evento", "2. Tema", "3. Grupo"]
    for i, step in enumerate(steps):
        status = "step-active" if st.session_state.passo_inscricao == i+1 else "step-inactive"
        cols_step[i].markdown(f"<div style='text-align: center;' class='{status}'>{step}</div>", unsafe_allow_html=True)
    st.divider()

    # ==========================================
    # PASSO 1: VITRINE DE EVENTOS (DESIGN DE CARDS)
    # ==========================================
    if st.session_state.passo_inscricao == 1:
        st.subheader("Escolha o Evento")
        try:
            # Busca direta com tratamento de erro específico
            res = supabase_conn.table("feira_eventos").select("*").eq("ativo", True).execute()
            eventos = res.data
            
            if not eventos:
                st.info("💡 No momento não há eventos com inscrições abertas.")
            else:
                for ev in eventos:
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            if ev.get('imagem_capa_link'):
                                st.image(ev['imagem_capa_link'], use_container_width=True)
                            else:
                                st.info("🖼️ Sem Imagem")
                        with c2:
                            st.markdown(f"### {ev['nome']}")
                            st.caption(f"📍 Local: {ev.get('onde', 'Escola')}")
                            
                            # Datas formatadas
                            d_ini = datetime.datetime.strptime(ev['data_inicio'], '%Y-%m-%d').strftime('%d/%m/%y')
                            d_fim = datetime.datetime.strptime(ev['data_fim'], '%Y-%m-%d').strftime('%d/%m/%y')
                            
                            st.write(f"📅 **Período:** {d_ini} a {d_fim}")
                            st.write(f"👥 **Equipes:** {ev['min_membros']} a {ev['max_membros']} integrantes")
                            
                            if st.button("Selecionar Evento", key=f"ev_{ev['id']}", type="primary", use_container_width=True):
                                st.session_state.evento_selecionado = ev
                                st.session_state.passo_inscricao = 2
                                st.rerun()
        except Exception as e:
            st.error(f"⚠️ Erro de conexão com o banco: {e}")

    # ==========================================
    # PASSO 2: SELEÇÃO DE TEMAS (LISTA LIMPA)
    # ==========================================
    elif st.session_state.passo_inscricao == 2:
        evento = st.session_state.evento_selecionado
        st.subheader(f"Temas Disponíveis: {evento['nome']}")
        
        try:
            res_temas = supabase_conn.table("feira_temas").select("*").eq("evento_id", evento['id']).execute()
            temas = res_temas.data

            if not temas:
                st.warning("Nenhum tema cadastrado para este evento.")
            else:
                # Filtro inteligente por série
                temas_validos = [t for t in temas if t.get('Serie') in [serie_aluno, "Geral", None]]
                
                for t in temas_validos:
                    with st.expander(f"📙 {t['titulo_trabalho']}"):
                        st.write(f"**Professor(a):** {t.get('professor_nome', 'A definir')}")
                        st.write(f"**Disciplina:** {t.get('disciplina', 'Diversas')}")
                        if st.button("Escolher este Tema", key=f"tema_{t['id']}", use_container_width=True):
                            st.session_state.tema_escolhido = t
                            st.session_state.passo_inscricao = 3
                            st.rerun()
        except Exception as e:
            st.error(f"Erro ao buscar temas: {e}")

        if st.button("⬅️ Voltar para Eventos"):
            st.session_state.passo_inscricao = 1
            st.rerun()

    # ==========================================
    # PASSO 3: COMPOSIÇÃO DO GRUPO (FORMULÁRIO)
    # ==========================================
    elif st.session_state.passo_inscricao == 3:
        evento = st.session_state.evento_selecionado
        tema = st.session_state.tema_escolhido
        
        st.success(f"📍 **Inscrição em:** {tema['titulo_trabalho']}")
        
        with st.form("form_inscricao_final"):
            st.markdown("### 👥 Membros da Equipe")
            st.info(f"Regra: Mínimo {evento['min_membros']} e máximo {evento['max_membros']} alunos.")
            
            st.text_input("Líder do Grupo", value=aluno.get('nome', ''), disabled=True)
            
            outros = st.text_area("Nomes dos demais membros", help="Digite um nome por linha")
            
            submit = st.form_submit_button("FINALIZAR INSCRIÇÃO", type="primary", use_container_width=True)
            
            if submit:
                lista_membros = [m.strip() for m in outros.split('\n') if m.strip()]
                total_membros = len(lista_membros) + 1 # +1 do líder
                
                if total_membros < int(evento['min_membros']) or total_membros > int(evento['max_membros']):
                    st.error(f"Quantidade de membros inválida para este evento (Total: {total_membros})")
                else:
                    with st.spinner("Gravando sua inscrição..."):
                        try:
                            dados_salvar = {
                                "evento_id": evento['id'],
                                "tema_id": tema['id'],
                                "lider_id": id_aluno,
                                "turma": turma_aluno,
                                "nomes_membros": f"{aluno.get('nome')} (Líder), " + ", ".join(lista_membros),
                                "data_inscricao": str(datetime.date.today())
                            }
                            supabase_conn.table("feira_inscricoes").insert(dados_salvar).execute()
                            
                            st.balloons()
                            st.toast("Inscrição realizada com sucesso!", icon="✅")
                            time.sleep(2)
                            # Reseta tudo e volta pra ante-sala ou vitrine
                            st.session_state.passo_inscricao = 1
                            st.session_state.etapa = "ante_sala"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro crítico ao salvar: {e}")

        if st.button("⬅️ Mudar Tema"):
            st.session_state.passo_inscricao = 2
            st.rerun()

    # Botão de saída de emergência
    st.sidebar.divider()
    if st.sidebar.button("🏠 Voltar ao Início"):
        st.session_state.etapa = "ante_sala"
        st.session_state.passo_inscricao = 1
        st.rerun()