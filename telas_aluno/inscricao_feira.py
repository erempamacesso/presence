import streamlit as st

def mostrar_tela_inscricao_feira(supabase_conn):
    st.title("🎪 Inscrição - Feira de Ciências")
    
    aluno = st.session_state.get('aluno', {})
    turma_aluno = aluno.get('turma', 'Sem Turma')
    id_aluno = aluno.get('id')

    st.info(f"📍 Olá Líder! Sua turma é: **{turma_aluno}**")

    # 1. BUSCAR QUAIS DISCIPLINAS A TURMA JÁ OCUPOU
    try:
        res_inscricoes = supabase_conn.table("feira_inscricoes").select("disciplina").eq("turma", turma_aluno).execute()
        disciplinas_ocupadas = [ins["disciplina"] for ins in res_inscricoes.data]
    except:
        disciplinas_ocupadas = []

    # 2. BUSCAR TODOS OS TEMAS CADASTRADOS PELOS PROFESSORES
    try:
        res_temas = supabase_conn.table("feira_temas").select("*").execute()
        todos_temas = res_temas.data if res_temas.data else []
    except Exception as e:
        st.error(f"Erro ao carregar temas: {e}")
        return

    st.markdown("### Selecione o Segmento")
    
    segmentos = ["Química", "Física", "Biologia", "Matemática"]
    icons = {"Química": "🧪", "Física": "⚛️", "Biologia": "🧬", "Matemática": "📐"}

    for seg in segmentos:
        label = f"{icons[seg]} {seg}"
        
        # VERIFICAÇÃO DE TRAVA: A turma já tem grupo nessa disciplina?
        if seg in disciplinas_ocupadas:
            with st.expander(f"🔒 {label} - (Indisponível para sua turma)"):
                st.warning(f"Sua turma ({turma_aluno}) já possui um grupo inscrito em {seg}.")
        
        else:
            with st.expander(f"📂 {label} - (Disponível)"):
                # Filtra os temas que pertencem a este segmento
                # (Assumindo que você criou a coluna 'disciplina' em feira_temas)
                temas_do_segmento = [t for t in todos_temas if t.get('disciplina') == seg]
                
                if not temas_do_segmento:
                    st.write("Nenhum tema cadastrado para este segmento ainda.")
                else:
                    st.write("Escolha um dos temas abaixo:")
                    
                    # Criamos uma lista formatada para o Radio Button
                    opcoes = {f"{t['nome']}": t['id'] for t in temas_do_segmento}
                    escolha = st.radio("Temas:", list(opcoes.keys()), key=f"radio_{seg}")
                    
                    id_tema_escolhido = opcoes[escolha]
                    
                    if st.button(f"🚀 Inscrever meu grupo em {seg}", key=f"btn_{seg}"):
                        st.session_state.dados_inscricao = {
                            "tema_id": id_tema_escolhido,
                            "tema_nome": escolha,
                            "disciplina": seg,
                            "turma": turma_aluno,
                            "lider_id": id_aluno
                        }
                        # No próximo passo criaremos a tela de selecionar os colegas
                        st.success(f"Tema '{escolha}' selecionado! Agora vamos adicionar seus colegas.")
                        # st.session_state.etapa_feira = "selecionar_membros"
                        # st.rerun()

    if st.button("⬅️ Voltar ao Painel"):
        st.session_state.etapa = "ante_sala"
        st.rerun()