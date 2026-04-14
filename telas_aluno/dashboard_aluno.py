import streamlit as st
import pandas as pd
from telas_aluno.desempenho import mostrar_tela_desempenho 

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno
    
    # Cabeçalho de Boas Vindas com Estilo
    st.markdown(f"""
        <div style="margin-bottom: 20px; padding: 15px; background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E2E8F0;">
            <h2 style="margin: 0; color: #1E293B;">👋 Olá, <span style="color: #00C896;">{aluno.get('nome').split()[0]}</span>!</h2>
            <p style="color: #64748b; margin: 0;">{aluno.get('turma')} | Matrícula: {aluno.get('numero_matricula')}</p>
        </div>
    """, unsafe_allow_html=True)

    tab_atividades, tab_concluidas, tab_perfil = st.tabs(["📝 Novas Atividades", "✅ Concluídas", "📊 Meu Desempenho"])

    # Logica para identificar a série (Ex: "2º C" -> "2º Ano")
    turma_bruta = str(aluno.get('turma', ''))
    serie_aluno = turma_bruta[:2] + " Ano" if len(turma_bruta) >= 2 else "1º Ano"

    with st.spinner("Sincronizando atividades..."):
        try:
            # 1. Busca todas as provas visíveis para a série do aluno
            res_p = db_provas.table("modelos_prova")\
                .select("*")\
                .eq("visivel", True)\
                .eq("serie", serie_aluno)\
                .execute()
            provas_disponiveis = res_p.data if res_p.data else []

            # 2. Busca o que o aluno já concluiu
            res_c = db_provas.table("resultados_provas")\
                .select("prova_id, pontuacao")\
                .eq("aluno_id", str(aluno['id']))\
                .execute()
            
            concluidas_ids = [c['prova_id'] for c in res_c.data] if res_c.data else []
            acertos_dict = {c['prova_id']: c['pontuacao'] for c in res_c.data} if res_c.data else {}

        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            provas_disponiveis = []
            concluidas_ids = []

    # --- ABA 1: NOVAS ATIVIDADES ---
    with tab_atividades:
        tem_nova = False
        for p in provas_disponiveis:
            if p['id'] not in concluidas_ids:
                tem_nova = True
                with st.container(border=True):
                    col_t, col_b = st.columns([3, 1])
                    col_t.markdown(f"### {p['titulo']}")
                    col_t.caption(f"📚 Matéria: {p.get('materia', 'Geral')} | ⏱️ {p.get('tempo_limite', 0)} min")
                    
                    if col_b.button("🚀 Iniciar", key=f"play_{p['id']}", use_container_width=True):
                        st.session_state.prova_config = p
                        st.session_state.etapa = "instrucoes"
                        st.rerun()
        
        if not tem_nova:
            st.info(f"Parabéns! Não há novas atividades pendentes para o {serie_aluno}.")

    # --- ABA 2: CONCLUÍDAS ---
    with tab_concluidas:
        tem_concluida = False
        for p in provas_disponiveis:
            if p['id'] in concluidas_ids:
                tem_concluida = True
                pid = p['id']
                with st.container(border=True):
                    col_t, col_b = st.columns([3, 1])
                    col_t.markdown(f"### {p['titulo']}")
                    
                    # Verifica se o professor liberou a visualização da nota
                    notas_liberadas = p.get('notas_liberadas', False)
                    
                    if notas_liberadas:
                        nota_aluno = acertos_dict.get(pid, 0)
                        col_t.markdown(f"✅ **Concluída** &nbsp;|&nbsp; 🎯 **Sua Nota: {nota_aluno}**")
                    else:
                        col_t.markdown("✅ **Concluída** &nbsp;|&nbsp; 🔒 *Nota em processamento*")
                    
                    if col_b.button(f"🔍 Revisar", key=f"rev_{pid}", use_container_width=True):
                        # Lógica para ver revisão se necessário
                        st.info("A funcionalidade de revisão será aberta em breve.")
        
        if not tem_concluida:
            st.info("Você ainda não finalizou nenhuma atividade.")

    # --- ABA 3: MEU DESEMPENHO (Notas da Chamada + Resumo) ---
    with tab_perfil:
        # Enviamos db_alunos (Notas) e db_provas (Atividades) para a tela de desempenho
        mostrar_tela_desempenho(db_alunos, db_provas)