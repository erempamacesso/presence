import streamlit as st
import unicodedata
from urllib.parse import quote
import time

def limpar_texto(texto):
    """Limpeza ultra-agressiva para garantir o match perfeito entre banco e storage"""
    if not texto: return ""
    # Remove extensão se houver
    if "." in str(texto):
        texto = str(texto).rsplit('.', 1)[0]
    
    # Normaliza (remove acentos)
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    
    # Remove TUDO que não for letra ou número (espaços, hífens, underlines)
    return "".join(filter(str.isalnum, texto_limpo))

def listar_arquivos_bucket(supabase):
    try:
        # Aumentamos o limite para garantir que pegue todos os arquivos
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {}
        for arq in arquivos:
            nome_original = arq['name']
            # Aceita PNG e JPG por segurança
            if nome_original.lower().endswith(('.png', '.jpg', '.jpeg')):
                chave = limpar_texto(nome_original)
                mapa[chave] = nome_original
        return mapa
    except: return {}

def exibir_fotograma(supabase):
    st.title("📸 Mapa de Sala (Fotograma)")
    
    try:
        # Busca as turmas
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        if lista_turmas:
            turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
            if turma_sel:
                # Busca alunos da turma em ordem alfabética
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                mapa_fotos = listar_arquivos_bucket(supabase)
                
                # GRID DE 6 COLUNAS
                num_cols = 6
                cols = st.columns(num_cols)
                
                for idx, aluno in enumerate(alunos):
                    with cols[idx % num_cols]:
                        # Container compacto para as fotos
                        with st.container(border=True):
                            chave_aluno = limpar_texto(aluno['nome'])
                            foto_arq = mapa_fotos.get(chave_aluno)
                            
                            if foto_arq:
                                # URL pública com timestamp para evitar cache de fotos velhas
                                url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
                                url = f"{url_base}?t={int(time.time())}"
                                st.image(url, use_container_width=True)
                            else:
                                # Placeholder cinza caso não encontre o match exato
                                st.markdown("<div style='height:80px; background:#f0f2f6; display:flex; align-items:center; justify-content:center; border-radius:5px; font-size:25px;'>👤</div>", unsafe_allow_html=True)
                            
                            # Nome menor para caber na grade de 6
                            nome_exibir = aluno['nome'].split()[0] # Mostra só o primeiro nome se quiser economizar espaço
                            st.markdown(f"<p style='text-align:center; font-size:9px; font-weight:bold; color:#555; margin-top:2px; line-height:1;'>{aluno['nome']}</p>", unsafe_allow_html=True)
        else:
            st.warning("Nenhuma turma encontrada.")
    except Exception as e:
        st.error(f"Erro ao carregar o Fotograma: {e}")
