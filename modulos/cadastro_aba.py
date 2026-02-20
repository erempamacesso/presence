import streamlit as st
import pandas as pd
import unicodedata
import time

def limpar_texto(texto):
    if not texto: return ""
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").strip()

def listar_arquivos_bucket(supabase):
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list()
        mapa = {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
        return mapa
    except: return {}

def exibir_cadastro(supabase):
    st.title("👤 Gestão de Alunos")
    
    aba_gerenciar, aba_manual = st.tabs(["📸 Gerenciar Turmas e Fotos", "➕ Cadastro Manual"])

    with aba_gerenciar:
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x['turma']])))
        
        if lista_turmas:
            turma_sel = st.selectbox("Selecione a Turma para Editar:", lista_turmas)
            alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
            mapa_arquivos = listar_arquivos_bucket(supabase)

            for aluno in alunos:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 3, 2])
                    with c1:
                        chave = limpar_texto(aluno['nome'])
                        foto_real = mapa_arquivos.get(chave)
                        if foto_real:
                            url = supabase.storage.from_('fotos-alunos').get_public_url(foto_real)
                            st.image(url, width=60)
                        else: st.markdown("👤")
                    with c2:
                        st.write(f"**{aluno['nome']}**")
                    with c3:
                        nova_turma = st.selectbox("Mudar Turma", lista_turmas, 
                                                 index=lista_turmas.index(aluno['turma']), 
                                                 key=f"edit_{aluno['id']}")
                        if nova_turma != aluno['turma']:
                            supabase.table("alunos").update({"turma": nova_turma}).eq("id", aluno['id']).execute()
                            st.toast(f"{aluno['nome']} movido!")
                            time.sleep(0.5)
                            st.rerun()
        else: st.warning("Nenhuma turma cadastrada.")

    with aba_manual:
        with st.form("form_manual", clear_on_submit=True):
            nome_man = st.text_input("Nome Completo")
            turma_man = st.text_input("Turma (Ex: 1A, 2B)")
            if st.form_submit_button("Salvar Cadastro"):
                if nome_man and turma_man:
                    supabase.table("alunos").insert({"nome": nome_man.upper(), "turma": turma_man.upper()}).execute()
                    st.success("Aluno cadastrado com sucesso!")
