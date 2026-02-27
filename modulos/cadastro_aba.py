import streamlit as st
import pandas as pd
import unicodedata
import time

# --- FUNÇÕES DE UTILITÁRIO ---

def limpar_texto(texto):
    """Padronização para nomes de arquivos e chaves de busca"""
    if not texto: return ""
    # Remove extensão se houver
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

# --- FUNÇÃO PRINCIPAL DE INTERFACE ---

def exibir_cadastro(supabase):
    st.title("👤 Sistema de Gestão Escolar")
    
    # Organização Profissional das Abas
    aba_busca, aba_gerenciar, aba_excel, aba_manual = st.tabs([
        "🔍 Localizar Aluno", 
        "📸 Fotos e Turmas", 
        "📁 Atualização Excel", 
        "➕ Cadastro Avulso"
    ])

    # =========================================================
    # ABA 1: LOCALIZAR ALUNO
    # =========================================================
    with aba_busca:
        st.subheader("Consulta Rápida de Alunos")
        nome_busca = st.text_input("Digite o nome ou parte do nome:").strip().upper()

        if nome_busca:
            with st.spinner("Buscando no sistema..."):
                res = supabase.table("alunos").select("nome, turma").ilike("nome", f"%{nome_busca}%").execute()
                
                if res.data:
                    st.success(f"Encontrados {len(res.data)} aluno(s)")
                    df_res = pd.DataFrame(res.data)
                    df_res.columns = ["Nome Completo", "Turma Atual"]
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                else:
                    st.warning(f"⚠️ Aluno '{nome_busca}' não encontrado no sistema.")

    # =========================================================
    # ABA 2: GERENCIAR TURMAS E FOTOS
    # =========================================================
    with aba_gerenciar:
        res_t = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res_t.data if x['turma']])))
        
        if lista_turmas:
            turma_sel = st.selectbox("Selecione a Turma para gerenciar:", lista_turmas)
            alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
            mapa_fotos = listar_arquivos_bucket(supabase)

            st.write(f"Exibindo **{len(alunos)}** alunos")

            for aluno in alunos:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 2, 2])
                    uid, nome_aluno, chave = aluno['id'], aluno['nome'], limpar_texto(aluno['nome'])
                    foto_real = mapa_fotos.get(chave)
                    
                    with c1:
                        if foto_real:
                            url = supabase.storage.from_('fotos-alunos').get_public_url(foto_real)
                            st.image(url, width=80)
                        else:
                            st.caption("🟡 Sem Foto")

                    with c2:
                        st.markdown(f"**{nome_aluno}**")
                        nova_t = st.selectbox("Mudar Turma:", lista_turmas, index=lista_turmas.index(aluno['turma']), key=f"t_{uid}")
                        if nova_t != aluno['turma']:
                            supabase.table("alunos").update({"turma": nova_t}).eq("id", uid).execute()
                            st.toast("Turma atualizada!")
                            time.sleep(0.5)
                            st.rerun()
                        
                        with st.popover("🗑️ Opções Críticas"):
                            if st.button("Excluir Aluno Permanentemente", key=f"del_{uid}", type="primary"):
                                if foto_real: supabase.storage.from_('fotos-alunos').remove([foto_real])
                                supabase.table("alunos").delete().eq("id", uid).execute()
                                st.rerun()

                    with c3:
                        foto_nova = st.file_uploader("Trocar Foto (.png)", type=["png"], key=f"up_{uid}")
                        if foto_nova and st.button("Salvar Foto", key=f"btn_{uid}"):
                            nome_arquivo = f"{chave}.png"
                            supabase.storage.from_('fotos-alunos').upload(
                                path=nome_arquivo, file=foto_nova.getvalue(),
                                file_options={"content-type": "image/png", "upsert": "true"}
                            )
                            st.rerun()
                        elif foto_real:
                            if st.button("🗑️ Remover Foto", key=f"del_pic_{uid}"):
                                supabase.storage.from_('fotos-alunos').remove([foto_real])
                                st.rerun()
        else:
            st.warning("Nenhum dado encontrado. Use as abas de importação.")

    # =========================================================
    # ABA 3: UPLOAD DO EXCEL (LÓGICA ANTERIOR)
    # =========================================================
    with aba_excel:
        st.subheader("Sincronização com Planilha Secretaria")
        arquivo = st.file_uploader("Suba o arquivo .xlsx ou .xls", type=["xlsx", "xls"])
        
        if arquivo:
            if st.button("🚀 Iniciar Sincronização", type="primary"):
                # ... (A lógica de processamento do Excel que fizemos antes entra aqui)
                st.info("Processando planilha...")
                # Aqui você insere o bloco do pd.ExcelFile, engine e upsert que validamos.

    # =========================================================
    # ABA 4: CADASTRO MANUAL
    # =========================================================
    with aba_manual:
        st.subheader("Cadastrar Aluno Individualmente")
        with st.form("f_manual", clear_on_submit=True):
            n = st.text_input("Nome Completo:")
            t = st.text_input("Turma:")
            if st.form_submit_button("Cadastrar"):
                if n and t:
                    supabase.table("alunos").insert({"nome": n.upper().strip(), "turma": t.upper().strip()}).execute()
                    st.success("Aluno cadastrado!")
                    time.sleep(1)
                    st.rerun()
