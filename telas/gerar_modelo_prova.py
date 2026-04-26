import streamlit as st
import pandas as pd
import re
import time

# --- CAÇADOR DE ERROS DO MOTOR WORD ---
erro_motor = None
try:
    from exportador import gerar_prova_word
except ImportError as e1:
    try:
        from telas.exportador import gerar_prova_word
    except Exception as e2:
        erro_motor = f"Erro local: {e1} | Erro na pasta: {e2}"
except Exception as e3:
    erro_motor = f"Erro fatal: {e3}"

def mostrar_tela_gerar_modelo(supabase):
    st.title("📄 Gerar Novo Modelo de Prova")

    # --- INICIALIZAÇÃO DA MEMÓRIA DE SELEÇÃO ---
    if 'ids_persistentes' not in st.session_state:
        st.session_state.ids_persistentes = set()

    # --- CONFIGURAÇÕES BÁSICAS DA PROVA ---
    c1, c2 = st.columns([3, 1])
    titulo = c1.text_input("Título da Prova", placeholder="Ex: 1ª Avaliação de Química - 2º Bimestre")
    valor = c2.number_input("Valor por questão", min_value=0.1, value=1.0, step=0.1)
    
    # ATENÇÃO: Mudamos para select("*") para o Word conseguir ler as alternativas (A, B, C...)
    res_q = supabase.table("questoes").select("*").order("id", desc=True).execute()
    
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
        
        # ==========================================
        # BOTÕES DE AÇÃO (SALVAR ONLINE VS IMPRIMIR)
        # ==========================================
        st.write("### 🚀 O que deseja fazer com essas questões?")
        
        col_b1, col_b2 = st.columns(2)
        
        # BOTÃO 1: Salvar no Banco (Para os alunos fazerem online)
        with col_b1:
            if st.button("💾 Salvar como Atividade Online", type="primary", use_container_width=True):
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
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar a prova: {e}")

        # BOTÃO 2: Gerar Word (Não salva no banco, apenas baixa)
        with col_b2:
            if total_selecionadas > 0:
                # Filtra os dados reais das questões selecionadas para enviar ao Word
                questoes_para_word = df_base[df_base['id'].isin(st.session_state.ids_persistentes)].to_dict('records')
                
                if 'gerar_prova_word' in globals():
                    try:
                        nome_arquivo = titulo if titulo else "Prova_Fisica"
                        arquivo_docx = gerar_prova_word(nome_arquivo, questoes_para_word)
                        
                        st.download_button(
                            label="📄 Baixar Word (Apenas Impressão)",
                            data=arquivo_docx,
                            file_name=f"{nome_arquivo}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            help="Baixa o documento Word sem disponibilizar a prova no portal dos alunos."
                        )
                    except Exception as e:
                        st.error(f"Erro na conversão: {e}")
                else:
                    st.error("⚠️ Sistema de Word não carregado. Verifique a instalação do python-docx.")
            else:
                st.button("📄 Baixar Word (Apenas Impressão)", disabled=True, use_container_width=True)

    else:
        st.warning("Não há questões cadastradas.")