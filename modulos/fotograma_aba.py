import streamlit as st
import unicodedata
from urllib.parse import quote
import time
from fpdf import FPDF

# ==========================================
# FUNÇÕES AUXILIARES E GERADOR DE PDF
# ==========================================
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

def gerar_pdf_mapa_sala(alunos, turma):
    """Gera um PDF na horizontal com uma grade de 6 colunas"""
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(0, 10, txt=f"Mapa de Sala - Turma {turma}", ln=True, align='C')
    pdf.ln(5)

    # Configurações da Grade (A4 Paisagem tem ~297mm de largura)
    pdf.set_font("Arial", size=9)
    largura_col = 46 # 6 colunas x 46 = 276mm (Deixa uma margem boa)
    altura_linha = 15
    
    # Desenha os alunos na grade
    for i, aluno in enumerate(alunos):
        # Tratamento de texto e limite de tamanho do nome
        nome_completo = str(aluno['nome']).encode('latin-1', 'ignore').decode('latin-1')
        partes_nome = nome_completo.split()
        # Pega os 2 primeiros nomes para não estourar a caixinha no PDF
        nome_curto = " ".join(partes_nome[:2]) if len(partes_nome) > 1 else partes_nome[0]
        
        # ln=1 quebra a linha quando chega no 6º aluno, ln=0 continua na mesma linha
        quebra_linha = 1 if (i + 1) % 6 == 0 else 0
        
        pdf.cell(largura_col, altura_linha, txt=nome_curto, border=1, align='C', ln=quebra_linha)
        
    return pdf.output(dest='S').encode('latin-1')


# ==========================================
# TELA PRINCIPAL
# ==========================================
def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    st.divider() # Linha separadora para organizar
    
    try:
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        if lista_turmas:
            # DIVISÃO DA TELA PARA O BOTÃO FICAR NA MESMA LINHA
            col_pills, col_btn = st.columns([8, 2], vertical_alignment="bottom")
            
            with col_pills:
                turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
                
            st.divider() # Outra linha antes de mostrar as fotos
            
            if turma_sel:
                # 1. Busca alunos em ordem alfabética
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                mapa_fotos = listar_arquivos_bucket(supabase)
                
                # 2. GERAÇÃO DO BOTÃO PDF NO CANTO DIREITO
                if alunos:
                    pdf_bytes = gerar_pdf_mapa_sala(alunos, turma_sel)
                    with col_btn:
                        st.download_button(
                            label="📥 Baixar Mapa",
                            data=pdf_bytes,
                            file_name=f"Mapa_Sala_{turma_sel.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                
                # 3. DEFINIÇÃO DA GRADE NA TELA (6 colunas)
                num_cols = 6
                
                # 4. LÓGICA DE LINHAS (Garante ordem alfabética no celular)
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
                                st.markdown(f"<p style='text-align:center; font-size:10px; font-weight:bold; margin-top:4px; line-height:1.1;'>{aluno['nome']}</p>", unsafe_allow_html=True)
        else:
            st.warning("Nenhuma turma encontrada.")
    except Exception as e:
        st.error(f"Erro no Fotograma: {e}")
