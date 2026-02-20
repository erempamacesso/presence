import streamlit as st
import unicodedata
from urllib.parse import quote
import time

def limpar_texto(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()
    return " ".join(texto_limpo.split())

def listar_arquivos_bucket(supabase):
    try:
        # Busca a lista de arquivos PNG no bucket
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 2000})
        mapa = {}
        for arq in arquivos:
            nome_original = arq['name']
            if nome_original.lower().endswith('.png'):
                nome_base = nome_original.rsplit('.', 1)[0]
                mapa[limpar_texto(nome_base)] = nome_original
        return mapa
    except: return {}

def exibir_fotograma(supabase):
    st.title("📸 Mapa de Sala (Fotograma)")
    
    try:
        # Busca as turmas cadastradas
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        if lista_turmas:
            turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
            if turma_sel:
                # ORDEM ALFABÉTICA ATIVADA
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                mapa_fotos = listar_arquivos_bucket(supabase)
                
                # AJUSTE PARA 2 COLUNAS (Ideal para celular)
                cols = st.columns(2) 
                for idx, aluno in enumerate(alunos):
                    with cols[idx % 2]:
                        with st.container(border=True):
                            chave = limpar_texto(aluno['nome'])
                            foto_arq = mapa_fotos.get(chave)
                            
                            if foto_arq:
                                # Monta a URL da imagem PNG
                                url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
                                url = f"{url_base}?t={int(time.time())}"
                                st.image(url, use_container_width=True)
                            else:
                                # Placeholder se não houver foto
                                st.markdown("<div style='height:150px; background:#f0f2f6; display:flex; align-items:center; justify-content:center; border-radius:10px; font-size:40px;'>👤</div>", unsafe_allow_html=True)
                            
                            st.markdown(f"<p style='text-align:center; font-size:11px; font-weight:bold; color:#333; margin-top:5px;'>{aluno['nome']}</p>", unsafe_allow_html=True)
        else:
            st.warning("Nenhuma turma encontrada no banco de dados.")
    except Exception as e:
        st.error(f"Erro ao carregar o Fotograma: {e}")
