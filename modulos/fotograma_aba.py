import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
from fpdf import FPDF
from datetime import datetime, timedelta
import simple_icd_10 as icd

# ==========================================
# 🧠 MOTOR DE INTELIGÊNCIA (CID + IA)
# ==========================================
def buscar_descricao_cid_hardcore(cid_input):
    if not cid_input: return ""
    codigo = str(cid_input).strip().upper().split('/')[0].split(' ')[0].replace("CID", "").replace(":", "").strip()
    try:
        if icd.is_valid_item(codigo):
            desc_en = icd.get_description(codigo)
            termos = {
                "Autism": "Autismo", "Disorders": "Transtornos", "Childhood": "Infantil",
                "Hyperkinetic": "Hipercinéticos", "Attention deficit": "TDAH",
                "Mental retardation": "Deficiência Intelectual", "Conduct": "Conduta",
                "Epilepsy": "Epilepsia", "Developmental": "do Desenvolvimento"
            }
            desc_pt = desc_en
            for en, pt in termos.items():
                desc_pt = desc_pt.replace(en, pt)
            return f" - {desc_pt}"
        return ""
    except: return ""

def gerar_sugestoes_ia(relatorio):
    rel = str(relatorio).lower()
    dicas = {
        "Linguagens": "Uso de textos curtos, apoio de imagens e respostas orais.",
        "Matemática": "Materiais concretos e fragmentação de problemas.",
        "Natureza": "Experimentos práticos e vídeos ilustrativos.",
        "Humanas": "Mapas mentais e debates visuais."
    }
    if "ler" in rel or "leitura" in rel:
        dicas["Linguagens"] = "⚠️ Aluno com dificuldade de leitura: Priorizar áudio e pictogramas."
    if "foco" in rel or "concentra" in rel:
        dicas["Matemática"] = "Tarefas curtas com pausas e cronômetro visual."
    return dicas

# ==========================================
# 🧩 POPUP DE INCLUSÃO (CORRIGIDO)
# ==========================================
@st.dialog("🧩 Ficha de Inclusão e AEE")
def abrir_popup_aee(nome, status, cid, relatorio):
    st.subheader(nome)
    desc_completa = buscar_descricao_cid_hardcore(cid)
    
    if status == "Em Investigação":
        st.warning(f"🟡 **Status:** Investigação Pedagógica")
    else:
        st.info(f"🔵 **Status:** Laudo Confirmado")
    
    st.markdown(f"**CID:** `{cid}` {desc_completa}")
        
    if relatorio:
        with st.expander("📝 Relatório / Observações", expanded=True):
            st.write(relatorio)
        
    st.divider()
    st.subheader("🤖 Sugestões Pedagógicas (IA)")
    
    if st.button("✨ Gerar Estratégias por Área", use_container_width=True):
        with st.spinner("Analisando perfil..."):
            sugestoes = gerar_sugestoes_ia(relatorio)
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**📚 Linguagens**\n\n{sugestoes['Linguagens']}")
                st.info(f"**🌍 Humanas**\n\n{sugestoes['Humanas']}")
            with c2:
                st.success(f"**🔢 Matemática**\n\n{sugestoes['Matemática']}")
                st.success(f"**🔬 Natureza**\n\n{sugestoes['Natureza']}")

# ==========================================
# 🛠️ FUNÇÕES AUXILIARES E PDF
# ==========================================
def limpar_texto(texto):
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()

def calcular_idade_completa(data_nascimento):
    try:
        dt_nasc = pd.to_datetime(str(data_nascimento).split('T')[0])
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
# 📸 EXIBIÇÃO DO FOTOGRAMA (COMPLETO)
# ==========================================
def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    
    try:
        # 1. Alerta de Novos Alunos AEE para Coordenadores
        # Simulamos buscando quem foi atualizado recentemente (ex: campo 'updated_at' se houver, ou apenas checando quem é AEE)
        res_aee = supabase.table("alunos").select("nome, turma, status_aee").neq("status_aee", "Nenhum").execute()
        if res_aee.data:
            st.toast(f"📢 Existem {len(res_aee.data)} alunos em acompanhamento especial nesta escola.", icon="🧩")

        # 2. Carregamento de dados
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
                                # CSS FIX: 'object-fit: contain' para não amassar as fotos (Print 2)
                                img_html = f'<img src="{url_img}" style="width: 100%; height: 130px; object-fit: contain; background: #f8f9fa; border-radius: 4px;">'
                            else:
                                img_html = "<div style='width:100%; height:130px; background:#f0f0f0; border-radius:4px; display:flex; align-items:center; justify-content:center; font-size:40px;'>👤</div>"
                            
                            idade = calcular_idade_completa(aluno.get('data_nascimento'))
                            
                            # Card Visual Blindado
                            st.markdown(f"""
                            <div style="border: {espessura} solid {borda_cor}; border-radius: 10px; padding: 8px; text-align: center; background: white; min-height: 220px; display: flex; flex-direction: column; justify-content: space-between;">
                                {img_html}
                                <div>
                                    <p style="font-size: 10px; font-weight: bold; margin: 5px 0 0 0; text-transform: uppercase;">{nome[:20]}</p>
                                    <p style="font-size: 9px; color: gray; margin: 0;">{idade}</p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if status_aee != "Nenhum":
                                if st.button("🧩 Ficha", key=f"f_{aluno['id']}", use_container_width=True):
                                    abrir_popup_aee(nome, status_aee, aluno.get('cid',''), aluno.get('relatorio_aee',''))
    except Exception as e:
        st.error(f"Erro: {e}")
