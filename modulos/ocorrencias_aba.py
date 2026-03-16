import streamlit as st
import pandas as pd
from datetime import datetime
import unicodedata
from urllib.parse import quote

# === FUNÇÕES DE APOIO ===
def limpar_texto(texto):
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
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
        mapa_fotos = listar_arquivos_bucket(supabase)
        
        c1, c2 = st.columns(2)
        with c1:
            # key dinâmica ajuda no reset da tela
            turma_sel = st.selectbox("1. Selecione a Turma:", [""] + lista_turmas, key="sel_turma")
        
        if turma_sel:
            alunos_turma = supabase.table("alunos").select("id, nome").eq("turma", turma_sel).order("nome").execute().data
            mapa_alunos = {a['nome']: a['id'] for a in alunos_turma}
            
            with c2:
                aluno_sel_nome = st.selectbox("2. Selecione o Estudante:", [""] + list(mapa_alunos.keys()), key="sel_aluno")
            
            if aluno_sel_nome:
                aluno_id = mapa_alunos[aluno_sel_nome]
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
                        # AJUSTE 2: Removida a ocorrência de professor
                        tipo_sel = st.selectbox("Tipo de Ação:", ["Advertência", "Suspensão (Gestão)", "Outros"], key="sel_tipo")
                        tipo_ocorrencia = st.text_input("Especifique:", key="txt_espec") if tipo_sel == "Outros" else tipo_sel
                        motivo = st.text_area("Motivo da ocorrência:", key="txt_motivo")
                        
                        data_retorno = None
                        if "Suspensão" in tipo_sel:
                            data_retorno = st.date_input("Vigente até:", min_value=datetime.today().date(), key="date_retorno")
                        
                        senha = st.text_input("Sua Matrícula (Assinatura Gestão):", type="password", key="txt_senha")
                        
                        if st.button("🚨 Gravar Ocorrência", type="primary", use_container_width=True):
                            if not motivo or not senha:
                                st.warning("Preencha o motivo e a assinatura!")
                            else:
                                res_prof = supabase.table("professores_matriculas").select("professor").eq("matricula", senha).execute()
                                
                                if res_prof.data:
                                    nome_assinatura = res_prof.data[0]['professor']
                                    
                                    # AJUSTE 3: Validar se o nome pertence à gestão autorizada
                                    gestores_autorizados = ["Lilian Jordao", "Lilian Cabral", "Jackson"]
                                    
                                    # Normalizamos os nomes para evitar erro de acentuação na conferência
                                    gestor_valido = any(limpar_texto(nome_assinatura) == limpar_texto(g) for g in gestores_autorizados)

                                    if gestor_valido:
                                        dados = {
                                            "aluno_id": aluno_id, 
                                            "aluno_nome": aluno_sel_nome, 
                                            "turma": turma_sel,
                                            "tipo_ocorrencia": tipo_ocorrencia, 
                                            "motivo": motivo,
                                            "data_retorno": str(data_retorno) if data_retorno else None,
                                            "quem_registrou": nome_assinatura, # Mostra o nome real de quem executou
                                            "status": "Ativa"
                                        }
                                        supabase.table("ocorrencias_disciplinares").insert(dados).execute()
                                        
                                        st.success(f"Registrado com sucesso por {nome_assinatura}!")
                                        
                                        # AJUSTE 1: Reiniciar a tela limpando o state
                                        for key in st.session_state.keys():
                                            del st.session_state[key]
                                        st.rerun()
                                    else:
                                        st.error("Acesso Negado: Apenas Lilian Jordão, Lilian Cabral ou Jackson podem autorizar.")
                                else:
                                    st.error("Matrícula não encontrada!")
    except Exception as e:
        st.error(f"Erro no sistema: {e}")