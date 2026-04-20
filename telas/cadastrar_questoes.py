import streamlit as st
from streamlit_quill import st_quill
import time
import json

def mostrar_tela_cadastrar_questoes(supabase):
    st.title("🖊️ Cadastro de Questões (Upload de Imagens)")
    
    # --- FUNÇÃO DE UPLOAD PARA O SUPABASE STORAGE ---
    def upload_imagem(arquivo_upload):
        if arquivo_upload is not None:
            try:
                # Gera um nome único para o arquivo
                nome_unico = f"{int(time.time())}_{arquivo_upload.name.replace(' ', '_')}"
                # Faz o upload para o bucket 'imagens'
                res = supabase.storage.from_("imagens").upload(
                    path=nome_unico, 
                    file=arquivo_upload.getvalue(),
                    file_options={"content-type": arquivo_upload.type}
                )
                # Pega a URL pública
                return supabase.storage.from_("imagens").get_public_url(nome_unico)
            except Exception as e:
                st.error(f"Erro no upload da imagem: {e}")
                return ""
        return ""

    tab1, tab2 = st.tabs(["📝 Cadastro Individual", "⚡ Importação Flash"])
    
    with tab1:
        with st.form("form_nova_questao_upload", clear_on_submit=True):
            st.subheader("1️⃣ Enunciado")
            enunciado = st_quill(placeholder="Digite o enunciado...", html=True, key="quill_up")
            
            col_m, col_a = st.columns(2)
            materia = col_m.selectbox("Disciplina", ["Matemática", "Português", "Física", "Química", "Biologia", "História", "Geografia"])
            assunto = col_a.text_input("Assunto")

            st.divider()
            st.subheader("2️⃣ Alternativas (Faça Upload da Imagem ou digite o texto)")
            
            # Arrays para segurar os uploads temporariamente
            textos_alts = {}
            arquivos_alts = {}
            
            for letra in ["A", "B", "C", "D", "E"]:
                c_txt, c_up = st.columns([2, 1])
                textos_alts[letra] = c_txt.text_input(f"Texto da {letra})", key=f"t_{letra}")
                # BOTÃO DE CARREGAR IMAGEM
                arquivos_alts[letra] = c_up.file_uploader(f"Anexar Img {letra}", type=['png', 'jpg', 'jpeg'], key=f"f_{letra}")

            st.divider()
            st.subheader("3️⃣ Resposta Correta")
            correta = st.radio("Selecione a correta:", ["A", "B", "C", "D", "E"], horizontal=True)
            
            btn_salvar = st.form_submit_button("💾 Salvar na Biblioteca e Fazer Upload", type="primary")

            if btn_salvar:
                if not enunciado or len(enunciado) < 5:
                    st.error("Preencha o enunciado!")
                else:
                    with st.spinner("Fazendo upload das imagens e salvando..."):
                        alts_dados = {}
                        
                        # Processa cada alternativa
                        for letra in ["A", "B", "C", "D", "E"]:
                            # Se tiver arquivo, faz upload e pega a URL. Se não, URL fica vazia.
                            url_final = upload_imagem(arquivos_alts[letra])
                            alts_dados[letra] = {
                                "texto": textos_alts[letra],
                                "imagem": url_final
                            }

                        dados_final = {
                            "enunciado": enunciado,
                            "materia": materia,
                            "assunto": assunto,
                            "alternativas": alts_dados,
                            "correta": correta,
                            "revisada": True
                        }
                        
                        try:
                            supabase.table("questoes").insert(dados_final).execute()
                            st.success("✅ Questão e imagens salvas com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao salvar no banco: {e}")

    with tab2:
        st.subheader("⚡ Importador Flash")
        
        # Dica visual para você (ou outros professores) saberem o formato exato
        with st.expander("💡 Ver formato de JSON exigido pelo banco"):
            st.code('''[
  {
    "enunciado": "Qual é a capital de Pernambuco?",
    "materia": "Geografia",
    "assunto": "Capitais",
    "alternativas": {
      "A": {"texto": "Recife", "imagem": ""},
      "B": {"texto": "Olinda", "imagem": ""},
      "C": {"texto": "Caruaru", "imagem": ""},
      "D": {"texto": "Petrolina", "imagem": ""},
      "E": {"texto": "Paulista", "imagem": ""}
    },
    "correta": "A",
    "revisada": true
  }
]''', language="json")

        json_input = st.text_area("Cole aqui o array de Questões em JSON:", height=300)
        
        if st.button("🚀 Iniciar Importação", use_container_width=True):
            if not json_input.strip():
                st.warning("⚠️ Cole o texto JSON antes de clicar em importar!")
            else:
                try:
                    # 1. Tenta decodificar o texto
                    dados_json = json.loads(json_input)
                    
                    # 2. Garante que seja uma lista para iterar/inserir
                    if isinstance(dados_json, dict):
                        dados_json = [dados_json]
                        
                    # 3. Insere em lote no Supabase (mais rápido e seguro que o loop)
                    with st.spinner(f"Processando {len(dados_json)} questões..."):
                        supabase.table("questoes").insert(dados_json).execute()
                        st.success(f"✅ {len(dados_json)} questões importadas com sucesso!")
                        
                except json.JSONDecodeError as e:
                    # Agora o sistema vai "caguetar" exatamente onde o JSON está errado
                    st.error(f"❌ Erro de sintaxe no JSON. Verifique aspas, vírgulas ou chaves faltando.\n\nDetalhe técnico: {e}")
                except Exception as e:
                    # Erros do Supabase (ex: faltou alguma coluna obrigatória)
                    st.error(f"❌ Erro na integração com o Banco de Dados:\n\n{e}")