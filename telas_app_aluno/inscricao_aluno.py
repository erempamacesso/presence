import streamlit as st

def mostrar_inscricao_aluno(supabase_conn):
    st.title("🚀 Eventos Disponíveis")
    st.write("Tentando conectar com o banco de dados...")

    try:
        # Busca simples e direta na tabela
        res = supabase_conn.table("feira_eventos").select("*").eq("ativo", True).execute()
        eventos = res.data

        if not eventos:
            st.warning("A conexão funcionou, mas não há eventos ativos cadastrados.")
        else:
            st.success("✅ Conexão perfeita! Tabela encontrada com sucesso.")
            
            # Mostra os eventos encontrados de forma simples
            for ev in eventos:
                with st.container(border=True):
                    st.subheader(ev.get('nome', 'Sem nome'))
                    st.write(f"📅 **Data:** {ev.get('data_inicio')} até {ev.get('data_fim')}")
                    st.write(f"👥 **Equipes de:** {ev.get('min_membros')} a {ev.get('max_membros')} alunos")
                    
    except Exception as e:
        # Se der o erro PGRST205, ele vai aparecer aqui
        st.error(f"🚨 Erro na conexão com o banco: {e}")

    st.divider()
    
    # Botão para voltar
    if st.button("⬅️ Voltar para o Menu", type="secondary"):
        st.session_state.etapa = "ante_sala"
        st.rerun()