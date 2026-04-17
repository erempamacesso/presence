import streamlit as st
import datetime
import time

def mostrar_tela_inscricao_feira(supabase_conn):
    st.title("ALUNO EREMPAM")
    st.subheader("🎪 Inscrição - Eventos e Feiras")
    
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
        
        try:
            # Busca os eventos ativos
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
                            
                            # CORREÇÃO DOS NOMES DAS COLUNAS CONFORME SEU PRINT:
                            # Usamos 'data_inicio' e 'data_fim' que é o que está no seu banco
                            data_evento_inicio = datetime.datetime.strptime(ev['data_inicio'], '%Y-%m-%d').date()
                            data_evento_fim = datetime.datetime.strptime(ev['data_fim'], '%Y-%m-%d').date()
                            
                            st.markdown(f"🗓️ **Período:** {data_br(ev['data_inicio'])} até {data_br(ev['data_fim'])}")
                            st.markdown(f"👥 **Grupo:** {ev.get('min_membros', 1)} a {ev.get('max_membros', 5)} alunos")

                            # Lógica simplificada: Se hoje está antes do fim do evento, pode inscrever
                            if hoje > data_evento_fim:
                                st.error("🚫 Evento encerrado")
                            else:
                                if st.button(f"🚀 Inscrever Grupo", key=f"btn_ev_{ev['id']}", type="primary", use_container_width=True):
                                    st.session_state.evento_selecionado = ev
                                    st.session_state.fluxo_feira = 'escolher_tema'
                                    st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")

        st.divider()
        if st.button("⬅️ Voltar ao Menu", use_container_width=True):
            st.session_state.etapa = "ante_sala"
            st.rerun()

    # ==========================================
    # PASSO 2: ESCOLHA DO TEMA
    # ==========================================
    elif st.session_state.fluxo_feira == 'escolher_tema':
        evento = st.session_state.evento_selecionado
        st.info(f"📍 **{evento['nome']}**")
        
        try:
            # Busca temas ligados a esse evento
            res_temas = supabase_conn.table("feira_temas").select("*").eq("evento_id", evento['id']).execute()
            temas = res_temas.data

            if not temas:
                st.warning("Ainda não há temas cadastrados para este evento.")
            else:
                # Filtra pela série do aluno
                temas_filtrados = [t for t in temas if t.get('Serie') == serie_aluno or t.get('Serie') == "Geral"]
                
                if not temas_filtrados:
                    st.warning(f"Não há temas específicos para o {serie_aluno} ano.")
                else:
                    for t in temas_filtrados:
                        with st.container(border=True):
                            st.write(f"**{t['titulo_trabalho']}**")
                            st.caption(f"Orientador: {t['professor_nome']} | Disciplina: {t['disciplina']}")
                            if st.button("Selecionar Tema", key=f"sel_{t['id']}", use_container_width=True):
                                st.session_state.tema_escolhido = t
                                st.session_state.fluxo_feira = 'adicionar_membros'
                                st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar temas: {e}")

        if st.button("⬅️ Voltar", use_container_width=True):
            st.session_state.fluxo_feira = 'vitrine'
            st.rerun()

    # ==========================================
    # PASSO 3: ADICIONAR MEMBROS E SALVAR
    # ==========================================
    elif st.session_state.fluxo_feira == 'adicionar_membros':
        evento = st.session_state.evento_selecionado
        tema = st.session_state.tema_escolhido
        
        st.success(f"✅ Tema: {tema['titulo_trabalho']}")
        
        with st.form("form_final"):
            st.write("### 👥 Membros do Grupo")
            st.info(f"Mínimo: {evento['min_membros']} | Máximo: {evento['max_membros']}")
            
            # Líder fixo
            st.text_input("Líder (Você)", value=nome_aluno, disabled=True)
            
            # Inputs para outros membros
            outros_membros = st.text_area("Nomes dos outros membros (um por linha)", help="Não inclua o seu nome aqui.")
            
            if st.form_submit_button("CONCLUIR INSCRIÇÃO", type="primary", use_container_width=True):
                # Validação simples de quantidade
                lista_membros = [m.strip() for m in outros_membros.split('\n') if m.strip()]
                total = len(lista_membros) + 1 # +1 do líder
                
                if total < int(evento['min_membros']):
                    st.error(f"O grupo precisa de pelo menos {evento['min_membros']} integrantes.")
                elif total > int(evento['max_membros']):
                    st.error(f"O grupo pode ter no máximo {evento['max_membros']} integrantes.")
                else:
                    try:
                        nomes_finais = f"{nome_aluno} (Líder), " + ", ".join(lista_membros)
                        
                        dados = {
                            "evento_id": evento['id'],
                            "tema_id": tema['id'],
                            "lider_id": id_aluno,
                            "turma": turma_aluno,
                            "nomes_membros": nomes_finais,
                            "data_inscricao": str(hoje)
                        }
                        
                        supabase_conn.table("feira_inscricoes").insert(dados).execute()
                        st.balloons()
                        st.success("Inscrição Confirmada!")
                        time.sleep(2)
                        st.session_state.fluxo_feira = 'vitrine'
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

        if st.button("⬅️ Trocar Tema"):
            st.session_state.fluxo_feira = 'escolher_tema'
            st.rerun()