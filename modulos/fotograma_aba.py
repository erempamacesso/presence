import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
from fpdf import FPDF
from datetime import datetime
import simple_icd_10 as icd

# ==========================================
# 🧠 MOTOR DE INTELIGÊNCIA (CIDs Múltiplos)
# ==========================================
def buscar_descricao_cid_hardcore(cid_input):
    if not cid_input: return ""
    partes = str(cid_input).replace('+', ' ').replace('/', ' ').replace(',', ' ').split()
    resultados = []
    for item in partes:
        codigo = item.strip().upper().replace("CID", "").replace(":", "")
        try:
            if icd.is_valid_item(codigo):
                desc_en = icd.get_description(codigo)
                termos = {
                    "Autism": "Autismo", "Disorders": "Transtornos", 
                    "Attention deficit": "TDAH", "Mental retardation": "Def. Intelectual", 
                    "Epilepsy": "Epilepsia", "Specific": "Específicos",
                    "Developmental": "do Desenvolvimento", "Hyperkinetic": "Hipercinéticos",
                    "Conduct": "Conduta", "Depressive": "Depressivo"
                }
                for en, pt in termos.items(): desc_en = desc_en.replace(en, pt)
                resultados.append(f"{codigo} ({desc_en})")
            else:
                resultados.append(codigo)
        except:
            resultados.append(codigo)
    return " - " + ", ".join(resultados) if resultados else ""

def gerar_sugestoes_ia(relatorio):
    rel = str(relatorio).lower()
    dicas = {
        "Linguagens": "Priorizar multiletramentos e suporte visual (pictogramas).",
        "Matemática": "Uso de materiais concretos e situações-problema curtas.",
        "Natureza": "Atividades experimentais e observação prática.",
        "Humanas": "Mapas conceituais e debates com mediação visual."
    }
    if "ler" in rel or "leitura" in rel or "alfabetiza" in rel:
        dicas["Linguagens"] = "⚠️ Foco urgente em consciência fonológica e pareamento de imagem/palavra."
    if "foco" in rel or "concentra" in rel or "agita" in rel:
        dicas["Matemática"] = "Dividir tarefas em blocos de 10 min com comandos únicos."
    return dicas

# ==========================================
# 🧩 POPUPS (AEE, BUSCA ATIVA, OCORRÊNCIA E ZOOM)
# ==========================================
@st.dialog("🧩 Ficha de Inclusão e AEE")
def abrir_popup_aee(nome, status, cid, relatorio):
    st.subheader(nome)
    desc = buscar_descricao_cid_hardcore(cid)
    
    if status == "Em Investigação": st.warning(f"🟡 **Status:** {status}")
    else: st.info(f"🔵 **Status:** {status}")
        
    st.markdown(f"**CID(s):** `{cid}` {desc}")
    
    if relatorio:
        with st.expander("📝 Relatório Original", expanded=True):
            st.write(relatorio)
            
    st.divider()
    st.subheader("🤖 Estratégias por Área")
    
    if st.button("✨ Gerar Propostas de Atividades", use_container_width=True):
        with st.spinner("IA Analisando perfil..."):
            sugestoes = gerar_sugestoes_ia(relatorio)
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**📚 Linguagens**\n\n{sugestoes['Linguagens']}")
                st.info(f"**🌍 Humanas**\n\n{sugestoes['Humanas']}")
            with c2:
                st.success(f"**🔢 Matemática**\n\n{sugestoes['Matemática']}")
                st.success(f"**🔬 Natureza**\n\n{sugestoes['Natureza']}")

