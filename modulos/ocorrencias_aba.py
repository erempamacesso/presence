import streamlit as st
import pandas as pd
from datetime import datetime
import unicodedata
from urllib.parse import quote

# === FUNÇÕES DE APOIO (IGUAIS AO FOTOGRAMA) ===
def limpar_texto(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

@st.cache_data(ttl=600)
def listar_arquivos_bucket(_supabase):
    try:
        arquivos = _supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
    except: return {}

def exibir_ocorrencias(supabase):
    st.title("🚨 Mural de Ocorrências e Suspensões")
    
    # Pegando a URL do Supabase para montar o link da imagem
    if "SUPABASE_URL_ALUNOS" in st.secrets:
        supabase_url = str(st.secrets["SUPABASE_URL_ALUNOS"])
    else:
        supabase_url = ""

    # 1. MURAL DE EXIBIÇÃO
    try:
        res_ocorrencias = supabase.table("ocorrencias_disciplinares").select("*").eq("status", "Ativa").order("created_at", desc=True).execute()
        if res_ocorrencias.data:
            df_exibicao = pd.DataFrame(res_ocorrencias.data)[['aluno_nome', 'turma', 'tipo_ocorrencia', 'data_retorno', 'quem_registrou']]
            df_exibicao.columns = ['Estudante', 'Turma', 'Penalidade', 'Vigente até', 'Registrado por']
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        else:
            st.success("Nenhuma suspensão ativa no momento. 🎉")
    except Exception as e:
        st.error(f"Erro ao carregar mural: {e}")

    st.divider()

    # 2. REGISTRO DE NOVA OCORRÊNCIA
    st.subheader("➕ Registrar Nova Ocorrência")
    
    try:
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        mapa_fotos = listar_arquivos_bucket(supabase) # Busca as fotos no storage
        
        c1, c2 = st.columns(2)
        with c1:
            turma_sel = st.selectbox("1. Selecione a Turma:", [""] + lista_turmas)
        
        if turma_sel:
            # Aqui buscamos APENAS id e nome, pois a foto vem do Storage
            alunos_turma = supabase.table("alunos").select("id, nome").eq("turma", turma_sel).order("nome").execute().data
            mapa_alunos = {a['nome']: a['id'] for a in alunos_turma}
            
            with c2:
                aluno_sel_nome = st.selectbox("2. Selecione o Estudante:", [""] + list(mapa_alunos.keys()))
            
            if aluno_sel_nome:
                aluno_id = mapa_alunos[aluno_sel_nome]
                
                # --- LÓGICA DE BUSCA DA FOTO (IGUAL AO FOTOGRAMA) ---
                chave = limpar_texto(aluno_sel_nome)
                foto_arq = mapa_fotos.get(chave)
                if foto_arq:
                    url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
                else:
                    url_img = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"

                with st.container(border=True):
                    col_foto, col_form = st.columns([1, 2.5])
                    
                    with col_foto:
                        st.image(url_img, use_container_width=True)
                        st.markdown(f"<p style='text-align:center'><b>{aluno_sel_nome}</b><br><small>{turma_sel}</small></p>", unsafe_allow_html=True)

                    with col_form:
                        tipo_sel = st.selectbox("Tipo de Ação:", ["Advertência", "Suspensão (Professor)", "Suspensão (Gestão)", "Outros"])
                        tipo_ocorrencia = st.text_input("Especifique:") if tipo_sel == "Outros" else tipo_sel
                        motivo = st.text_area("Motivo da ocorrência:")
                        
                        data_retorno = None
                        if "Suspensão" in tipo_sel:
                            data_retorno = st.date_input("Vigente até:", min_value=datetime.today().date())
                        
                        senha = st.text_input("Sua Matrícula (Assinatura):", type="password")
                        
                        if st.button("🚨 Gravar Ocorrência", type="primary", use_container_width=True):
                            if not motivo or not senha:
                                st.warning("Preencha o motivo e a assinatura!")
                            else:
                                res_prof = supabase.table("professores_matriculas").select("professor").eq("matricula", senha).execute()
                                if res_prof.data:
                                    dados = {
                                        "aluno_id": aluno_id, "aluno_nome": aluno_sel_nome, "turma": turma_sel,
                                        "tipo_ocorrencia": tipo_ocorrencia, "motivo": motivo,
                                        "data_retorno": str(data_retorno) if data_retorno else None,
                                        "quem_registrou": res_prof.data[0]['professor'], "status": "Ativa"
                                    }
                                    supabase.table("ocorrencias_disciplinares").insert(dados).execute()
                                    st.success("Registrado!")
                                    st.rerun()
                                else:
                                    st.error("Matrícula não encontrada!")
    except Exception as e:
        st.error(f"Erro no sistema: {e}")