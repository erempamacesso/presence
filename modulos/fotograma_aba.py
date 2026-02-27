import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
from fpdf import FPDF
from datetime import datetime

# ==========================================
# CONFIGURAÇÕES GLOBAIS (MARCADORES)
# ==========================================
# Altere aqui se os nomes das colunas no Supabase mudarem
COLUNA_NOME = "nome"
COLUNA_DATA = "data_nascimento"  # Pode ser "Data de nascimento" também

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def calcular_idade(data_nascimento):
    """Calcula idade e retorna o termo formatado 'XX anos'"""
    if not data_nascimento or pd.isna(data_nascimento): 
        return ""
    try:
        # Converte para datetime (dayfirst=True para formato brasileiro DD/MM/AAAA)
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
    altura_linha = 46 # Altura do box
    
    start_x = pdf.get_x()
    start_y = pdf.get_y()
    x, y = start_x, start_y
    
    for i, aluno in enumerate(alunos):
        # 1. Obter Dados
        nome_original = aluno.get(COLUNA_NOME, 'Sem Nome')
        raw_date = aluno.get(COLUNA_DATA) or aluno.get('Data de nascimento')
        
        # 2. Processar Nome Curto
        nome_completo = str(nome_original).encode('latin-1', 'ignore').decode('latin-1')
        partes = nome_completo.split()
        nome_exibicao = " ".join(partes[:2]) if len(partes) > 1 else partes[0]
        
        # 3. Processar Data e Idade
        idade_str = calcular_idade(raw_date)
        try:
            dt_fmt = pd.to_datetime(raw_date, dayfirst=True).strftime('%d/%m/%Y') if raw_date else ""
        except:
            dt_fmt = ""
        
        # Formato solicitado: "DATA - XX anos"
        legenda_final = f"{dt_fmt} - {idade_str}" if (dt_fmt and idade_str) else (dt_fmt or idade_str)

        # 4. Desenhar Box e Foto
        pdf.set_xy(x, y)
        pdf.cell(largura_col, altura_linha, txt="", border=1)
        
        chave_foto = limpar_texto(nome_original)
        foto_arq = mapa_fotos.get(chave_foto)
        if foto_arq:
            url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
            try:
                pdf.image(url_img, x=x + (largura_col - 22)/2, y=y + 3, w=22, h=22)
            except: pass
        
        # 5. Textos (Nome e Data/Idade)
        pdf.set_font("Arial", style='B', size=8)
        pdf.set_xy(x, y + 27)
        pdf.cell(largura_col, 5, txt=nome_exibicao, border=0, align='C')
        
        pdf.set_font("Arial", size=7)
        pdf.set_xy(x, y + 33)
        pdf.cell(largura_col, 5, txt=legenda_final, border=0, align='C')
        
        # Lógica de colunas
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
# TELA PRINCIPAL (STREAMLIT)
# ==========================================
def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    
    try:
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
                
                with col_btn:
                    if st.button("⚙️ Gerar PDF", use_container_width=True):
                        pdf_bytes = gerar_pdf_mapa_sala_com_fotos(alunos, turma_sel, mapa_fotos, supabase_url)
                        st.download_button("📥 Baixar PDF", data=pdf_bytes, file_name=f"Mapa_{turma_sel}.pdf")

                st.divider()

                # Grade de visualização na tela
                num_cols = 6
                for i in range(0, len(alunos), num_cols):
                    linha_alunos = alunos[i : i + num_cols]
                    cols = st.columns(num_cols)
                    
                    for j, aluno in enumerate(linha_alunos):
                        with cols[j]:
                            with st.container(border=True):
                                # Foto
                                chave = limpar_texto(aluno[COLUNA_NOME])
                                foto_arq = mapa_fotos.get(chave)
                                if foto_arq:
                                    st.image(f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}", use_container_width=True)
                                else:
                                    st.markdown("<div style='height:80px; background:#f4f4f4; display:flex; align-items:center; justify-content:center; border-radius:8px; border: 1px dashed #ccc; font-size:24px;'>👤</div>", unsafe_allow_html=True)
                                
                                # Nome
                                st.markdown(f"<p style='text-align:center; font-size:10px; font-weight:bold; margin-bottom:0px;'>{aluno[COLUNA_NOME]}</p>", unsafe_allow_html=True)
                                
                                # Data e Idade (Formatado como pedido)
                                raw_date = aluno.get(COLUNA_DATA) or aluno.get('Data de nascimento')
                                idade = calcular_idade(raw_date)
                                try:
                                    dt_fmt = pd.to_datetime(raw_date, dayfirst=True).strftime('%d/%m/%Y') if raw_date else "--/--/----"
                                except:
                                    dt_fmt = "--/--/----"
                                
                                texto_legenda = f"{dt_fmt} - {idade}" if idade else dt_fmt
                                st.markdown(f"<p style='text-align:center; font-size:9px; color:gray; margin-top:2px;'>{texto_legenda}</p>", unsafe_allow_html=True)
        else:
            st.warning("Nenhuma turma encontrada.")
    except Exception as e:
        st.error(f"Erro: {e}")
