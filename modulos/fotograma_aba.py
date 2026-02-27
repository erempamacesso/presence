import streamlit as st
import unicodedata
from urllib.parse import quote
import time
from fpdf import FPDF

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def limpar_texto(texto):
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

# 1ª OTIMIZAÇÃO: Guarda a lista de fotos na memória por 10 minutos (600s)
@st.cache_data(ttl=600)
def listar_arquivos_bucket(_supabase):
    try:
        arquivos = _supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
    except: return {}

# ==========================================
# GERADOR DE PDF (MANTIDO IGUAL)
# ==========================================
def gerar_pdf_mapa_sala_com_fotos(alunos, turma, mapa_fotos, supabase_url):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(0, 10, txt=f"Mapa de Sala - Turma {turma}", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", size=9)
    
    largura_col = 45 
    altura_linha = 40
    
    start_x = pdf.get_x()
    start_y = pdf.get_y()
    
    x = start_x
    y = start_y
    
    for i, aluno in enumerate(alunos):
        nome_completo = str(aluno['nome']).encode('latin-1', 'ignore').decode('latin-1')
        partes_nome = nome_completo.split()
        nome_curto = " ".join(partes_nome[:2]) if len(partes_nome) > 1 else partes_nome[0]
        
        pdf.set_xy(x, y)
        pdf.cell(largura_col, altura_linha, txt="", border=1)
        
        chave = limpar_texto(aluno['nome'])
        foto_arq = mapa_fotos.get(chave)
        
        if foto_arq:
            url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
            img_size = 22
            img_x = x + (largura_col - img_size) / 2
            img_y = y + 4
            
            try:
                pdf.image(url_img, x=img_x, y=img_y, w=img_size, h=img_size)
            except Exception:
                pdf.set_xy(x, img_y + 5)
                pdf.cell(largura_col, 5, txt="(Sem Foto)", border=0, align='C')
        
        pdf.set_xy(x, y + 28)
        pdf.cell(largura_col, 10, txt=nome_curto, border=0, align='C')
        
        if (i + 1) % 6 == 0:
            x = start_x
            y += altura_linha
            if y > 160: 
                pdf.add_page()
                x = start_x
                y = pdf.get_y()
        else:
            x += largura_col
            
    try:
        out = pdf.output(dest='S')
        if isinstance(out, str): return out.encode('latin-1')
        return bytes(out)
    except Exception:
        return bytes(pdf.output())

# ==========================================
# TELA PRINCIPAL (FOTOGRAMA)
# ==========================================
def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    st.divider()
    
    try:
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        if lista_turmas:
            col_pills, col_btn = st.columns([8, 2], vertical_alignment="bottom")
            
            with col_pills:
                turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
                
            st.divider()
            
            # Reseta o botão de PDF se trocar de turma
            if "turma_pdf_atual" not in st.session_state or st.session_state.turma_pdf_atual != turma_sel:
                st.session_state.pdf_gerado = False
                st.session_state.turma_pdf_atual = turma_sel
            
            if turma_sel:
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                mapa_fotos = listar_arquivos_bucket(supabase)
                supabase_url = st.secrets['SUPABASE_URL']
                
                # --- 2ª OTIMIZAÇÃO: BOTÃO DE DOWNLOAD SOB DEMANDA ---
                with col_btn:
                    if not st.session_state.pdf_gerado:
                        if st.button("⚙️ Preparar PDF", use_container_width=True):
                            with st.spinner("Montando..."):
                                st.session_state.pdf_bytes = gerar_pdf_mapa_sala_com_fotos(alunos, turma_sel, mapa_fotos, supabase_url)
                                st.session_state.pdf_gerado = True
                                st.rerun() # Atualiza a tela para mostrar o botão de baixar
                    else:
                        st.download_button(
                            label="📥 Baixar PDF",
                            data=st.session_state.pdf_bytes,
                            file_name=f"Mapa_Sala_Fotos_{turma_sel.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary"
                        )
                
                # --- GRADE DE FOTOS NA TELA DO APP ---
                num_cols = 6
                for i in range(0, len(alunos), num_cols):
                    linha_alunos = alunos[i : i + num_cols]
                    cols = st.columns(num_cols)
                    
                    for j, aluno in enumerate(linha_alunos):
                        with cols[j]:
                            with st.container(border=True):
                                chave = limpar_texto(aluno['nome'])
                                foto_arq = mapa_fotos.get(chave)
                                
                                if foto_arq:
                                    url_base = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
                                    # 3ª OTIMIZAÇÃO: Removido o cache-buster (?t=...) para a imagem carregar instantaneamente
                                    st.image(url_base, use_container_width=True)
                                else:
                                    st.markdown("<div style='height:80px; background:#f9f9f9; display:flex; align-items:center; justify-content:center; border-radius:8px; border: 1px dashed #ccc; font-size:24px;'>👤</div>", unsafe_allow_html=True)
                                
                                st.markdown(f"<p style='text-align:center; font-size:10px; font-weight:bold; margin-top:4px; line-height:1.1;'>{aluno['nome']}</p>", unsafe_allow_html=True)
        else:
            st.warning("Nenhuma turma encontrada.")
    except Exception as e:
        st.error(f"Erro na conexão do banco: {e}")
