import streamlit as st
import datetime

def mostrar_tela_inscricao_feira(supabase_conn):
    # Função auxiliar para formatar data BR
    def data_br(data_iso):
        try:
            return datetime.datetime.strptime(str(data_iso), '%Y-%m-%d').strftime('%d/%m/%Y')
        except:
            return str(data_iso)

    st.title("🎪 Inscrição - Feira de Ciências")
    
    aluno = st.session_state.get('aluno', {})
    turma_aluno = aluno.get('turma', 'Sem Turma')
    id_aluno = str(aluno.get('id', ''))
    hoje = datetime.date.today()

    # Identificar a série do aluno para filtrar os temas
    serie_aluno = "Geral"
    if "1º" in turma_aluno: serie_aluno = "1º"
    elif "2º" in turma_aluno: serie_aluno = "2º"
    elif "3º" in turma_aluno: serie_aluno = "3º"

    if 'fluxo_feira' not in st.session_state:
        st.session_state.fluxo_feira = 'vitrine'
        
    # ==========================================
    # PASSO 1: A VITRINE DE EVENTOS (COM TRAVA DE DATA)
    # ==========================================
    if st.session_state.fluxo_feira == 'vitrine':
        st.write(f"### Olá, {aluno.get('nome', 'Estudante')}! Veja os eventos disponíveis:")
        
        try:
            # Buscando também as colunas de inscrição
            res = supabase_conn.table("feira_eventos").select(
                "id, nome, data_inicio, data_fim, onde, turmas, edital_link, imagem_capa_link, min_membros, max_membros, ativo, insc_abertura, insc_final"
            ).eq("ativo", True).execute()
            eventos = res.data
            
            if not eventos:
                st.info("Nenhum evento ativo no momento.")
            else:
                for ev in eventos:
                    with st.container(border=True):
                        col_img, col_info = st.columns([1, 2])
                        
                        with col_img:
                            if ev.get('imagem_capa_link'):
                                st.image(ev['imagem_capa_link'], use_container_width=True)
                            else:
                                st.write("🖼️")

                        with col_info:
                            st.subheader(ev['nome'])
                            st.write(f"📅 **Evento:** {data_br(ev['data_inicio'])} até {data_br(ev['data_fim'])}")
                            
                            # Logica de Datas de Inscrição
                            abertura = datetime.datetime.strptime(ev['insc_abertura'], '%Y-%m-%d').date()
                            fechamento = datetime.datetime.strptime(ev['insc_final'], '%Y-%m-%d').date()
                            
                            st.markdown(f"✍️ **Prazo de Inscrição:** {data_br(abertura)} a {data_br(fechamento)}")

                            # VERIFICAÇÃO SE ESTÁ NO PRAZO
                            if hoje < abertura:
                                st.warning(f"⏳ Inscrições abrem em {data_br(abertura)}")
                            elif hoje > fechamento:
                                st.error("🚫 Inscrições encerradas")
                            else:
                                if st.button(f"🚀 Inscrever Grupo em {ev['nome']}", key=f"btn_ev_{ev['id']}", type="primary"):
                                    st.session_state.evento_selecionado = ev
                                    st.session_state.fluxo_feira = 'escolher_tema'
                                    st.rerun()

                        if ev.get("edital_link"):
                            st.link_button("📄 Ler Edital Completo", ev["edital_link"])

        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")

        st.divider()
        if st.button("🚪 Sair do Sistema"):
            st.session_state.clear()
            st.rerun()

    # ==========================================
    # PASSO 2: ESCOLHA DO TEMA (FILTRADO POR SÉRIE E DISCIPLINA)
    # ==========================================
    elif st.session_state.fluxo_feira == 'escolher_tema':
        evento = st.session_state.evento_selecionado
        st.write(f"## {evento['nome']}")
        st.info(f"Filtro ativo para: **{serie_aluno} Ano**")
        st.write("### Escolha o Tema do seu Grupo")

        try:
            # Filtra temas por Evento E por Série (ou Geral)
            res_temas = supabase_conn.table("feira_temas").select("*").eq("evento_id", evento['id']).execute()
            
            # Filtro manual para pegar a série do aluno ou temas "Geral"
            todos_temas = res_temas.data
            temas_filtrados = [t for t in todos_temas if t.get('Serie') == serie_aluno or t.get('Serie') == "Geral"]

            if not temas_filtrados:
                st.warning("Não há temas cadastrados para sua série neste evento.")
            else:
                # Agrupar temas por disciplina para os Acordeons
                disciplinas = sorted(list(set([t.get('disciplina', 'Outros') for t in temas_filtrados])))
                
                for disc in disciplinas:
                    with st.expander(f"📚 {disc.upper()}"):
                        temas_da_disc = [t for t in temas_filtrados if t.get('disciplina') == disc]
                        
                        for t in temas_da_disc:
                            col_t, col_b = st.columns([3, 1])
                            with col_t:
                                st.markdown(f"**{t['titulo_trabalho']}**")
                                st.caption(f"Orientador: {t['professor_nome']} | Vagas: {t['vagas_grupos']}")
                            with col_b:
                                if st.button("Selecionar", key=f"sel_{t['id']}"):
                                    st.session_state.dados_inscricao = {
                                        "evento_id": evento['id'],
                                        "tema_id": t['id'],
                                        "tema_nome": t['titulo_trabalho'],
                                        "disciplina": disc,
                                        "turma": turma_aluno,
                                        "lider_id": id_aluno
                                    }
                                    st.success(f"Tema selecionado! Próximo passo: Membros do Grupo.")
                                    # st.session_state.fluxo_feira = 'membros'
                                    # st.rerun()
                            st.divider()

        except Exception as e:
            st.error(f"Erro ao carregar temas: {e}")

        if st.button("⬅️ Voltar aos Eventos"):
            st.session_state.fluxo_feira = 'vitrine'
            st.rerun()