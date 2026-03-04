import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
from fpdf import FPDF
from datetime import datetime
import simple_icd_10 as icd # <--- Biblioteca Hardcore integrada

# ==========================================
# 🧠 MOTOR DE INTELIGÊNCIA (CID + IA)
# ==========================================
def buscar_descricao_cid_hardcore(cid_input):
    """Busca na biblioteca oficial e traduz termos técnicos"""
    if not cid_input: return ""
    codigo = str(cid_input).strip().upper().replace("CID", "").replace(":", "").strip()
    try:
        # Tenta validar o código (ex: F84.0 ou F84)
        if icd.is_valid_item(codigo):
            desc_en = icd.get_description(codigo)
            # Dicionário de tradução técnica para manter o profissionalismo
            termos = {
                "Autism": "Autismo", "Disorders": "Transtornos", "Childhood": "Infantil",
                "Hyperkinetic": "Hipercinéticos", "Attention deficit": "Déficit de Atenção",
                "Mental retardation": "Deficiência Intelectual", "Conduct": "Conduta",
                "Epilepsy": "Epilepsia", "Specific": "Específicos", "Developmental": "do Desenvolvimento"
            }
            desc_pt = desc_en
            for en, pt in termos.items():
                desc_pt = desc_pt.replace(en, pt)
            return f"({desc_pt})"
        return ""
    except: return ""

def gerar_sugestoes_ia(relatorio):
    """IA rápida que mapeia o relatório para as 4 áreas do conhecimento"""
    rel = str(relatorio).lower()
    dicas = {
        "Linguagens": "Uso de textos curtos, apoio de imagens (pictogramas) e priorização de respostas orais ou digitais.",
        "Matemática": "Utilização de materiais concretos (blocos, ábaco). Decompor problemas complexos em etapas simples.",
        "Natureza": "Foco em experimentos práticos, vídeos ilustrativos e saídas de campo para observação direta.",
        "Humanas": "Mapas mentais, linha do tempo visual e debates sobre temas atuais para fixação de contexto social."
    }
    # Personalização dinâmica baseada no texto
    if "não sabe ler" in rel or "alfabetiza" in rel:
        dicas["Linguagens"] = "⚠️ Aluno em fase de alfabetização: Priorizar áudio, vídeos e reconhecimento de sons/letras com suporte visual."
    if "concentra" in rel or "foco" in rel or "agita" in rel:
        dicas["Matemática"] = "Atividades curtas com pausas. Usar cronômetro visual para ajudar na gestão do tempo da tarefa."
    
    return dicas

# ==========================================
# 🧩 POPUP DE INCLUSÃO (MODO IA + TRADUTOR)
# ==========================================
@st.dialog("🧩 Ficha de Inclusão e AEE")
def abrir_popup_aee(nome, status, cid, relatorio):
    st.subheader(nome)
    
    # Busca a descrição na biblioteca hardcore
    desc_completa = buscar_descricao_cid_hardcore(cid)
    
    if status == "Em Investigação":
        st.warning(f"🟡 **Em Investigação Pedagógica**\n\n**Código:** {cid} {desc_completa}")
    elif status == "Laudo Confirmado":
        st.info(f"🔵 **Laudo Confirmado**\n\n**Código:** {cid} {desc_completa}")
        
    if relatorio:
        with st.expander("📝 Ver Relatório/Observações", expanded=True):
            st.write(relatorio)
        
    st.divider()
    st.subheader("🤖 Sugestões Pedagógicas (IA)")
    
    if st.button("✨ Gerar Estratégias por Área", use_container_width=True):
        with st.spinner("A IA está analisando o prontuário..."):
            sugestoes = gerar_sugestoes_ia(relatorio)
            
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**📚 Linguagens e Códigos**\n\n{sugestoes['Linguagens']}")
                st.info(f"**🌍 Ciências Humanas**\n\n{sugestoes['Humanas']}")
            with c2:
                st.success(f"**🔢 Matemática**\n\n{sugestoes['Matemática']}")
                st.success(f"**🔬 Ciências da Natureza**\n\n{sugestoes['Natureza']}")
            
            st.caption("Nota: Estas estratégias são sugestões de apoio baseadas no perfil do estudante.")

# ==========================================
# FUNÇÕES DE TRATAMENTO E PDF (PADRÃO)
# ==========================================
COLUNA_NOME = "nome"
COLUNA_DATA = "data_nascimento"

def limpar_texto(texto):
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

def calcular_idade_completa(data_nascimento):
    try:
        if not data_nascimento or str(data_nascimento).strip() == "": return ""
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

