import streamlit as st
import pandas as pd
import re

def mostrar_tela_gerar_modelo(supabase):
    st.title("📄 Gerar Novo Modelo de Prova")
    
    # --- CONFIGURAÇÕES BÁSICAS DA PROVA ---
    c1, c2 = st.columns([3, 1])
    titulo = c1.text_input("Título da Prova", placeholder="Ex: 1ª Avaliação de Química - 2º Bimestre")
    valor = c2.number_input("Valor por questão", min_value=0.1, value=1.0, step=0.1)
    
    # Puxa as questões do banco para podermos selecionar
    res_q = supabase.table("questoes").select("id, serie, assunto, enunciado").order("id", desc=True).execute()
    
    if res_q.data:
        df_sel = pd.DataFrame(res_q.data)
        
        # Função rápida para limpar o HTML do enunciado (criado pelo editor) e deixar só o texto puro no menu
        def clean_html(raw_html):
            if not raw_html: return ""
            cleanr = re.compile('<.*?>')
            cleantext = re.sub(cleanr, '', str(raw_html))
            return cleantext[:60] + "..." if len(cleantext) > 60 else cleantext
        
        # Cria um dicionário para mapear o texto bonito para o ID da questão
        opcoes_dict = {}
        for _, row in df_sel.iterrows():
            serie_txt = row.get('serie', 'Geral')
            assunto_txt = row.get('assunto', '')
            enunciado_limpo = clean_html(row.get('enunciado', ''))
            
            # Como a opção vai aparecer na tela para você
            texto_exibicao = f"[{serie_txt}] {assunto_txt} | {enunciado_limpo}"
            # Se der nomes duplicados por coincidência, adicionamos o ID invisível para diferenciar
            texto_exibicao = f"{texto_exibicao} (ID:{row['id']})"
            
            opcoes_dict[texto_exibicao] = row['id']
        
        st.divider()
        st.subheader("📚 Selecione as Questões")
        
        # Filtro opcional para limpar a tela
        series_disponiveis = ["Todas"] + sorted(list(df_sel['serie'].dropna().unique()))
        filtro_s = st.selectbox("Filtrar lista de seleção por Série (Opcional):", series_disponiveis)
        
        opcoes_exibicao = list(opcoes_dict.keys())
        if filtro_s != "Todas":
            opcoes_exibicao = [op for op in opcoes_exibicao if f"[{filtro_s}]" in op]
        
        # O campo de múltipla escolha
        selecionadas = st.multiselect(
            "Busque e adicione as questões para esta prova:", 
            options=opcoes_exibicao,
            help="Você pode digitar parte do assunto ou do texto para encontrar a questão mais rápido."
        )
        
        st.info(f"Quantidade de questões selecionadas para esta prova: **{len(selecionadas)}**")
        
        # --- BOTÃO DE SALVAR PROVA ---
        st.write("---")
        if st.button("🔨 Gerar Prova e Salvar", type="primary", use_container_width=True):
            if not titulo:
                st.error("❌ Dê um título para a prova!")
            elif len(selecionadas) == 0:
                st.error("❌ Selecione pelo menos 1 questão!")
            else:
                # Pega os IDs reais das questões selecionadas usando nosso dicionário
                ids_selecionados = [opcoes_dict[opt] for opt in selecionadas]
                
                dados_prova = {
                    "titulo": titulo, 
                    "questoes_ids": ids_selecionados, 
                    "valor_questao": float(valor), 
                    "ativa": True
                }
                
                try:
                    supabase.table("modelos_prova").insert(dados_prova).execute()
                    st.success(f"✅ Prova '{titulo}' gerada com sucesso contendo {len(selecionadas)} questões!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar a prova no banco: {e}")
    else:
        st.warning("Não há questões cadastradas no banco de dados. Vá em 'Cadastrar Questões' primeiro.")