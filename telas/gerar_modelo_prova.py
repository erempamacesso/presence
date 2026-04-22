import streamlit as st
import pandas as pd
import re

def mostrar_tela_gerar_modelo(supabase):
    st.title("📄 Gerar Novo Modelo de Prova")
    
    # --- CONFIGURAÇÕES BÁSICAS DA PROVA ---
    c1, c2 = st.columns([3, 1])
    titulo = c1.text_input("Título da Prova", placeholder="Ex: 1ª Avaliação de Química - 2º Bimestre")
    valor = c2.number_input("Valor por questão", min_value=0.1, value=1.0, step=0.1)
    
    # Puxa as questões do banco
    res_q = supabase.table("questoes").select("id, serie, assunto, enunciado").order("id", desc=True).execute()
    
    if res_q.data:
        df_base = pd.DataFrame(res_q.data)
        
        # Função para limpar HTML do enunciado para o título da sanfona
        def clean_html(raw_html):
            if not raw_html: return ""
            cleanr = re.compile('<.*?>')
            cleantext = re.sub(cleanr, '', str(raw_html))
            return cleantext[:100] + "..." if len(cleantext) > 100 else cleantext

        # --- FILTROS (LADO A LADO) ---
        st.write("### 🔍 Filtros de Busca")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            series_disponiveis = sorted(df_base['serie'].dropna().unique())
            filtro_serie = st.multiselect("Filtrar por Série:", options=series_disponiveis)
        
        # Aplica filtro de série primeiro para o filtro de assunto ser dinâmico
        df_filtrado = df_base.copy()
        if filtro_serie:
            df_filtrado = df_filtrado[df_filtrado['serie'].isin(filtro_serie)]
            
        with col_f2:
            assuntos_disponiveis = sorted(df_filtrado['assunto'].dropna().unique())
            filtro_assunto = st.multiselect("Filtrar por Assunto:", options=assuntos_disponiveis)
        
        if filtro_assunto:
            df_filtrado = df_filtrado[df_filtrado['assunto'].isin(filtro_assunto)]

        st.divider()

        # --- LISTA DE SELEÇÃO (FORMATO SANFONA) ---
        st.write(f"### 📝 Questões Encontradas ({len(df_filtrado)})")
        st.info("Selecione as questões marcando o checkbox à esquerda. Clique no título para expandir o enunciado completo.")

        # Criamos uma lista para armazenar os IDs selecionados
        ids_selecionados = []

        # Área de rolagem para não esticar a página infinitamente
        container_questoes = st.container()
        
        with container_questoes:
            for _, row in df_filtrado.iterrows():
                # Layout: Checkbox pequeno e Expander grande ao lado
                col_check, col_exp = st.columns([0.05, 0.95])
                
                # O checkbox usa o ID da questão como chave única
                selecionada = col_check.checkbox("", key=f"sel_{row['id']}")
                
                if selecionada:
                    ids_selecionados.append(row['id'])
                
                # Expander com o enunciado
                with col_exp.expander(f"ID: {row['id']} | {row['assunto']} | {clean_html(row['enunciado'])}"):
                    st.markdown(row['enunciado'], unsafe_allow_html=True)
        
        st.divider()
        st.info(f"Quantidade de questões selecionadas para esta prova: **{len(ids_selecionados)}**")
        
        # --- BOTÃO DE SALVAR PROVA ---
        if st.button("🔨 Gerar Prova e Salvar", type="primary", use_container_width=True):
            if not titulo:
                st.error("❌ Dê um título para a prova!")
            elif len(ids_selecionados) == 0:
                st.error("❌ Selecione pelo menos 1 questão!")
            else:
                dados_prova = {
                    "titulo": titulo, 
                    "questoes_ids": ids_selecionados, # Agora enviamos direto a lista de IDs
                    "valor_questao": float(valor), 
                    "ativa": True
                }
                
                try:
                    supabase.table("modelos_prova").insert(dados_prova).execute()
                    st.success(f"✅ Prova '{titulo}' gerada com sucesso contendo {len(ids_selecionados)} questões!")
                    st.balloons()
                    # Pequeno delay para o usuário ver o sucesso antes de resetar se necessário
                except Exception as e:
                    st.error(f"Erro ao salvar a prova no banco: {e}")
    else:
        st.warning("Não há questões cadastradas no banco de dados.")