import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
import time
from fpdf import FPDF
from datetime import datetime

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def calcular_idade(data_nascimento):
    """Calcula idade lidando com diferentes formatos de data"""
    if not data_nascimento or pd.isna(data_nascimento): 
        return ""
    try:
        # Tenta converter para datetime se ainda não for
        dt_nasc = pd.to_datetime(data_nascimento, dayfirst=True, errors='coerce')
        
        if pd.isnat(dt_nasc): 
            return ""
            
        hoje = datetime.now()
        idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
        return f"{idade} anos"
    except:
        return ""

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

# ==========================================
# GERADOR DE PDF
# ==========================================
def gerar_pdf_mapa_sala_com_fotos(alunos, turma, mapa_fotos, supabase_url):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(0, 10, txt=f"Mapa de Sala - Turma {turma}", ln=True, align='C')
    pdf.ln(5)

    largura_col = 45 
    altura_linha = 46 # Espaço suficiente para nome + data/idade
    
    start_x = pdf.get_x()
    start_y = pdf.get_y()
    x, y = start_x, start_y
    
    for i, aluno in enumerate(alunos):
        # Tratamento de Nome
        nome_completo = str(aluno.get('nome', 'Sem Nome')).encode('latin-1', 'ignore').decode('latin-1')
        partes_nome = nome_completo.split()
        nome_curto = " ".join(partes_nome[:2]) if len(partes_nome) > 1 else partes_nome[0]
        
        # Busca Data (Tenta as duas formas comuns de nome de coluna)
        raw_date = aluno.get('data_nascimento') or aluno.get('Data de nascimento')
        idade_str = calcular_idade(raw_date)
        
        # Formatação da Data para o PDF
        try:
            dt_fmt = pd.to_datetime(raw_date, dayfirst=True).strftime('%d/%m/%Y') if raw_date else ""
        except:
            dt_fmt = ""
        
        info_extra = f"{dt_fmt} - {idade_str}" if dt_fmt else idade_str

        # Desenha o Box
        pdf.set_xy(x, y)
        pdf.cell(largura_col, altura_linha, txt="", border=1)
        
        # Foto
        chave = limpar_texto(aluno.get('nome', ''))
        foto_arq = mapa_fotos.get(chave)
        if foto_arq:
            url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
            img_size = 22
            try:
                pdf.image(url_img, x=x + (largura_col - img_size)/2, y=y + 3, w=img_size, h=img_size)
            except: pass
        
        # Nome (Negrito)
        pdf.set_font("Arial", style='B', size=8)
        pdf.set_xy(x, y + 27)
        pdf.cell(largura_col, 5, txt=nome_curto, border=0, align='C')
        
        # Data e Idade (Normal e menor)
        pdf.set_font("Arial", size=7)
        pdf.set_xy(x, y + 33)
        pdf.cell(largura_col, 5, txt=info_extra, border=0, align='C')
        
        # Quebra de Linha (6 colunas por linha)
        if (i + 1) % 6 == 0:
            x = start_x
            y += altura_linha
            if y > 160: 
                pdf.add_page()
                y = pdf.get_y()
        else:
            x += largura_col
            
    return bytes(pdf.output(dest='S'))

# ==========================================
# TELA PRINCIPAL (FOTOGRAMA)
# ==========================================
def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    
    try:
        # Busca turmas
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        if lista_turmas:
            col_pills, col_btn = st.columns([8, 2], vertical_alignment="bottom")
            with col_pills:
                turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
            
            if turma_sel:
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                mapa_fotos = listar_arquivos_bucket(supabase)
                supabase_url = st.secrets['SUPABASE_URL']
                
                # Download PDF
                with col_btn:
                    if st.button("⚙️ Gerar PDF", use_container_width=True):
                        with st.spinner("Gerando..."):
                            pdf_bytes = gerar_pdf_mapa_sala_com_fotos(alunos, turma_sel, mapa_fotos, supabase_url)
                            st.download_button("📥 Baixar PDF", data=pdf_bytes, 
                                             file_name=f"Mapa_{turma_sel}.pdf", mime="application/pdf")

                st.divider()

                # Grade de Fotos na Tela
                num_cols = 6
                for i in range(0, len(alunos), num_cols):
                    linha_alunos = alunos[i : i + num_cols]
                    cols = st.columns(num_cols)
                    
                    for j, aluno in enumerate(linha_alunos):
                        with cols[j]:
                            with st.container(border=True):
                                # Lógica da Foto
                                chave = limpar_texto(aluno['nome'])
                                foto_arq = mapa_fotos.get(chave)
                                
                                if foto_arq:
                                    url_base = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
                                    st.image(url_base, use_container_width=True)
                                else:
                                    st.markdown("<div style='height:80px; background:#f4f4f4; display:flex; align-items:center; justify-content:center; border-radius:8px; border: 1px dashed #ccc; font-size:24px;'>👤</div>", unsafe_allow_html=True)
                                
                                # Nome
                                st.markdown(f"<p style='text-align:center; font-size:10px; font-weight:bold; margin-bottom:0px; line-height:1.2;'>{aluno['nome']}</p>", unsafe_allow_html=True)
                                
                                # Data e Idade
                                raw_date = aluno.get('data_nascimento') or aluno.get('Data de nascimento')
                                idade = calcular_idade(raw_date)
                                try:
                                    dt_fmt = pd.to_datetime(raw_date, dayfirst=True).strftime('%d/%m/%Y') if raw_date else "--/--/----"
                                except:
                                    dt_fmt = "--/--/----"
                                
                                st.markdown(f"<p style='text-align:center; font-size:9px; color:gray; margin-top:2px;'>{dt_fmt} • {idade}</p>", unsafe_allow_html=True)
        else:
            st.warning("Nenhuma turma encontrada no banco de dados.")
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")
