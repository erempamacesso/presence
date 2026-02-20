import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime

# Conexão com o Supabase (puxando dos Secrets do Streamlit para sua segurança)
load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📅 Sistema de Reservas")
st.markdown("Reserve espaços e equipamentos da escola.")

# --- DADOS FIXOS DA ESCOLA (Altere com os nomes reais) ---
LISTA_PROFESSORES = [
    "Ana Maria (Matemática)", "Carlos Eduardo (História)", 
    "Fernanda Lima (Português)", "João Silva (Física)", "Maria Souza (Biologia)"
]

AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]
ESPACOS_TOTAIS = ["Auditório", "Laboratório de Ciências", "Sala de informática", "Biblioteca", "Refeitório", "Nenhum (Só Equipamento)"]

# Estoque da escola
TOTAL_DATASHOWS = 5
TOTAL_CAIXAS = 3
TOTAL_MICROFONES = 3

# --- ETAPA 1: ESCOLHER DATA E HORA ---
col1, col2 = st.columns(2)
with col1:
    data_selecionada = st.date_input("Data da Reserva:", min_value=datetime.today().date())
with col2:
    aula_selecionada = st.selectbox("Qual Aula?", AULAS)

# Busca no banco as reservas que já existem para esse dia e período
try:
    resposta = supabase.table("reservas").select("*").eq("data_reserva", str(data_selecionada)).eq("periodo", aula_selecionada).execute()
    reservas_existentes = resposta.data
except Exception as e:
    st.error(f"Erro ao buscar dados: {e}")
    reservas_existentes = []

# --- LÓGICA DE PREVENÇÃO DE CONFLITOS (ESPAÇOS) ---
espacos_ocupados = [reserva.get('espaco') for reserva in reservas_existentes if reserva.get('espaco') and reserva.get('espaco') != "Nenhum (Só Equipamento)"]
espacos_disponiveis = [e for e in ESPACOS_TOTAIS if e not in espacos_ocupados]

# --- LÓGICA DE INVENTÁRIO (EQUIPAMENTOS) ---
datashows_usados = sum(1 for r in reservas_existentes if r.get('equipamentos') and "Datashow" in r.get('equipamentos', ''))
caixas_usadas = sum(1 for r in reservas_existentes if r.get('equipamentos') and "Caixa de Som" in r.get('equipamentos', ''))
mics_usados = sum(1 for r in reservas_existentes if r.get('equipamentos') and "Microfone" in r.get('equipamentos', ''))

disp_data = TOTAL_DATASHOWS - datashows_usados
disp_caixa = TOTAL_CAIXAS - caixas_usadas
disp_mic = TOTAL_MICROFONES - mics_usados

opcoes_equip = []
if disp_data > 0: opcoes_equip.append(f"Datashow ({disp_data} disponíveis)")
if disp_caixa > 0: opcoes_equip.append(f"Caixa de Som ({disp_caixa} disponíveis)")
if disp_mic > 0: opcoes_equip.append(f"Microfone ({disp_mic} disponíveis)")

st.divider()

# --- ETAPA 2: FORMULÁRIO ---
with st.form("form_reserva"):
    professor = st.selectbox("👩‍🏫 Professor(a):", ["-- Selecione --"] + sorted(LISTA_PROFESSORES))
    
    if not espacos_disponiveis:
        st.error("⚠️ Todos os espaços já estão ocupados neste horário!")
        espaco = st.selectbox("📍 Espaço:", ["Nenhum (Só Equipamento)"])
    else:
        espaco = st.selectbox("📍 Espaço:", espacos_disponiveis)
    
    if not opcoes_equip:
        st.warning("⚠️ Todos os equipamentos já estão emprestados neste horário.")
        equipamentos = st.multiselect("💻 Equipamentos:", ["Nenhum disponível"])
    else:
        equipamentos = st.multiselect("💻 Equipamentos (Opcional):", opcoes_equip)
    
    observacoes = st.text_area("📝 Observações (Opcional):", placeholder="Ex: Deixar o datashow na sala dos professores...")

    enviar = st.form_submit_button("✅ Confirmar Reserva", use_container_width=True)

    if enviar:
        if professor == "-- Selecione --":
            st.warning("Por favor, selecione seu nome na lista.")
        else:
            # Limpa o texto para salvar no banco bonitinho (Tira o "4 disponíveis")
            equip_limpos = [e.split(" (")[0] for e in equipamentos if "disponíve" in e]
            equip_str = ", ".join(equip_limpos) if equip_limpos else "Nenhum"

            dados = {
                "data_reserva": str(data_selecionada),
                "periodo": aula_selecionada, 
                "professor": professor,
                "espaco": espaco,
                "equipamentos": equip_str,
                "observacoes": observacoes
            }

            try:
                supabase.table("reservas").insert(dados).execute()
                st.success("🎉 Reserva efetuada com sucesso!")
                st.balloons()
            except Exception as e:
                st.error("Erro ao salvar a reserva!")
                st.info(f"Detalhe técnico: {e}")
                st.warning("🚨 Você lembrou de criar as colunas 'equipamentos' e 'observacoes' lá no Supabase?")
