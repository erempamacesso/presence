import streamlit as st
import unicodedata
from urllib.parse import quote
import time

def limpar_texto(texto):
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

def listar_arquivos_bucket(supabase):
    try:
        # Aumentamos o limite para garantir que pegue todos os arquivos da escola
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
    except: return {}

def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    
    try:
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        if lista_turmas:
            turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
            if turma_sel:
                # 1. Busca alunos em ordem alfabética
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                mapa_fotos = listar_arquivos_bucket(supabase)
                
                # 2. DEFINIÇÃO DA GRADE (6 colunas)
                num_cols = 6
                
                # 3. LÓGICA DE LINHAS (Garante ordem alfabética no celular)
                # Dividimos a lista de alunos em grupos de 6
                for i in range(0, len(alunos), num_cols):
                    linha_alunos = alunos[i : i + num_cols]
                    cols = st.columns(num_cols)
                    
                    for j, aluno in enumerate(linha_alunos):
                        with cols[j]:
                            with st.container(border=True):
                                chave = limpar_texto(aluno['nome'])
                                foto_arq = mapa_fotos.get(chave)
                                
                                if foto_arq:
                                    url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
                                    st.image(f"{url_base}?t={int(time.time())}", use_container_width=True)
                                else:
                                    # Placeholder visualmente mais limpo
                                    st.markdown("<div style='height:80px; background:#f9f9f9; display:flex; align-items:center; justify-content:center; border-radius:8px; border: 1px dashed #ccc; font-size:24px;'>👤</div>", unsafe_allow_html=True)
                                
                                # Nome formatado para não quebrar o layout
                                nome_curto = aluno['nome'].split()[0] # Pega o primeiro nome
                                st.markdown(f"<p style='text-align:center; font-size:10px; font-weight:bold; margin-top:4px; line-height:1.1;'>{aluno['nome']}</p>", unsafe_allow_html=True)
        else:
            st.warning("Nenhuma turma encontrada.")
    except Exception as e:
        st.error(f"Erro no Fotograma: {e}")
