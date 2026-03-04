import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
from fpdf import FPDF
from datetime import datetime
import simple_icd_10 as icd

# ==========================================
# 🧠 MOTOR DE INTELIGÊNCIA (TRADUÇÃO REAL)
# ==========================================
def buscar_descricao_cid_hardcore(cid_input):
    if not cid_input: return ""
    # Limpa o código para garantir que a biblioteca encontre (ex: F84.0)
    codigo = str(cid_input).strip().upper().split('/')[0].split(' ')[0].replace("CID", "").replace(":", "").strip()
    try:
        if icd.is_valid_item(codigo):
            desc_en = icd.get_description(codigo)
            # Dicionário de tradução técnica para os termos da biblioteca
            termos = {
                "Autism": "Autismo", "Disorders": "Transtornos", 
                "Attention deficit": "TDAH", "Mental retardation": "Def. Intelectual", 
                "Epilepsy": "Epilepsia", "Specific": "Específicos",
                "Developmental": "do Desenvolvimento", "Hyperkinetic": "Hipercinéticos"
            }
            desc_pt = desc_en
            for en, pt in termos.items(): 
                desc_pt = desc_pt.replace(en, pt)
            return f" - {desc_pt}"
        return ""
    except: return ""

# ==========================================
# 🤖 IA DE PROPOSTAS PEDAGÓGICAS
# ==========================================
def gerar_sugestoes_ia(relatorio):
    """Mapeia o relatório para as 4 áreas do conhecimento"""
    rel = str(relatorio).lower()
    # Estratégia base
    dicas = {
        "Linguagens": "Priorizar multiletramentos e suporte visual (pictogramas).",
        "Matemática": "Uso de materiais concretos e situações-problema curtas.",
        "Natureza": "Atividades experimentais e observação prática.",
                "Humanas": "Mapas conceituais e debates com mediação visual."
    }
    # Personalização baseada em palavras-chave
    if "leitura" in rel or "alfabetiza" in rel:
        dicas["Linguagens"] = "⚠️ Foco em consciência fonológica e pareamento de imagem/palavra."
    if "foco" in rel or "concentra" in rel or "agitação" in rel:
        dicas["Matemática"] = "Dividir tarefas em blocos de 10 min com comandos únicos."
    
    return dicas

# ==========================================
# 🧩 POPUP DE INCLUSÃO (RESTAURADO)
# ==========================================
@st.dialog("🧩 Ficha de Inclusão e AEE")
def abrir_popup_aee(nome, status, cid, relatorio):
    st.subheader(nome)
    
    # Agora a tradução vai aparecer aqui!
    desc = buscar_descricao_cid_hardcore(cid)
    
    if status == "Em Investigação":
        st.warning(f"🟡 **Status:** {status}")
    else:
        st.info(f"🔵 **Status:** {status}")
        
    st.markdown(f"**CID:** `{cid}` {desc}")
    
    if relatorio:
        with st.expander("📝 Relatório Original", expanded=True):
            st.write(relatorio)
            
    st.divider()
    st.subheader("🤖 Estratégias por Área")
    
    if st.button("✨ Gerar Propostas de Atividades", use_container_width=True):
        with st.spinner("IA Analisando..."):
            sugestoes = gerar_sugestoes_ia(relatorio)
            
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**📚 Linguagens**\n{sugestoes['Linguagens']}")
                st.info(f"**🌍 Humanas**\n{sugestoes['Humanas']}")
            with c2:
                st.success(f"**🔢 Matemática**\n{sugestoes['Matemática']}")
                st.success(f"**🔬 Natureza**\n{sugestoes['Natureza']}")

# ==========================================
# 🛠️ FUNÇÕES DE TRATAMENTO (PADRONIZADAS)
# ==========================================
def limpar_texto(texto):
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

def calcular_idade_completa(data_nascimento):
    try:
        if not data_nascimento: return ""
        dt_nasc = pd.to_datetime(str(data_nascimento).split('T')[0], errors='coerce')
        if pd.isnull(dt_nasc): return ""
        hoje = datetime.now()
        idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
        return f"{int(idade)} anos"
    except: return ""

@st.cache_data(ttl=600)
def listar_arquivos_bucket(_supabase):
    try:
        arquivos = _supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
    except: return {}

# ==========================================
# 📸 EXIBIÇÃO DO FOTOGRAMA
# ==========================================
def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    
    try:
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        mapa_fotos = listar_arquivos_bucket(supabase)
        supabase_url = st.secrets['SUPABASE_URL']

        if lista_turmas:
            turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
            
            if turma_sel:
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                st.divider()
                
                num_cols = 6
                for i in range(0, len(alunos), num_cols):
                    linha_alunos = alunos[i : i + num_cols]
                    cols = st.columns(num_cols)
                    for j, aluno in enumerate(linha_alunos):
                        with cols[j]:
                            status_aee = aluno.get('status_aee', 'Nenhum')
                            borda_cor = "#007BFF" if status_aee == "Laudo Confirmado" else "#FFC107" if status_aee == "Em Investigação" else "transparent"
                            espessura = "4px" if status_aee != "Nenhum" else "0px"
                            
                            nome = aluno.get("nome", "Sem Nome")
                            chave = limpar_texto(nome)
                            foto_arq = mapa_fotos.get(chave)
                            
                            if foto_arq:
                                url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
                                img_html = f'<img src="{url_img}" style="width: 100%; height: 130px; object-fit: contain; background: #f8f9fa; border-radius: 4px;">'
                            else:
                                img_html = "<div style='width:100%; height:130px; background:#f0f0f0; border-radius:4px; display:flex; align-items:center; justify-content:center; font-size:40px;'>👤</div>"
                            
                            raw_date = aluno.get('data_nascimento') or aluno.get('Data de nascimento')
                            idade = calcular_idade_completa(raw_date)
                            try:
                                dt_fmt = pd.to_datetime(str(raw_date).split('T')[0]).strftime('%d/%m/%Y')
                            except:
                                dt_fmt = "--/--/----"
                            
                            st.markdown(f"""
                            <div style="border: {espessura} solid {borda_cor}; border-radius: 10px; padding: 8px; text-align: center; background: white; min-height: 230px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);">
                                {img_html}
                                <div>
                                    <p style="font-size: 10px; font-weight: bold; margin: 5px 0 0 0; text-transform: uppercase; color: #333;">{nome[:20]}</p>
                                    <p style="font-size: 9px; color: #666; margin: 0;">{dt_fmt} - {idade}</p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if status_aee != "Nenhum":
                                if st.button("🧩 Ficha", key=f"f_{aluno['id']}", use_container_width=True):
                                    abrir_popup_aee(nome, status_aee, aluno.get('cid',''), aluno.get('relatorio_aee',''))
    except Exception as e:
        st.error(f"Erro ao carregar fotograma: {e}")
