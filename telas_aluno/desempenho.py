import streamlit as st

def mostrar_tela_desempenho(supabase):
    st.markdown(f"### 📊 Meu Desempenho Acadêmico")
    st.write(f"Olá, **{st.session_state.aluno['nome']}**! Aqui você acompanha suas notas registradas.")

    try:
        # Busca as notas usando o ID do aluno logado
        res_notas = supabase.table("notas_atividades")\
            .select("*")\
            .eq("aluno_id", st.session_state.aluno['id'])\
            .eq("unidade", "1º Bimestre")\
            .execute()

        if res_notas.data:
            notas = res_notas.data[0]
            
            # Cálculos automáticos
            n1 = sum([notas.get('at1',0), notas.get('at2',0), notas.get('at3',0), notas.get('at4',0), notas.get('at5',0)])
            n2 = notas.get('prova', 0)
            media = (n1 + n2) / 2

            st.markdown("---")
            st.subheader("📅 1º Trimestre")

            # LINHA ÚNICA COM TODOS OS CAMPOS
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            
            with c1: st.metric("AT1", f"{notas.get('at1', 0):.1f}")
            with c2: st.metric("AT2", f"{notas.get('at2', 0):.1f}")
            with c3: st.metric("AT3", f"{notas.get('at3', 0):.1f}")
            with c4: st.metric("AT4", f"{notas.get('at4', 0):.1f}")
            with c5: st.metric("AT5", f"{notas.get('at5', 0):.1f}")
            with c6: st.metric("PROVA", f"{n2:.1f}")

            # RESUMO FINAL
            st.markdown("---")
            col_res1, col_res2 = st.columns(2)
            
            with col_res1:
                st.markdown(f"**Soma das Atividades (N1):**")
                st.title(f"{n1:.1f}")
            
            with col_res2:
                cor_media = "#00C896" if media >= 6 else "#FF4B4B"
                st.markdown(f"**Média Final:**")
                st.markdown(f"<h1 style='color:{cor_media}; margin-top:-15px;'>{media:.1f}</h1>", unsafe_allow_html=True)

            st.progress(min(media/10, 1.0))
            
            if media >= 6:
                st.success("Parabéns! Você está acima da média.")
            else:
                st.warning("Atenção: Você está abaixo da média esperada. Procure o professor se precisar de ajuda!")

        else:
            st.info("💡 **Ainda não há notas lançadas.**\n\nAssim que o professor registrar suas atividades no sistema, elas aparecerão aqui automaticamente.")

    except Exception as e:
        st.error(f"Erro ao carregar o boletim: {e}")