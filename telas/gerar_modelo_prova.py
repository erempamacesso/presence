import streamlit as st
import pandas as pd
import re
import time  # <--- ADICIONADO PARA CORRIGIR O ERRO

def mostrar_tela_gerar_modelo(supabase):
    st.title("📄 Gerar Novo Modelo de Prova")

    # --- INICIALIZAÇÃO DA MEMÓRIA DE SELEÇÃO ---
    if 'ids_persistentes' not in st.session_state:
        st.session_state.ids_persistentes = set()

    # --- CONFIGURAÇÕES BÁSICAS DA PROVA ---
    c1, c2 = st.columns([3, 1])
    titulo = c1.text_input("Título da Prova", placeholder="Ex: 1ª Avaliação de Química - 2º Bimestre")
    valor = c2.number_input("Valor por questão", min_value=0.1, value=1.0, step=0.1)
    
    # Puxa as questões do banco
    res_q = supabase.table("questoes").select("id, serie, assunto, enunciado").order("id", desc=True).execute()
    
    if res_q.data:
        df_base = pd.DataFrame(res_q.data)
        
        def clean_html(raw_html):
            if not raw_html: return ""
            cleanr = re.compile('<.*?>')
            cleantext = re.sub(cleanr, '', str(raw_html))
            return cleantext[:100] + "..." if len(cleantext) > 100 else cleantext

        # --- FILTROS ---
        st.write("### 🔍 Filtros de Busca")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            series_disponiveis = sorted(df_base['serie'].dropna().unique())
            filtro_serie = st.multiselect("Filtrar por Série:", options=series_disponiveis)
        
        df_filtrado = df_base.copy()
        if filtro_serie:
            df_filtrado = df_filtrado[df_filtrado['serie'].isin(filtro_serie)]
            
        with col_f2:
            assuntos_disponiveis = sorted(df_filtrado['assunto'].dropna().unique())
            filtro_assunto = st.multiselect("Filtrar por Assunto:", options=assuntos_disponiveis)
        
        if filtro_assunto:
            df_filtrado = df_filtrado[df_filtrado['assunto'].isin(filtro_assunto)]

        st.divider()

        # --- BOTÃO PARA LIMPAR TUDO ---
        if len(st.session_state.ids_persistentes) > 0:
            if st.button("🗑️ Limpar toda a seleção atual"):
                st.session_state.ids_persistentes = set()
                st.rerun()

        # --- LISTA DE SELEÇÃO ---
        st.write(f"### 📝 Questões Encontradas ({len(df_filtrado)})")
        
        container_questoes = st.container()
        
        with container_questoes:
            for _, row in df_filtrado.iterrows():
                id_atual = row['id']
                col_check, col_exp = st.columns([0.05, 0.95])
                
                # Verifica se o ID já está na memória
                ja_selecionada = id_atual in st.session_state.ids_persistentes
                
                selecionada = col_check.checkbox("", value=ja_selecionada, key=f"sel_{id_atual}")
                
                if selecionada:
                    st.session_state.ids_persistentes.add(id_atual)
                else:
                    st.session_state.ids_persistentes.discard(id_atual)
                
                titulo_expander = f"📌 {row['assunto']} | {clean_html(row['enunciado'])}"
                with col_exp.expander(titulo_expander):
                    st.markdown(row['enunciado'], unsafe_allow_html=True)
        
        st.divider()
        total_selecionadas = len(st.session_state.ids_persistentes)
        st.info(f"Total de questões selecionadas (acumulado): **{total_selecionadas}**")
        
        # --- BOTÃO DE SALVAR PROVA ---
        if st.button("🔨 Gerar Prova e Salvar", type="primary", use_container_width=True):
            if not titulo:
                st.error("❌ Dê um título para a prova!")
            elif total_selecionadas == 0:
                st.error("❌ Selecione pelo menos 1 questão!")
            else:
                dados_prova = {
                    "titulo": titulo, 
                    "questoes_ids": list(st.session_state.ids_persistentes), 
                    "valor_questao": float(valor), 
                    "ativa": True
                }
                
                try:
                    supabase.table("modelos_prova").insert(dados_prova).execute()
                    st.success(f"✅ Prova '{titulo}' gerada com {total_selecionadas} questões!")
                    st.session_state.ids_persistentes = set()
                    st.balloons()
                    time.sleep(2) # Agora o 'time' vai funcionar!
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar a prova: {e}")
    else:
        st.warning("Não há questões cadastradas.")