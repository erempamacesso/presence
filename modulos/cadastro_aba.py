import streamlit as st
import pandas as pd
import unicodedata
import time
from urllib.parse import quote

def limpar_texto(texto):
    """Padronização para nomes de arquivos e chaves de busca"""
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

def listar_arquivos_bucket(supabase):
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
        return mapa
    except: return {}

def exibir_cadastro(supabase):
    st.title("👤 Gestão de Alunos e Fotos")
    
    aba_gerenciar, aba_manual = st.tabs(["📸 Gerenciar Turmas e Fotos", "➕ Cadastro Manual"])

    with aba_gerenciar:
        # Busca turmas para o filtro
        res_t = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res_t.data if x['turma']])))
        
        if lista_turmas:
            turma_sel = st.selectbox("Selecione a Turma:", lista_turmas)
            alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
            mapa_fotos = listar_arquivos_bucket(supabase)

            st.write(f"Editando **{len(alunos)}** alunos da turma **{turma_sel}**")

            for aluno in alunos:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 2, 2])
                    uid = aluno['id']
                    nome_aluno = aluno['nome']
                    chave = limpar_texto(nome_aluno)
                    
                    # --- COLUNA 1: FOTO ATUAL ---
                    with c1:
                        foto_real = mapa_fotos.get(chave)
                        if foto_real:
                            url = supabase.storage.from_('fotos-alunos').get_public_url(foto_real)
                            st.image(url, width=70)
                        else:
                            st.markdown("🟡 **Sem Foto**")

                    # --- COLUNA 2: INFO E TROCAR TURMA ---
                    with c2:
                        st.markdown(f"**{nome_aluno}**")
                        nova_t = st.selectbox("Mudar Turma:", lista_turmas, 
                                             index=lista_turmas.index(aluno['turma']), 
                                             key=f"t_{uid}")
                        if nova_t != aluno['turma']:
                            supabase.table("alunos").update({"turma": nova_t}).eq("id", uid).execute()
                            st.toast("Turma atualizada!")
                            time.sleep(0.5)
                            st.rerun()

                    # --- COLUNA 3: UPLOAD DE FOTO DIRETO NO BUCKET ---
                    with c3:
                        foto_nova = st.file_uploader("Trocar Foto (.png)", type=["png"], key=f"up_{uid}")
                        if foto_nova:
                            if st.button("Salvar Foto", key=f"btn_{uid}"):
                                # Define o nome do arquivo como o nome do aluno limpo + .png
                                nome_arquivo = f"{chave}.png"
                                
                                # Upload para o Supabase Bucket (usando upsert=True para substituir a velha)
                                try:
                                    res_up = supabase.storage.from_('fotos-alunos').upload(
                                        path=nome_arquivo,
                                        file=foto_nova.getvalue(),
                                        file_options={"content-type": "image/png", "upsert": "true"}
                                    )
                                    st.success("Foto salva!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro no upload: {e}")
        else:
            st.warning("Cadastre uma turma ou importe alunos primeiro.")

    with aba_manual:
        st.subheader("Novo Cadastro Avulso")
        with st.form("f_manual", clear_on_submit=True):
            n = st.text_input("Nome Completo:")
            t = st.text_input("Turma:")
            if st.form_submit_button("Cadastrar Aluno"):
                if n and t:
                    supabase.table("alunos").insert({"nome": n.upper().strip(), "turma": t.upper().strip()}).execute()
                    st.success("Cadastrado!")
                    st.rerun()