def gerar_pdf_mapa_sala_com_fotos(alunos, turma, mapa_fotos, supabase_url):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(0, 10, txt=f"Mapa de Sala - Turma {turma}", ln=True, align='C')
    pdf.ln(5)
    largura_col, altura_linha = 45, 48 
    start_x, start_y = pdf.get_x(), pdf.get_y()
    x, y = start_x, start_y
    for i, aluno in enumerate(alunos):
        nome_completo = aluno.get(COLUNA_NOME, "Sem Nome")
        raw_date = aluno.get(COLUNA_DATA) or aluno.get('Data de nascimento')
        idade_str = calcular_idade_completa(raw_date)
        try: dt_fmt = pd.to_datetime(str(raw_date).split('T')[0], errors='coerce').strftime('%d/%m/%Y') if raw_date else ""
        except: dt_fmt = ""
        legenda_pdf = f"{dt_fmt} - {idade_str}" if (dt_fmt and idade_str) else (dt_fmt or idade_str)
        pdf.set_xy(x, y); pdf.cell(largura_col, altura_linha, txt="", border=1)
        chave_busca = limpar_texto(nome_completo)
        foto_nome_arquivo = mapa_fotos.get(chave_busca)
        if foto_nome_arquivo:
            url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_nome_arquivo)}"
            try: pdf.image(url_img, x=x + (largura_col - 22)/2, y=y + 3, w=22, h=22)
            except: pass
        pdf.set_font("Arial", style='B', size=8); pdf.set_xy(x, y + 28)
        nome_str = str(nome_completo).encode('latin-1', 'replace').decode('latin-1')
        partes = nome_str.split(); nome_curto = " ".join(partes[:2]) if len(partes) > 1 else partes[0]
        pdf.cell(largura_col, 5, txt=nome_curto, border=0, align='C')
        pdf.set_font("Arial", size=7); pdf.set_xy(x, y + 34)
        pdf.cell(largura_col, 5, txt=legenda_pdf, border=0, align='C')
        if (i + 1) % 6 == 0:
            x = start_x; y += altura_linha
            if y > 150: pdf.add_page(); y = pdf.get_y()
        else: x += largura_col
    return pdf.output(dest='S').encode('latin-1')

def gerar_pdf_pendencias_fotos(pendentes):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(0, 10, txt="Relatorio de Alunos Sem Foto - EREMPAM", ln=True, align='C')
    pdf.ln(10)
    df_p = pd.DataFrame(pendentes).sort_values(by=['turma', COLUNA_NOME])
    for turma, grupo in df_p.groupby('turma'):
        pdf.set_font("Arial", style='B', size=12); pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 10, txt=f" TURMA: {turma}", ln=True, fill=True)
        pdf.set_font("Arial", size=11)
        for _, row in grupo.iterrows():
            nome_aluno = str(row[COLUNA_NOME]).encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(0, 8, txt=f" [  ] {nome_aluno}", ln=True)
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# TELA DO APP (RENDERIZAÇÃO)
# ==========================================
def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    try:
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        mapa_fotos = listar_arquivos_bucket(supabase)
        supabase_url = st.secrets['SUPABASE_URL']

        # Notificação de Pendências
        res_total = supabase.table("alunos").select("nome, turma").execute()
        alunos_sem_foto = [a for a in res_total.data if limpar_texto(a.get(COLUNA_NOME)) not in mapa_fotos]
        if alunos_sem_foto:
            with st.expander(f"⚠️ Existem {len(alunos_sem_foto)} alunos sem foto"):
                c1, c2 = st.columns([7, 3])
                c1.info("Gere a lista para organizar as sessões de fotos.")
                if c2.button("📄 Gerar Lista de Pendentes", use_container_width=True):
                    pdf_p_bytes = gerar_pdf_pendencias_fotos(alunos_sem_foto)
                    st.download_button("📥 Baixar Relatório", data=pdf_p_bytes, file_name="pendentes.pdf", mime="application/pdf")

        if lista_turmas:
            col_pills, col_btn = st.columns([8, 2], vertical_alignment="bottom")
            with col_pills:
                turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
            
            if turma_sel:
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                with col_btn:
                    if st.button("⚙️ Gerar PDF", use_container_width=True):
                        pdf_bytes = gerar_pdf_mapa_sala_com_fotos(alunos, turma_sel, mapa_fotos, supabase_url)
                        st.download_button("📥 Baixar Mapa", data=pdf_bytes, file_name=f"Mapa_{turma_sel}.pdf")

                st.divider()
                num_cols = 6
                for i in range(0, len(alunos), num_cols):
                    linha_alunos = alunos[i : i + num_cols]
                    cols = st.columns(num_cols)
                    for j, aluno in enumerate(linha_alunos):
                        with cols[j]:
                            status_aee = aluno.get('status_aee', 'Nenhum')
                            borda_cor = "#007BFF" if status_aee == "Laudo Confirmado" else "#FFC107" if status_aee == "Em Investigação" else "transparent"
                            espessura = "3px" if status_aee != "Nenhum" else "0px"
                            
                            nome = aluno.get(COLUNA_NOME, "Sem Nome")
                            chave = limpar_texto(nome)
                            foto_arq = mapa_fotos.get(chave)
                            
                            if foto_arq:
                                url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
                                img_html = f'<img src="{url_img}" style="width: 100%; height: 120px; object-fit: cover; border-radius: 8px;">'
                            else:
                                img_html = "<div style='width:100%; height:120px; background:#f0f0f0; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:48px;'>👤</div>"
                            
                            raw_date = aluno.get(COLUNA_DATA) or aluno.get('Data de nascimento')
                            idade = calcular_idade_completa(raw_date)
                            
                            st.markdown(f"""
                            <div style="border: {espessura} solid {borda_cor}; border-radius: 8px; padding: 10px; margin-bottom: 5px; text-align: center; background: white; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);">
                                {img_html}
                                <p style="font-size: 11px; font-weight: bold; margin: 8px 0 2px 0; text-transform: uppercase;">{nome[:15]}</p>
                                <p style="font-size: 10px; color: gray; margin: 0;">{idade}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if status_aee != "Nenhum":
                                if st.button("🧩 Ficha", key=f"f_{aluno['id']}", use_container_width=True):
                                    abrir_popup_aee(nome, status_aee, aluno.get('cid',''), aluno.get('relatorio_aee',''))
        else:
            st.warning("Nenhuma turma encontrada.")
    except Exception as e:
        st.error(f"Erro: {e}")
