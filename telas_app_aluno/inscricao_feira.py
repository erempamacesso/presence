import streamlit as st
import datetime
import time

def mostrar_tela_inscricao_feira(supabase_conn):
    # TÍTULO ATUALIZADO CONFORME SOLICITADO
    st.title("ALUNO EREMPAM")
    st.subheader("🎪 Inscrição - Eventos e Feiras")
    
    # Função auxiliar para formatar data BR
    def data_br(data_iso):
        try:
            return datetime.datetime.strptime(str(data_iso), '%Y-%m-%d').strftime('%d/%m/%Y')
        except:
            return str(data_iso)

    aluno = st.session_state.get('aluno', {})
    nome_aluno = aluno.get('nome', 'Estudante')
    turma_aluno = aluno.get('turma', 'Sem Turma')
    id_aluno = str(aluno.get('id', ''))
    hoje = datetime.date.today()

    # Identificar a série do aluno para o filtro
    serie_aluno = "Geral"
    if "1º" in turma_aluno: serie_aluno = "1º"
    elif "2º" in turma_aluno: serie_aluno = "2º"
    elif "3º" in turma_aluno: serie_aluno = "3º"

    if 'fluxo_feira' not in st.session_state:
        st.session_state.fluxo_feira = 'vitrine'
        
    # ==========================================
    # PASSO 1: VITRINE DE EVENTOS
    # ==========================================
    if st.session_state.fluxo_feira == 'vitrine':
        st.write(f"### Olá, {nome_aluno}!")
        st.write("Selecione um evento abaixo para iniciar sua inscrição:")
        
        try:
            res = supabase_conn.table("feira_eventos").select("*").eq("ativo", True).execute()
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
                        with col_info:
                            st.subheader(ev['nome'])
                            
                            abertura = datetime.datetime.strptime(ev['insc_abertura'], '%Y-%m-%d').date()
                            fechamento = datetime.datetime.strptime(ev['insc_final'], '%Y-%m-%d').date()
                            
                            st.markdown(f"🗓️ **Evento:** {data_br(ev['data_inicio'])}")
                            st.markdown(f"✍️ **Inscrições:** {data_br(abertura)} a {data_br(fechamento)}")
                            st.markdown(f"👥 **Tamanho do Grupo:** {ev.get('min_membros', 1)} a {ev.get('max_membros', 5)} alunos")

                            if hoje < abertura:
                                st.warning(f"⏳ Inscrições abrem em {data_br(abertura)}")
                            elif hoje > fechamento:
                                st.error("🚫 Inscrições encerradas")
                            else:
                                if st.button(f"🚀 Inscrever Grupo", key=f"btn_ev_{ev['id']}", type="primary", use_container_width=True):
                                    st.session_state.evento_selecionado = ev
                                    st.session_state.fluxo_feira = 'escolher_tema'
                                    st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")

        st.divider()
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # ==========================================
    # PASSO 2: ESCOLHA DO TEMA (COM FILTRO)
    # ==========================================
    elif st.session_state.fluxo_feira == 'escolher_tema':
        evento = st.session_state.evento_selecionado
        st.info(f"📍 **{evento['nome']}** | Público: {serie_aluno} Ano")
        
        try:
            res_temas = supabase_conn.table("feira_temas").select("*").eq("evento_id", evento['id']).execute()
            # Filtra apenas temas da série do aluno ou "Geral"
            temas_filtrados = [t for t in res_temas.data if t.get('Serie') == serie_aluno or t.get('Serie') == "Geral"]

            if not temas_filtrados:
                st.warning("Não há temas disponíveis para sua série neste evento.")
            else:
                st.write("### Escolha uma disciplina:")
                disciplinas = sorted(list(set([t.get('disciplina', 'Outros') for t in temas_filtrados])))
                
                for disc in disciplinas:
                    with st.expander(f"📚 {disc.upper()}"):
                        for t in [x for x in temas_filtrados if x.get('disciplina') == disc]:
                            col_t, col_b = st.columns([3, 1])
                            with col_t:
                                st.markdown(f"**{t['titulo_trabalho']}**")
                                st.caption(f"Orientador: {t['professor_nome']} | Vagas: {t['vagas_grupos']}")
                            with col_b:
                                if st.button("Selecionar", key=f"sel_{t['id']}", type="secondary"):
                                    st.session_state.tema_escolhido = t
                                    # MUDA O ESTADO E AVANÇA PRA ETAPA 3
                                    st.session_state.fluxo_feira = 'adicionar_membros'
                                    st.rerun()
                            st.divider()
        except Exception as e:
            st.error(f"Erro ao carregar temas: {e}")

        if st.button("⬅️ Voltar aos Eventos", use_container_width=True):
            st.session_state.fluxo_feira = 'vitrine'
            st.rerun()

    # ==========================================
    # PASSO 3: FORMAÇÃO DO GRUPO (NOVIDADE AQUI!)
    # ==========================================
    elif st.session_state.fluxo_feira == 'adicionar_membros':
        evento = st.session_state.evento_selecionado
        tema = st.session_state.tema_escolhido
        
        min_membros = evento.get('min_membros', 1)
        max_membros = evento.get('max_membros', 5)

        st.success(f"✅ Tema selecionado: **{tema['titulo_trabalho']}**")
        st.write("### 👥 Formação do Grupo")
        st.info(f"O grupo deve ter entre **{min_membros} e {max_membros} alunos** (incluindo você).")

        with st.form("form_inscricao_final", clear_on_submit=False):
            st.markdown("**Líder do Grupo (Você):**")
            st.text_input("Líder", value=nome_aluno, disabled=True)
            
            st.markdown(f"**Adicione os demais membros (Turma: {turma_aluno}):**")
            
            # Cria os campos dinamicamente baseado no máximo de membros permitido
            membros_nomes = []
            for i in range(2, max_membros + 1):
                # Se for menor que o minimo, é obrigatório preencher
                obrigatorio = " (Obrigatório)" if i <= min_membros else " (Opcional)"
                nome_membro = st.text_input(f"Membro {i}{obrigatorio}", key=f"membro_{i}")
                membros_nomes.append(nome_membro)

            st.divider()
            submit_inscricao = st.form_submit_button("✅ Finalizar Inscrição do Grupo", type="primary", use_container_width=True)

            if submit_inscricao:
                # Filtrar apenas os campos que foram preenchidos
                membros_preenchidos = [m.strip() for m in membros_nomes if m.strip() != ""]
                total_alunos = len(membros_preenchidos) + 1 # +1 porque conta o líder
                
                # Validação de Mínimo e Máximo
                if total_alunos < min_membros:
                    st.error(f"⚠️ O grupo precisa ter no mínimo {min_membros} alunos. Você adicionou apenas {total_alunos}.")
                else:
                    try:
                        # Monta a string com todos os nomes separados por vírgula
                        lista_completa_nomes = f"{nome_aluno} (Líder)"
                        if membros_preenchidos:
                            lista_completa_nomes += ", " + ", ".join(membros_preenchidos)

                        # SALVAR NO BANCO DE DADOS
                        dados_inscricao = {
                            "evento_id": evento['id'],
                            "tema_id": tema['id'],
                            "lider_id": id_aluno,
                            "turma": turma_aluno,
                            "nomes_membros": lista_completa_nomes,
                            "data_inscricao": str(hoje)
                        }
                        
                        # OBS: Certifique-se de que a tabela "feira_inscricoes" existe no Supabase 
                        # com essas colunas acima.
                        supabase_conn.table("feira_inscricoes").insert(dados_inscricao).execute()
                        
                        st.success("🎉 Inscrição realizada com sucesso! Boa sorte no projeto!")
                        time.sleep(2)
                        st.session_state.fluxo_feira = 'vitrine'
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"🚨 Erro ao salvar inscrição: {e}")

        if st.form_submit_button("⬅️ Trocar de Tema", use_container_width=True):
            st.session_state.fluxo_feira = 'escolher_tema'
            st.rerun()