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
            # Forçando a busca para garantir que o Supabase leia a tabela fresca
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
                            
                            # AJUSTE AQUI: Usei os nomes que apareceram no seu print
                            abertura = datetime.datetime.strptime(ev['data_inicio'], '%Y-%m-%d').date()
                            fechamento = datetime.datetime.strptime(ev['data_fim'], '%Y-%m-%d').date()
                            
                            st.markdown(f"🗓️ **Período do Evento:** {data_br(ev['data_inicio'])} a {data_br(ev['data_fim'])}")
                            st.markdown(f"👥 **Tamanho do Grupo:** {ev.get('min_membros', 1)} a {ev.get('max_membros', 5)} alunos")

                            # Lógica de botão
                            if hoje > fechamento:
                                st.error("🚫 Inscrições encerradas")
                            else:
                                if st.button(f"🚀 Inscrever Grupo", key=f"btn_ev_{ev['id']}", type="primary", use_container_width=True):
                                    st.session_state.evento_selecionado = ev
                                    st.session_state.fluxo_feira = 'escolher_tema'
                                    st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")

        st.divider()
        if st.button("⬅️ Voltar ao Menu Principal", use_container_width=True):
            st.session_state.etapa = "ante_sala"
            st.rerun()

    # (O restante do código de temas e membros continua o mesmo, 
    # apenas certifique-se de que feira_temas e feira_inscricoes existam)