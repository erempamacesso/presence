import streamlit as st
import pandas as pd
import json
import time
import re
from telas.config_frentes import FRENTES

def mostrar_tela_biblioteca(supabase):
    st.title("📚 Biblioteca de Questões")

    res_q = supabase.table("questoes").select("*").order("id", desc=True).execute()

    if res_q.data:
        df_q = pd.DataFrame(res_q.data)

        if 'serie' not in df_q.columns: df_q['serie'] = "Geral"
        if 'assunto' not in df_q.columns: df_q['assunto'] = "Sem Assunto"
        if 'frente' not in df_q.columns: df_q['frente'] = ""
        if 'revisada' not in df_q.columns: df_q['revisada'] = False
        df_q['revisada'] = df_q['revisada'].fillna(False)
        df_q['assunto'] = df_q['assunto'].fillna("Sem Assunto")
        df_q['frente'] = df_q['frente'].fillna("")

        def clean_html(raw_html):
            if not raw_html: return ""
            cleanr = re.compile('<.*?>')
            cleantext = re.sub(cleanr, '', str(raw_html))
            return cleantext[:80] + "..." if len(cleantext) > 80 else cleantext

        # --- BLOCO DE FILTROS ---
        st.write("### 🔍 Filtrar Biblioteca")
        col_f1, col_f2, col_f3, col_f4 = st.columns([1.2, 1.5, 1.5, 1.2])

        with col_f1:
            series_list = sorted(df_q['serie'].unique())
            filtro_serie = st.multiselect("Por Série:", options=series_list)

        # Filtro dinâmico de assunto baseado na série
        df_temp = df_q.copy()
        if filtro_serie:
            df_temp = df_temp[df_temp['serie'].isin(filtro_serie)]

        with col_f2:
            assuntos_list = sorted(df_temp['assunto'].unique())
            filtro_assunto = st.multiselect("Por Assunto:", options=assuntos_list)

        with col_f3:
            filtro_frente = st.multiselect(
                "Por Frente:",
                options=FRENTES,
                format_func=lambda x: x,
            )

        with col_f4:
            filtro_rev = st.selectbox("Status:", ["Todas", "✅ Revisadas", "⚠️ Pendentes"])

        # Aplicando os filtros
        if filtro_serie: df_q = df_q[df_q['serie'].isin(filtro_serie)]
        if filtro_assunto: df_q = df_q[df_q['assunto'].isin(filtro_assunto)]
        if filtro_frente: df_q = df_q[df_q['frente'].isin(filtro_frente)]

        if filtro_rev == "✅ Revisadas": df_q = df_q[df_q['revisada'] == True]
        elif filtro_rev == "⚠️ Pendentes": df_q = df_q[df_q['revisada'] == False]

        st.write(f"Exibindo **{len(df_q)}** questões")
        st.divider()

        # --- LISTAGEM EM FORMATO SANFONA ---
        for _, row in df_q.iterrows():
            is_rev = row.get('revisada', False)
            status_icon = "✅" if is_rev else "⚠️"
            frente_txt = row.get('frente', '') or ''

            titulo_expander = f"{status_icon} 📌 {row['assunto']} | {clean_html(row['enunciado'])}"

            with st.expander(titulo_expander):
                if not is_rev:
                    st.warning("Questão PENDENTE de revisão (imagens ou texto).")

                serie_info = row['serie']
                assunto_info = row['assunto']
                frente_label = frente_txt if frente_txt else "—"
                st.caption(f"📍 Série: {serie_info} | Assunto: {assunto_info} | Frente: {frente_label}")

                st.markdown(row['enunciado'], unsafe_allow_html=True)

                st.write("**Alternativas:**")
                alts = row.get('alternativas', {})
                if isinstance(alts, str):
                    try: alts = json.loads(alts.replace("'", '"'))
                    except: alts = {}

                resposta_certa = row.get('resposta_correta', 'A')

                if isinstance(alts, dict):
                    for letra in ["A", "B", "C", "D", "E"]:
                        item = alts.get(letra, "")
                        if not item: continue

                        txt_alt = item.get("texto", "") if isinstance(item, dict) else str(item)
                        url_img = item.get("imagem", "") if isinstance(item, dict) else ""

                        cor = "green" if letra == resposta_certa else "black"
                        marcador = "✅" if letra == resposta_certa else "⚪"

                        st.markdown(f"<span style='color:{cor}'>{marcador} **{letra})** {txt_alt}</span>", unsafe_allow_html=True)
                        if url_img: st.image(url_img, width=250)

                st.divider()

                col_del, col_vazio = st.columns([1, 4])
                if col_del.button("🗑️ Excluir", key=f"del_{row['id']}", type="secondary", use_container_width=True):
                    try:
                        supabase.table("questoes").delete().eq("id", row['id']).execute()
                        st.toast(f"Questão {row['id']} removida!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
    else:
        st.info("Nenhuma questão encontrada com esses filtros.")