@st.dialog("🔎 Histórico de Busca Ativa")
def abrir_popup_busca_ativa(aluno_id, nome, supabase):
    st.subheader(nome)
    st.write("Histórico de ações realizadas pela equipe:")
    
    try:
        res = supabase.table("historico_busca_ativa").select("*").eq("aluno_id", aluno_id).order("data_registro", desc=True).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data_registro']).dt.strftime('%d/%m/%Y às %H:%M')
            
            for _, row in df.iterrows():
                with st.container(border=True):
                    st.caption(f"📅 {row['data']} | 👤 Registro por: {row.get('quem_registrou', 'Equipe')}")
                    st.markdown(f"**Ação Tomada:** {row['acao_realizada']}")
                    
                    status_cor = "red" if "Evasão" in row['status_atual'] else "orange" if "acompanhamento" in row['status_atual'] else "green"
                    st.markdown(f"**Status Atual:** :{status_cor}[{row['status_atual']}]")
        else:
            st.warning("Nenhum histórico registrado ainda, mas o aluno está no radar de alerta.")
    except Exception as e:
        st.error(f"Erro ao buscar histórico: {e}")

@st.dialog("🚨 Ocorrências Disciplinares")
def abrir_popup_ocorrencia(aluno_id, nome, supabase):
    st.subheader(nome)
    st.write("Histórico de ocorrências ativas:")
    
    try:
        res = supabase.table("ocorrencias_disciplinares").select("*").eq("aluno_id", aluno_id).order("created_at", desc=True).execute()
        
        if res.data:
            for row in res.data:
                with st.container(border=True):
                    data_fmt = pd.to_datetime(row['created_at']).strftime('%d/%m/%Y')
                    st.caption(f"📅 Registrado em: {data_fmt} por {row.get('quem_registrou', 'Sistema')}")
                    st.error(f"**Ação:** {row.get('tipo_ocorrencia', 'Não informada')}")
                    st.markdown(f"**Motivo:** {row.get('motivo', 'Não detalhado')}")
                    if row.get('data_retorno'):
                        data_retorno_fmt = pd.to_datetime(row['data_retorno']).strftime('%d/%m/%Y')
                        st.markdown(f"**Data de Retorno:** {data_retorno_fmt}")
        else:
            st.success("Este estudante não possui ocorrências recentes.")
    except Exception as e:
        st.error(f"Erro ao buscar ocorrências: {e}")

@st.dialog("📸 Foto Ampliada")
def abrir_popup_foto(nome, url_img):
    st.subheader(nome)
    st.image(url_img, use_container_width=True)

# ==========================================
# 🛠️ FUNÇÕES DE TRATAMENTO E CACHE (OTIMIZADAS PARA GITHUB)
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

# 👇 NOVA FUNÇÃO: Busca direto do GitHub
@st.cache_data(ttl=3600)
def listar_fotos_github():
    try:
        from github import Github, Auth
        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        repo = g.get_repo("erempamacesso/presence")
        contents = repo.get_contents("alunos_fotos")
        # Retorna { 'nomelimpo': 'url_direta_do_github' }
        return {limpar_texto(arq.name): arq.download_url for arq in contents}
    except Exception as e:
        return {}

