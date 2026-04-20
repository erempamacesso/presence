import streamlit as st
import pandas as pd
import json
import time

def mostrar_tela_biblioteca(supabase):
    st.title("📚 Biblioteca de Questões")
    
    res_q = supabase.table("questoes").select("*").order("id", desc=True).execute()
    
    if res_q.data:
        df_q = pd.DataFrame(res_q.data)
        
        # Proteção de colunas
        if 'serie' not in df_q.columns: df_q['serie'] = "Geral"
        if 'assunto' not in df_q.columns: df_q['assunto'] = ""
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_serie = st.multiselect("Filtrar por Série:", options=sorted(df_q['serie'].dropna().unique()))
        with col_f2:
            busca_assunto = st.text_input("Buscar por Assunto:")

        if filtro_serie: df_q = df_q[df_q['serie'].isin(filtro_serie)]
        if busca_assunto: df_q = df_q[df_q['assunto'].str.contains(busca_assunto, case=False, na=False)]

        st.write(f"Total de questões encontradas: **{len(df_q)}**")
        st.divider()

        for index, row in df_q.iterrows():
            str_serie = row.get('serie', '')
            str_assunto = row.get('assunto', '')
            
            # --- Título do expander ---
            with st.expander(f"📖 {str_serie} | Assunto: {str_assunto}"):
                st.markdown(row['enunciado'], unsafe_allow_html=True)
                
                st.write("**Alternativas:**")
                
                alts = row.get('alternativas', {})
                if isinstance(alts, str):
                    try:
                        alts = json.loads(alts.replace("'", '"'))
                    except:
                        alts = {}
                
                resposta_certa = row.get('resposta_correta', 'A')

                if isinstance(alts, dict):
                    for letra in ["A", "B", "C", "D"]:
                        item = alts.get(letra, "")
                        
                        if isinstance(item, dict):
                            txt_alt = item.get("texto", "")
                            url_img = item.get("imagem", "")
                        else:
                            txt_alt = str(item)
                            url_img = ""

                        cor = "green" if letra == resposta_certa else "black"
                        marcador = "✅" if letra == resposta_certa else "⚪"
                        
                        st.markdown(f"<span style='color:{cor}'>{marcador} **{letra})** {txt_alt}</span>", unsafe_allow_html=True)
                        
                        if url_img:
                            st.image(url_img, width=200)
                
                st.divider()
                # O ID continua sendo usado apenas "por baixo dos panos" no botão de excluir
                if st.button("🗑️ Excluir Questão", key=f"del_{row['id']}", type="secondary"):
                    try:
                        supabase.table("questoes").delete().eq("id", row['id']).execute()
                        st.success("Questão removida!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
    else:
        st.info("Nenhuma questão na biblioteca.")