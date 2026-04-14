import streamlit as st
import pandas as pd

def mostrar_tela_desempenho(supabase_chamada, supabase_av):
    st.markdown("### 📈 Resumo de Aprendizagem")
    
    # 1. NOTAS DO PROJETO CHAMADA
    try:
        res_notas = supabase_chamada.table("notas_atividades")\
            .select("*")\
            .eq("aluno_id", str(st.session_state.aluno['id']))\
            .execute()
        
        if res_notas.data:
            notas = res_notas.data[0]
            st.subheader("📅 Notas do Trimestre")
            cols = st.columns(6)
            for i, label in enumerate(['at1','at2','at3','at4','at5','prova']):
                cols[i].metric(label.upper(), f"{notas.get(label, 0):.1f}")
        else:
            st.info("Notas em processo de lançamento.")
    except:
        st.caption("Sistema de notas temporariamente indisponível.")

    st.markdown("---")
    
    # 2. ATIVIDADES CONCLUÍDAS DO PROJETO AVALIADOR
    st.subheader("✅ Atividades Concluídas")
    try:
        # Busca resultados do aluno
        res_res = supabase_av.table("resultados_provas")\
            .select("*")\
            .eq("aluno_id", str(st.session_state.aluno['id']))\
            .execute()

        if res_res.data:
            ids_provas = [r['prova_id'] for r in res_res.data]
            # Busca nomes das provas
            res_mod = supabase_av.table("modelos_prova")\
                .select("id, titulo, materia")\
                .in_("id", ids_provas)\
                .execute()
            
            mapa_provas = {p['id']: p for p in res_mod.data}

            for r in res_res.data:
                info = mapa_provas.get(r['prova_id'], {})
                with st.expander(f"✅ {info.get('titulo', 'Simulado Concluído')}"):
                    c1, c2 = st.columns(2)
                    c1.metric("Sua Nota", f"{r.get('pontuacao', 0)}")
                    c2.write(f"**Matéria:** {info.get('materia', 'Geral')}")
                    st.caption(f"Concluído em: {r.get('created_at')[:10]}")
        else:
            st.write("Ainda não tens atividades concluídas.")
    except Exception as e:
        st.write("A carregar histórico...")