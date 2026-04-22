import streamlit as st
from streamlit_quill import st_quill
import time
import json
import pandas as pd
import re

def mostrar_tela_cadastrar_questoes(supabase):
    st.title("🖊️ Cadastro e Edição de Questões")
    
    # --- FUNÇÃO DE UPLOAD PARA O SUPABASE STORAGE ---
    def upload_imagem(arquivo_upload):
        if arquivo_upload is not None:
            try:
                nome_unico = f"{int(time.time())}_{arquivo_upload.name.replace(' ', '_')}"
                res = supabase.storage.from_("imagens").upload(
                    path=nome_unico, 
                    file=arquivo_upload.getvalue(),
                    file_options={"content-type": arquivo_upload.type}
                )
                return supabase.storage.from_("imagens").get_public_url(nome_unico)
            except Exception as e:
                st.error(f"Erro no upload da imagem: {e}")
                return ""
        return ""

    # --- CRIAÇÃO DAS 3 ABAS ---
    tab1, tab2, tab3 = st.tabs(["📝 Cadastro Individual", "⚡ Importação Flash", "🛠️ Revisão e Edição"])
    
    # ==========================================
    # ABA 1: CADASTRO MANUAL
    # ==========================================
    with tab1:
        with st.form("form_nova_questao_upload", clear_on_submit=True):
            st.subheader("1️⃣ Enunciado")
            enunciado = st_quill(placeholder="Digite o enunciado...", html=True, key="quill_up")
            
            col_m, col_a = st.columns(2)
            serie = col_m.selectbox("Série", ["2º ano", "3º ano"])
            assunto = col_a.text_input("Assunto")

            st.divider()
            st.subheader("2️⃣ Alternativas (Upload ou Texto)")
            textos_alts = {}
            arquivos_alts = {}
            
            for letra in ["A", "B", "C", "D", "E"]:
                c_txt, c_up = st.columns([2, 1])
                textos_alts[letra] = c_txt.text_input(f"Texto da {letra})", key=f"t_{letra}")
                arquivos_alts[letra] = c_up.file_uploader(f"Anexar Img {letra}", type=['png', 'jpg', 'jpeg'], key=f"f_{letra}")

            st.divider()
            st.subheader("3️⃣ Resposta Correta")
            correta = st.radio("Selecione a correta:", ["A", "B", "C", "D", "E"], horizontal=True)
            btn_salvar = st.form_submit_button("💾 Salvar na Biblioteca", type="primary")

            if btn_salvar:
                if not enunciado or len(enunciado) < 5:
                    st.error("Preencha o enunciado!")
                else:
                    with st.spinner("Fazendo upload e salvando..."):
                        alts_dados = {}
                        for letra in ["A", "B", "C", "D", "E"]:
                            url_final = upload_imagem(arquivos_alts[letra])
                            alts_dados[letra] = {"texto": textos_alts[letra], "imagem": url_final}

                        dados_final = {
                            "enunciado": enunciado,
                            "serie": serie,
                            "assunto": assunto,
                            "alternativas": alts_dados,
                            "resposta_correta": correta,
                            "revisada": True
                        }
                        try:
                            supabase.table("questoes").insert(dados_final).execute()
                            st.success("✅ Questão salva com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao salvar no banco: {e}")

    # ==========================================
    # ABA 2: IMPORTAÇÃO FLASH
    # ==========================================
    with tab2:
        st.subheader("⚡ Importador Flash")
        with st.expander("💡 Ver formato de JSON exigido"):
            st.code('''[
  {
    "enunciado": "Qual o estado físico da água a 100°C ao nível do mar?",
    "serie": "2º ano",
    "assunto": "Termoquímica",
    "alternativas": {
      "A": {"texto": "Sólido", "imagem": ""},
      "B": {"texto": "Líquido", "imagem": ""},
      "C": {"texto": "Gasoso", "imagem": ""},
      "D": {"texto": "Plasma", "imagem": ""},
      "E": {"texto": "Vapor", "imagem": ""}
    },
    "resposta_correta": "C",
    "revisada": true
  }
]''', language="json")

        json_input = st.text_area("Cole aqui o array de Questões em JSON:", height=300)
        if st.button("🚀 Iniciar Importação", use_container_width=True):
            if not json_input.strip():
                st.warning("⚠️ Cole o texto JSON antes de clicar em importar!")
            else:
                try:
                    dados_json = json.loads(json_input)
                    if isinstance(dados_json, dict): dados_json = [dados_json]
                    with st.spinner(f"Processando {len(dados_json)} questões..."):
                        supabase.table("questoes").insert(dados_json).execute()
                        st.success(f"✅ {len(dados_json)} questões importadas com sucesso!")
                except json.JSONDecodeError as e:
                    st.error(f"❌ Erro de sintaxe no JSON:\n{e}")
                except Exception as e:
                    st.error(f"❌ Erro no Banco de Dados:\n{e}")

    # ==========================================
    # ABA 3: REVISÃO E EDIÇÃO (ATUALIZADA COM FILTROS!)
    # ==========================================
    with tab3:
        st.subheader("🛠️ Revisão e Atualização de Questões")
        st.write("Filtre e selecione uma questão para editar o texto ou adicionar imagens.")
        
        # Busca todas as questões para o DataFrame de edição
        res_q = supabase.table("questoes").select("*").order("id", desc=True).execute()
        
        if res_q.data:
            df_q = pd.DataFrame(res_q.data)
            
            # Padronização de colunas
            if 'revisada' not in df_q.columns: df_q['revisada'] = False
            df_q['revisada'] = df_q['revisada'].fillna(False)
            df_q['serie'] = df_q['serie'].fillna("Não definida")
            df_q['assunto'] = df_q['assunto'].fillna("Sem assunto")

            # --- BLOCO DE FILTROS ---
            st.write("### 🔍 Filtros de Busca")
            c_f1, c_f2, c_f3 = st.columns([1, 1, 1])
            
            with c_f1:
                status_f = st.radio("Status:", ["⚠️ Pendentes", "✅ Revisadas", "Todas"], horizontal=True)
            
            # Aplica filtro de status primeiro
            if status_f == "⚠️ Pendentes":
                df_q = df_q[df_q['revisada'] == False]
            elif status_f == "✅ Revisadas":
                df_q = df_q[df_q['revisada'] == True]

            with c_f2:
                series_disponiveis = sorted(df_q['serie'].unique())
                filtro_serie_ed = st.multiselect("Filtrar por Série:", options=series_disponiveis)
            
            if filtro_serie_ed:
                df_q = df_q[df_q['serie'].isin(filtro_serie_ed)]

            with c_f3:
                assuntos_disponiveis = sorted(df_q['assunto'].unique())
                filtro_assunto_ed = st.multiselect("Filtrar por Assunto:", options=assuntos_disponiveis)
            
            if filtro_assunto_ed:
                df_q = df_q[df_q['assunto'].isin(filtro_assunto_ed)]

            st.divider()

            if df_q.empty:
                st.warning("🔎 Nenhuma questão encontrada com esses filtros.")
            else:
                # Monta dicionário para o menu dropdown (selectbox)
                opcoes_dict = {}
                for _, row in df_q.iterrows():
                    # Limpa o HTML do enunciado para o menu
                    enunciado_limpo = re.sub('<.*?>', '', str(row.get('enunciado', '')))[:60] + "..."
                    txt_exibicao = f"[{row.get('serie', '')}] {row.get('assunto', '')} | {enunciado_limpo} (ID:{row['id']})"
                    opcoes_dict[txt_exibicao] = row
                
                questao_selecionada = st.selectbox("Selecione a questão para editar:", list(opcoes_dict.keys()))
                
                if questao_selecionada:
                    q_data = opcoes_dict[questao_selecionada]
                    id_q = q_data['id']
                    
                    # Formulário de Edição
                    with st.form(f"form_edicao_{id_q}"):
                        st.info(f"✏️ Editando Questão ID: {id_q}")
                        
                        enunc_edit = st_quill(value=q_data.get('enunciado', ''), html=True, key=f"q_edit_{id_q}")
                        
                        col1, col2 = st.columns(2)
                        serie_atual = q_data.get('serie', '2º ano')
                        # Tenta achar o índice da série atual na lista padrão
                        lista_series = ["2º ano", "3º ano"]
                        idx_serie = lista_series.index(serie_atual) if serie_atual in lista_series else 0
                        
                        serie_edit = col1.selectbox("Série", lista_series, index=idx_serie)
                        assunto_edit = col2.text_input("Assunto", value=q_data.get('assunto', ''))
                        
                        st.divider()
                        st.subheader("🖼️ Alternativas e Imagens")
                        
                        alts_existentes = q_data.get('alternativas', {})
                        if isinstance(alts_existentes, str):
                            try: alts_existentes = json.loads(alts_existentes.replace("'", '"'))
                            except: alts_existentes = {}
                            
                        textos_alts_edit = {}
                        arquivos_alts_edit = {}
                        urls_existentes = {}
                        
                        for letra in ["A", "B", "C", "D", "E"]:
                            alt_data = alts_existentes.get(letra, {})
                            if isinstance(alt_data, str): 
                                txt_atual, img_atual = alt_data, ""
                            else:
                                txt_atual = alt_data.get("texto", "")
                                img_atual = alt_data.get("imagem", "")
                            
                            urls_existentes[letra] = img_atual
                            
                            c_txt, c_up, c_img = st.columns([2, 1, 1])
                            textos_alts_edit[letra] = c_txt.text_input(f"Texto {letra})", value=txt_atual, key=f"t_edit_{letra}_{id_q}")
                            arquivos_alts_edit[letra] = c_up.file_uploader(f"Trocar Imagem {letra}", type=['png', 'jpg', 'jpeg'], key=f"f_edit_{letra}_{id_q}")
                            
                            if img_atual: c_img.image(img_atual, width=100, caption="Atual")
                            else: c_img.write("Sem imagem")
                        
                        st.divider()
                        resp_atual = q_data.get("resposta_correta", "A")
                        idx_resp = ["A", "B", "C", "D", "E"].index(resp_atual) if resp_atual in ["A", "B", "C", "D", "E"] else 0
                        correta_edit = st.radio("Resposta Correta:", ["A", "B", "C", "D", "E"], index=idx_resp, horizontal=True)
                        
                        marcar_revisada = st.checkbox("✅ Marcar como Revisada (Concluída)", value=True)
                        
                        btn_salvar = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
                        
                        if btn_salvar:
                            with st.spinner("Atualizando no banco..."):
                                alts_novas = {}
                                for letra in ["A", "B", "C", "D", "E"]:
                                    # Se enviou novo arquivo, faz upload. Se não, mantém a URL antiga.
                                    nova_url = upload_imagem(arquivos_alts_edit[letra]) if arquivos_alts_edit[letra] else urls_existentes[letra]
                                    alts_novas[letra] = {"texto": textos_alts_edit[letra], "imagem": nova_url}
                                
                                update_dados = {
                                    "enunciado": enunc_edit,
                                    "serie": serie_edit,
                                    "assunto": assunto_edit,
                                    "alternativas": alts_novas,
                                    "resposta_correta": correta_edit,
                                    "revisada": marcar_revisada
                                }
                                
                                try:
                                    supabase.table("questoes").update(update_dados).eq("id", id_q).execute()
                                    st.success("✅ Sucesso! Questão atualizada.")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")
        else:
            st.info("Nenhuma questão cadastrada no banco.")