# ==========================================
# 🖨️ GERADORES DE PDF 
# ==========================================
def gerar_pdf_pendencias(turma, alunos_pendentes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"Pendencias de Fotos - Turma {turma}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(140, 10, "Nome do Estudante", 1)
    pdf.cell(50, 10, "Status", 1, ln=True, align='C')
    pdf.set_font("Arial", "", 10)
    for a in alunos_pendentes:
        pdf.cell(140, 10, str(a['nome'])[:50], 1)
        pdf.cell(50, 10, "[ ] Foto Coletada", 1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

def gerar_pdf_fotograma_impresso(turma, alunos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"Mapa de Sala (Fotograma Nominal) - {turma}", ln=True, align='C')
    pdf.set_font("Arial", "I", 10)
    pdf.cell(190, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 9)
    col_width = 90
    row_height = 8
    
    for i in range(0, len(alunos), 2):
        a1 = alunos[i]
        a2 = alunos[i+1] if i+1 < len(alunos) else None
        
        stat1 = "[AEE]" if a1.get('status_aee', 'Nenhum') != 'Nenhum' else ""
        txt1 = f"{stat1} {str(a1.get('nome', ''))[:40]}"
        pdf.cell(col_width, row_height, txt1, border=1)
        
        if a2:
            stat2 = "[AEE]" if a2.get('status_aee', 'Nenhum') != 'Nenhum' else ""
            txt2 = f"{stat2} {str(a2.get('nome', ''))[:40]}"
            pdf.cell(col_width, row_height, txt2, border=1, ln=True)
        else:
            pdf.cell(col_width, row_height, "", border=1, ln=True)
            
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 📸 EXIBIÇÃO DO FOTOGRAMA PRINCIPAL
# ==========================================
def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    
    try:
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        # 👇 Chama a função nova do GitHub
        mapa_fotos = listar_fotos_github()

        # Buscando alunos em Busca Ativa
        res_busca = supabase.table("historico_busca_ativa").select("aluno_id").in_("status_atual", ["Em acompanhamento", "Alerta"]).execute()
        alunos_em_busca = {r['aluno_id'] for r in res_busca.data} if res_busca.data else set()

        # Buscando alunos com ocorrência disciplinar ativa
        res_ocorrencias = supabase.table("ocorrencias_disciplinares").select("aluno_id").eq("status", "Ativa").execute()
        alunos_com_ocorrencia = {r['aluno_id'] for r in res_ocorrencias.data} if res_ocorrencias.data else set()

        res_todos_alunos = supabase.table("alunos").select("nome").execute()
        total_sem_foto_escola = sum(1 for a in res_todos_alunos.data if limpar_texto(a.get('nome')) not in mapa_fotos)
        
        if total_sem_foto_escola > 0:
            st.info(f"🏫 **Visão Geral:** Faltam **{total_sem_foto_escola}** fotos para completar 100% do mapa da escola.")
        else:
            st.success("🏫 **Visão Geral:** Parabéns! 100% dos estudantes estão com foto cadastrada.")

        if lista_turmas:
            turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
            
            if turma_sel:
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                alunos_sem_foto = [a for a in alunos if limpar_texto(a.get('nome')) not in mapa_fotos]
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    pdf_mapa = gerar_pdf_fotograma_impresso(turma_sel, alunos)
                    st.download_button("🖨️ Imprimir Mapa Nominal (PDF)", data=pdf_mapa, file_name=f"Mapa_Sala_{turma_sel}.pdf", mime="application/pdf", use_container_width=True)
                
                if alunos_sem_foto:
                    with col_btn2:
                        with st.popover(f"🚩 {len(alunos_sem_foto)} Fotos Pendentes nesta Turma", use_container_width=True):
                            st.write("Estes alunos precisam de foto atualizada:")
                            st.dataframe(pd.DataFrame([{"Nome": a['nome']} for a in alunos_sem_foto]), hide_index=True)
                            pdf_pend = gerar_pdf_pendencias(turma_sel, alunos_sem_foto)
                            st.download_button("📄 Baixar Lista de Busca", data=pdf_pend, file_name=f"Busca_Fotos_{turma_sel}.pdf", mime="application/pdf", use_container_width=True, type="primary")

                st.divider()
                
                # --- GRID DE FOTOS COM LÓGICA DE MÚLTIPLAS CORES ---
                num_cols = 4 
                for i in range(0, len(alunos), num_cols):
                    linha_alunos = alunos[i : i + num_cols]
                    cols = st.columns(num_cols)
                    
                    for j, aluno in enumerate(linha_alunos):
                        with cols[j]:
                            status_aee = aluno.get('status_aee', 'Nenhum')
                            is_aee = status_aee != "Nenhum"
                            is_busca = aluno['id'] in alunos_em_busca
                            is_ocorrencia = aluno['id'] in alunos_com_ocorrencia
                            
                            cores_borda = []
                            if is_aee: 
                                cores_borda.append("#007BFF" if status_aee == "Laudo Confirmado" else "#FFC107") 
                            if is_busca: 
                                cores_borda.append("#FF9800") 
                            if is_ocorrencia: 
                                cores_borda.append("#E53935") 
                            
                            if len(cores_borda) == 1:
                                estilo_borda = f"border: 4px solid {cores_borda[0]}; background: white;"
                            elif len(cores_borda) > 1:
                                gradiente = ", ".join(cores_borda)
                                estilo_borda = f"border: 4px solid transparent; background-image: linear-gradient(white, white), linear-gradient(135deg, {gradiente}); background-origin: border-box; background-clip: padding-box, border-box;"
                            else:
                                estilo_borda = "border: 1px solid #ddd; background: white;"
                            
                            nome = aluno.get("nome", "Sem Nome")
                            chave = limpar_texto(nome)
                            
                            # 👇 Pega a URL que já veio completinha do GitHub
                            url_img = mapa_fotos.get(chave)
                            
                            if url_img:
                                img_html = f'<img src="{url_img}" style="width: 100%; height: 200px; object-fit: contain; background: #f8f9fa; border-radius: 6px;">'
                            else:
                                img_html = "<div style='width:100%; height:200px; background:#f0f0f0; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:50px;'>👤</div>"
                            
                            raw_date = aluno.get('data_nascimento') or aluno.get('Data de nascimento')
                            idade = calcular_idade_completa(raw_date)
                            try:
                                dt_fmt = pd.to_datetime(str(raw_date).split('T')[0]).strftime('%d/%m/%Y')
                            except:
                                dt_fmt = "--/--/----"
                            
                            st.markdown(f"""
                            <div style="{estilo_borda} border-radius: 12px; padding: 10px; text-align: center; min-height: 300px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); margin-bottom: 5px;">
                                {img_html}
                                <div style="margin-top: 10px;">
                                    <p style="font-size: 12px; font-weight: bold; margin: 0; text-transform: uppercase; color: #222;">{nome[:25]}</p>
                                    <p style="font-size: 11px; color: #555; margin: 4px 0 0 0;">{dt_fmt} - {idade}</p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            tem_foto = bool(url_img)
                            num_botoes = sum([1 if tem_foto else 0, 1 if is_aee else 0, 1 if is_busca else 0, 1 if is_ocorrencia else 0])
                            
                            if num_botoes > 0:
                                cols_btn = st.columns(num_botoes)
                                idx_btn = 0
                                
                                if tem_foto:
                                    with cols_btn[idx_btn]:
                                        if st.button("🔍", help="Zoom", key=f"zoom_{aluno['id']}", use_container_width=True):
                                            abrir_popup_foto(nome, url_img)
                                    idx_btn += 1
                                
                                if is_aee:
                                    with cols_btn[idx_btn]:
                                        if st.button("🧩", help="Ficha AEE", key=f"aee_{aluno['id']}", use_container_width=True):
                                            abrir_popup_aee(nome, status_aee, aluno.get('cid',''), aluno.get('relatorio_aee',''))
                                    idx_btn += 1
                                
                                if is_busca:
                                    with cols_btn[idx_btn]:
                                        if st.button("🔎", help="Busca Ativa", key=f"ba_{aluno['id']}", type="primary", use_container_width=True):
                                            abrir_popup_busca_ativa(aluno['id'], nome, supabase)
                                    idx_btn += 1

                                if is_ocorrencia:
                                    with cols_btn[idx_btn]:
                                        if st.button("🚨", help="Ocorrência Disciplinar", key=f"oc_{aluno['id']}", type="primary", use_container_width=True):
                                            abrir_popup_ocorrencia(aluno['id'], nome, supabase)
                                    idx_btn += 1
                            else:
                                st.write("") 

    except Exception as e:
        st.error(f"Erro ao carregar fotograma: {e}")