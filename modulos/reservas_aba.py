import streamlit as st
import pandas as pd
import datetime
from streamlit_calendar import calendar

# --- GESTORES COM PRIVILÉGIO TOTAL ---
# Apenas os nomes dos gestores. A validação das senhas vem direto do banco!
GESTORES = ["Lilian Jordão", "Jackson Carvalho", "Lylian Cabral"]

def exibir_reservas(supabase, lista_professores_antiga, aulas_opcoes, espacos, arg1=None, arg2=None, arg3=None):
    st.title("📅 Sistema de Reservas")
    
    # -----------------------------------------
    # 1. BUSCAR TODOS OS NOMES DO BANCO DE DADOS
    # -----------------------------------------
    lista_pessoas = []
    try:
        res_prof = supabase.table("professores_matriculas").select("professor").execute()
        if res_prof.data:
            # Pega os nomes, tira duplicatas e organiza em ordem alfabética
            lista_pessoas = sorted(list(set([p['professor'] for p in res_prof.data])))
    except Exception as e:
        st.error(f"Erro ao buscar lista no banco: {e}")
        lista_pessoas = lista_professores_antiga # Backup de segurança

    # Cria a lista formatada para os selects das outras abas
    opcoes_professores = ["-- Selecione --"] + lista_pessoas

    # -----------------------------------------
    # 2. CRIANDO AS ABAS
    # -----------------------------------------
    aba_cal, aba_lista, aba_nova, aba_cancelar, aba_assinatura = st.tabs([
        "🗓️ Calendário Mensal", 
        "📋 Lista Diária", 
        "✍️ Nova Reserva", 
        "❌ Gerenciar/Cancelar",
        "🔑 Cadastrar Assinatura"
    ])

    # -----------------------------------------
    # ABA 1: CALENDÁRIO MENSAL (Em Português e Limpo)
    # -----------------------------------------
    with aba_cal:
        st.subheader("Visão Geral do Mês")
              
        try:
            # Busca apenas reservas ativas
            res_cal = supabase.table("reservas").select("*").eq("status", "Ativa").execute()
            
            if res_cal.data:
                eventos = []
                for r in res_cal.data:
                    # Captura os dados e evita o erro de "None"
                    prof = r.get('professor', '')
                    espaco = r.get('espaco', '')
                    equip = r.get('equipamentos')
                    
                    if equip and str(equip).strip() != "" and str(equip).strip() != "None":
                        titulo_limpo = f"{prof} - {espaco} - {equip}"
                    else:
                        titulo_limpo = f"{prof} - {espaco}"
                    
                    eventos.append({
                        "title": titulo_limpo,
                        "start": r['data_reserva'],
                        "end": r['data_reserva'],
                        "backgroundColor": "#1f77b4" # Cor do bloco
                    })
                
                # Configurações do Calendário Visual (Brasil)
                calendar_options = {
                    "locale": "pt-br",
                    "headerToolbar": {
                        "left": "today prev,next",
                        "center": "title",
                        "right": "dayGridMonth,timeGridWeek"
                    },
                    "initialView": "dayGridMonth",
                    "buttonText": {
                        "today": "Hoje",
                        "month": "Mês",
                        "week": "Semana"
                    }
                }
                
                # Renderiza o calendário
                calendar(events=eventos, options=calendar_options)
            else:
                st.info("Nenhuma reserva encontrada para exibir no calendário.")
                
        except Exception as e:
            st.error(f"Erro ao carregar calendário: {e}")

    # -----------------------------------------
    # ABA 2: LISTA DIÁRIA (Com proteção anti-erros)
    # -----------------------------------------
    with aba_lista:
        st.subheader("Visão Diária por Espaço")
        data_filtro = st.date_input("Ver detalhes do dia:", value=datetime.date.today(), key="data_lista")
        
        try:
            res = supabase.table("reservas").select("*").eq("data_reserva", str(data_filtro)).execute()
            if res.data:
                df_dia = pd.DataFrame(res.data)
                
                for espaco_atual in espacos:
                    # Filtra apenas se a coluna espaco existir para não quebrar
                    if 'espaco' in df_dia.columns:
                        df_espaco = df_dia[df_dia['espaco'] == espaco_atual]
                        
                        if not df_espaco.empty:
                            with st.expander(f"📍 {espaco_atual} ({len(df_espaco)} reservas)", expanded=True):
                                # Filtra colunas disponíveis para não dar KeyError
                                colunas_desejadas = ['aula', 'professor', 'equipamentos', 'obs', 'status']
                                colunas_existentes = [c for c in colunas_desejadas if c in df_espaco.columns]
                                
                                df_exibir = df_espaco[colunas_existentes].copy()
                                
                                # Ajusta o status visual se a coluna existir
                                if 'status' in df_exibir.columns:
                                    df_exibir['status'] = df_exibir['status'].apply(
                                        lambda x: "🟢 Ativa" if x == "Ativa" else "🔴 Cancelada"
                                    )
                                
                                # Traduz os cabeçalhos
                                df_exibir = df_exibir.rename(columns={
                                    'aula': 'Aula', 
                                    'professor': 'Professor', 
                                    'equipamentos': 'Equipamentos', 
                                    'obs': 'Observações', 
                                    'status': 'Status'
                                })
                                
                                st.dataframe(df_exibir, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma reserva para esta data.")
        except Exception as e:
            st.error(f"Erro ao carregar lista diária: {e}")

    # -----------------------------------------
    # ABA 3: NOVA RESERVA
    # -----------------------------------------
    with aba_nova:
        st.subheader("Agendar Espaço")
        with st.form("form_nova_reserva"):
            col1, col2 = st.columns(2)
            with col1:
                data_reserva = st.date_input("Data:", value=datetime.date.today())
                aula = st.selectbox("Aula:", aulas_opcoes)
                professor = st.selectbox("Professor:", opcoes_professores)
            with col2:
                espaco = st.selectbox("Espaço:", ["-- Selecione --"] + espacos)
                equipamentos = st.text_input("Equipamentos (Opcional):", placeholder="Ex: Data show, Caixa de som")
                obs = st.text_input("Observações (Opcional):")
            
            btn_salvar = st.form_submit_button("💾 Confirmar Reserva")

            if btn_salvar:
                if professor == "-- Selecione --" or espaco == "-- Selecione --":
                    st.warning("⚠️ Selecione o Professor e o Espaço.")
                else:
                    conflito = supabase.table("reservas").select("id").eq("data_reserva", str(data_reserva))\
                        .eq("aula", aula).eq("espaco", espaco).eq("status", "Ativa").execute()
                    
                    if conflito.data:
                        st.error(f"🚨 CONFLITO! O espaço '{espaco}' já está reservado na {aula} para o dia {data_reserva.strftime('%d/%m/%Y')}.")
                    else:
                        try:
                            dados = {
                                "data_reserva": str(data_reserva),
                                "aula": aula,
                                "professor": professor,
                                "espaco": espaco,
                                "equipamentos": equipamentos,
                                "obs": obs,
                                "status": "Ativa" 
                            }
                            supabase.table("reservas").insert(dados).execute()
                            st.success("✅ Reserva confirmada com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

    # -----------------------------------------
    # ABA 4: GERENCIAR E CANCELAR
    # -----------------------------------------
    with aba_cancelar:
        st.subheader("Cancelar uma Reserva")
        st.info("Apenas gestores ou o próprio professor que reservou podem cancelar.")
        
        data_canc = st.date_input("Data da reserva a cancelar:", value=datetime.date.today(), key="data_canc")
        
        try:
            # Busca todas as matrículas para validar a assinatura
            MATRICULAS_DB = {}
            try:
                res_mat = supabase.table("professores_matriculas").select("*").execute()
                if res_mat.data:
                    MATRICULAS_DB = {str(r['matricula']): r['professor'] for r in res_mat.data}
            except:
                pass 

            res_ativas = supabase.table("reservas").select("*").eq("data_reserva", str(data_canc)).eq("status", "Ativa").execute()
            
            if res_ativas.data:
                opcoes_canc = {f"{r['aula']} - {r['espaco']} ({r['professor']})": r['id'] for r in res_ativas.data}
                
                reserva_selecionada = st.selectbox("Selecione a Reserva para cancelar:", ["-- Selecione --"] + list(opcoes_canc.keys()))
                
                if reserva_selecionada != "-- Selecione --":
                    id_reserva = opcoes_canc[reserva_selecionada]
                    prof_da_reserva = next(r['professor'] for r in res_ativas.data if r['id'] == id_reserva)
                    
                    st.warning("⚠️ SUA MATRÍCULA NÃO FICARÁ EXPOSTA. DIGITE-A ABAIXO PARA ASSINAR O CANCELAMENTO.")
                    matricula_input = st.text_input("Assinatura Eletrônica (Sua Matrícula):", type="password", help="Digite apenas números")
                    
                    if st.button("🗑️ Confirmar Cancelamento", type="primary"):
                        if matricula_input in MATRICULAS_DB:
                            usuario_nome = MATRICULAS_DB[matricula_input]
                            
                            # Verifica se o assinante é um Gestor ou o Dono da reserva
                            if usuario_nome in GESTORES or usuario_nome == prof_da_reserva:
                                supabase.table("reservas").update({
                                    "status": "Cancelada", 
                                    "cancelado_por": usuario_nome
                                }).eq("id", id_reserva).execute()
                                
                                st.success(f"✅ Reserva cancelada com sucesso por {usuario_nome}.")
                                st.rerun()
                            else:
                                st.error("⛔ Você não tem permissão para cancelar a reserva de outro professor.")
                        else:
                            st.error("❌ Matrícula inválida. Vá na aba 'Cadastrar Assinatura' para registrar sua matrícula.")
            else:
                st.info("Não há reservas ativas para cancelar neste dia.")
        except Exception as e:
            st.error(f"Erro no módulo de cancelamento: {e}")

    # -----------------------------------------
    # ABA 5: CADASTRAR ASSINATURA
    # -----------------------------------------
    with aba_assinatura:
        st.subheader("Cadastro de Assinatura")
        st.error("🔒 PRIVACIDADE GARANTIDA: SUA MATRÍCULA NÃO FICARÁ EXPOSTA EM NENHUMA TELA DO SISTEMA. ELA É USADA APENAS COMO SENHA DE CANCELAMENTO.")
        
        prof_selecionado = st.selectbox("1. Selecione seu Nome:", opcoes_professores)
        matricula_nova = st.text_input("2. Digite sua Matrícula (Apenas números):", type="password")
        
        if st.button("💾 Salvar Minha Assinatura"):
            if prof_selecionado == "-- Selecione --" or not matricula_nova.isdigit():
                st.warning("⚠️ Selecione seu nome e digite apenas números na matrícula.")
            else:
                try:
                    existe = supabase.table("professores_matriculas").select("*").eq("professor", prof_selecionado).execute()
                    
                    if existe.data:
                        supabase.table("professores_matriculas").update({"matricula": matricula_nova}).eq("professor", prof_selecionado).execute()
                    else:
                        supabase.table("professores_matriculas").insert({"professor": prof_selecionado, "matricula": matricula_nova}).execute()
                    
                    st.success(f"✅ Assinatura de {prof_selecionado} cadastrada com sucesso! Agora você pode cancelar suas reservas.")
                except Exception as e:
                    st.error(f"Erro ao salvar matrícula: {e}")
