import streamlit as st
import pandas as pd
import json
import time
import re

def mostrar_tela_biblioteca(supabase):
    st.title("📚 Biblioteca de Questões")
    
    # Busca todas as questões
    res_q = supabase.table("questoes").select("*").order("id", desc=True).execute()
    
    if res_q.data:
        df_q = pd.DataFrame(res_q.data)
        
        # Proteção e limpeza de colunas
        if 'serie' not in df_q.columns: df_q['serie'] = "Geral"
        if 'assunto' not in df_q.columns: df_q['assunto'] = "Sem Assunto"
        if 'revisada' not in df_q.columns: df_q['revisada'] = False
        df_q['revisada'] = df_q['revisada'].fillna(False)
        df_q['assunto'] = df_q['assunto'].fillna("Sem Assunto")

        # Função para limpar HTML do enunciado para o título da sanfona
        def clean_html(raw_html):
            if not raw_html: return ""
            cleanr = re.compile('<.*?>')
            cleantext = re.sub(cleanr, '', str(raw_html))
            return cleantext[:80] + "..." if len(cleantext) > 80 else cleantext

        # --- BLOCO DE FILTROS ---
        st.write("### 🔍 Filtrar Biblioteca")
        col_f1, col_f2, col_f3 = st.columns([1.5, 2, 1.2])
        
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
            filtro_rev = st.selectbox("Status:", ["Todas", "✅ Revisadas", "⚠️ Pendentes"])

        # Aplicando os filtros no DF final
        if filtro_serie: df_q = df_q[df_q['serie'].isin(filtro_serie)]
        if filtro_assunto: df_q = df_q[df_q['assunto'].isin(filtro_assunto)]
        
        if filtro_rev == "✅ Revisadas": df_q = df_q[df_q['revisada'] == True]
        elif filtro_rev == "⚠️ Pendentes": df_q = df_q[df_q['revisada'] == False]

        st.write(f"Exibindo **{len(df_q)}** questões")
        st.divider()

        # --- LISTAGEM EM FORMATO SANFONA ---
        for index, row in df_q.iterrows():
            is_rev = row.get('revisada', False)
            status_icon = "✅" if is_rev else "⚠️"
            
            # Título: Ícone + Assunto + Resumo Enunciado
            titulo_expander = f"{status_icon} 📌 {row['assunto']} | {clean_html(row['enunciado'])}"
            
            with st.expander(titulo_expander):
                if not is_rev:
                    st.warning("Questão PENDENTE de revisão (imagens ou texto).")
                
                # Exibe Série e Assunto como tags
                st.caption(f"📍 Série: {row['serie']} | Assunto: {row['assunto']}")
                
                # Conteúdo do Enunciado
                st.markdown(row['enunciado'], unsafe_allow_html=True)
                
                # Alternativas
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
                        
                        # Extrai texto e imagem se for dicionário
                        txt_alt = item.get("texto", "") if isinstance(item, dict) else str(item)
                        url_img = item.get("imagem", "") if isinstance(item, dict) else ""

                        cor = "green" if letra == resposta_certa else "black"
                        marcador = "✅" if letra == resposta_certa else "⚪"
                        
                        st.markdown(f"<span style='color:{cor}'>{marcador} **{letra})** {txt_alt}</span>", unsafe_allow_html=True)
                        if url_img: st.image(url_img, width=250)
                
                st.divider()
                
                # BOTÃO DE EXCLUIR DENTRO DA SANFONA
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