import streamlit as st
import pandas as pd
from telas_aluno.desempenho import mostrar_tela_desempenho 

def mostrar_tela_dashboard(db_provas, supabase_provas_for_desempenho):
    aluno = st.session_state.aluno
    
    # Cabeçalho de Boas Vindas
    st.markdown(f"""
        <div style="margin-bottom: 20px; padding: 15px; background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E2E8F0;">
            <h2 style="margin: 0; color: #1E293B;">👋 Olá, <span style="color: #00C896;">{aluno.get('nome').split()[0]}</span>!</h2>
            <p style="color: #64748b; margin: 0;">{aluno.get('turma')} | Matrícula: {aluno.get('numero_matricula')}</p>
        </div>
    """, unsafe_allow_html=True)

    tab_atividades, tab_concluidas, tab_perfil = st.tabs(["📝 Novas Atividades", "✅ Concluídas", "📊 Meu Desempenho"])

    with st.spinner("Buscando atividades..."):
        turma_bruta = str(aluno.get('turma', ''))
        serie_aluno = "1º Ano"
        if "2" in turma_bruta: serie_aluno = "2º Ano"
        elif "3" in turma_bruta: serie_aluno = "3º Ano"

        res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).execute()
        provas_ativas = res_p.data
        
        # --- BUSCA AVANÇADA DE RESULTADOS ---
        # Agora buscamos também o campo "acertou" para calcular a nota!
        ja_fez_dict = {}
        acertos_dict = {}
        
        if provas_ativas:
            ids_ativas = [p['id'] for p in provas_ativas]
            res_JF = db_provas.table("resultados_provas").select("prova_id, acertou").eq("aluno_id", str(aluno.get('id', ''))).in_("prova_id", ids_ativas).execute()
            
            for r in res_JF.data:
                pid = r['prova_id']
                ja_fez_dict[pid] = True
                
                # Conta os acertos do aluno naquela prova
                if pid not in acertos_dict:
                    acertos_dict[pid] = 0
                if r.get('acertou') == True:
                    acertos_dict[pid] += 1

    # --- ABA 1: PROVAS PENDENTES ---
    with tab_atividades:
        tem_nova = False
        if provas_ativas:
            for p in provas_ativas:
                if not ja_fez_dict.get(p['id'], False):
                    tem_nova = True
                    with st.container(border=True):
                        col_t, col_b = st.columns([3, 1])
                        col_t.markdown(f"### {p['titulo']}")
                        col_t.caption(f"📚 Assunto: {p.get('assunto', 'Geral')} | ⏱️ {p.get('tempo_duracao', 0)} min")
                        
                        if col_b.button(f"🚀 Iniciar", key=f"start_{p['id']}", type="primary", use_container_width=True):
                            st.session_state.prova_config = p
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
        
        if not tem_nova:
            st.info("🎉 Parabéns! Você não tem nenhuma atividade nova pendente.")

    # --- ABA 2: PROVAS CONCLUÍDAS (AGORA COM NOTAS!) ---
    with tab_concluidas:
        tem_concluida = False
        if provas_ativas:
            for p in provas_ativas:
                pid = p['id']
                if ja_fez_dict.get(pid, False):
                    tem_concluida = True
                    with st.container(border=True):
                        col_t, col_b = st.columns([3, 1])
                        col_t.markdown(f"### {p['titulo']}")
                        
                        # Verifica se o professor liberou a nota (cadeado aberto)
                        notas_liberadas = p.get('notas_liberadas', False)
                        
                        if notas_liberadas:
                            # Se o cadeado estiver aberto, calcula a nota e mostra!
                            valor_cada = p.get('valor_questao', 1.0)
                            acertos_aluno = acertos_dict.get(pid, 0)
                            nota_final = acertos_aluno * valor_cada
                            
                            col_t.markdown(f"✅ **Concluída** &nbsp;|&nbsp; 🎯 **Sua Nota: {nota_final:.1f}**")
                        else:
                            # Se o cadeado estiver fechado, faz suspense
                            col_t.markdown("✅ **Concluída** &nbsp;|&nbsp; 🔒 *Nota em avaliação pelo professor*")
                        
                        if col_b.button(f"🔍 Ver Resultado", key=f"res_{pid}", use_container_width=True):
                            st.session_state.prova_resultado = p
                            st.session_state.etapa = "ver_meu_resultado"
                            st.rerun()
        
        if not tem_concluida:
            st.info("Você ainda não concluiu nenhuma atividade desta lista.")

    # --- ABA 3: DESEMPENHO TRIMESTRAL ---
    with tab_perfil:
        mostrar_tela_desempenho(supabase_provas_for_desempenho)