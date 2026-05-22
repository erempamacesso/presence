import requests
import toml
import time
from supabase import create_client

# =========================================
# SECRETS
# =========================================

secrets = toml.load(
    ".streamlit/secrets.toml"
)

TOKEN = secrets[
    "TELEGRAM_BOT_TOKEN"
]

SUPABASE_URL = secrets[
    "SUPABASE_URL_ALUNOS"
]

SUPABASE_KEY = secrets[
    "SUPABASE_KEY_ALUNOS"
]

# =========================================
# SUPABASE
# =========================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =========================================
# MENU INLINE
# =========================================

inline_keyboard = {

    "inline_keyboard": [

        [
            {
                "text":
                "📋 Meus estudantes",

                "callback_data":
                "meus_estudantes"
            }
        ],

        [
            {
                "text":
                "📈 Ver atrasos",

                "callback_data":
                "ver_atrasos"
            }
        ],

        [
            {
                "text":
                "🔔 Notificações",

                "callback_data":
                "notificacoes"
            }
        ],

        [
            {
                "text":
                "🛑 Sair",

                "callback_data":
                "sair"
            }
        ]

    ]

}

# =========================================
# OFFSET
# =========================================

offset = 0

print(
    "🤖 Bot online..."
)

# =========================================
# LOOP PRINCIPAL
# =========================================

while True:

    try:

        # =================================
        # GET UPDATES
        # =================================

        url = (
            f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        )

        response = requests.get(

            url,

            params={

                "offset": offset,

                "timeout": 30

            }

        )

        dados = response.json()

        # =================================
        # PROCESSA RESULTADOS
        # =================================

        for item in dados["result"]:

            offset = (
                item["update_id"] + 1
            )

            # =============================
            # MENSAGENS
            # =============================

            if "message" in item:

                mensagem = item[
                    "message"
                ].get(
                    "text",
                    ""
                )

                chat_id = str(
                    item["message"]["chat"]["id"]
                )

                print(
                    f"Mensagem: {mensagem}"
                )

                # =========================
                # START
                # =========================

                if mensagem == "/start":

                    resposta = """
Digite apenas os números do seu CPF para vincular sua conta.
"""

                    requests.post(

                        f"https://api.telegram.org/bot{TOKEN}/sendMessage",

                        json={

                            "chat_id": chat_id,

                            "text": resposta

                        }

                    )

                    print(
                        "Solicitando CPF..."
                    )

                # =========================
                # CPF
                # =========================

                elif (
                    mensagem.isdigit()
                    and
                    len(mensagem) == 11
                ):

                    cpf = mensagem

                    resultado = (

                        supabase
                        .table(
                            "responsaveis_oficiais"
                        )
                        .select(
                            "nome_responsavel"
                        )
                        .eq(
                            "cpf_responsavel",
                            cpf
                        )
                        .limit(1)
                        .execute()

                    )

                    # =====================
                    # CPF ENCONTRADO
                    # =====================

                    if resultado.data:

                        nome = resultado.data[0][
                            "nome_responsavel"
                        ]

                        (
                            supabase
                            .table(
                                "responsaveis_oficiais"
                            )
                            .update({

                                "telegram_chat_id":
                                chat_id

                            })
                            .eq(
                                "cpf_responsavel",
                                cpf
                            )
                            .execute()
                        )

                        resposta = f"""
✅ Vinculação realizada com sucesso.

Responsável:
{nome}
"""

                    # =====================
                    # CPF NÃO ENCONTRADO
                    # =====================

                    else:

                        resposta = """
❌ CPF não encontrado.

Verifique os números digitados.
"""

                    requests.post(

                        f"https://api.telegram.org/bot{TOKEN}/sendMessage",

                        json={

                            "chat_id": chat_id,

                            "text": resposta,

                            "reply_markup":
                            inline_keyboard

                        }

                    )

            # =============================
            # CALLBACK BUTTONS
            # =============================

            elif "callback_query" in item:

                callback = item[
                    "callback_query"
                ]

                data = callback[
                    "data"
                ]

                chat_id = str(
                    callback[
                        "message"
                    ][
                        "chat"
                    ][
                        "id"
                    ]
                )

                print(
                    f"Botão: {data}"
                )

                # =========================
                # MEUS ESTUDANTES
                # =========================

                if data == "meus_estudantes":

                    resposta = """
📋 Seus estudantes vinculados aparecerão aqui.
"""

                # =========================
                # VER ATRASOS
                # =========================

                elif data == "ver_atrasos":

                    resposta = """
📈 Consulta de atrasos em desenvolvimento.
"""

                # =========================
                # NOTIFICAÇÕES
                # =========================

                elif data == "notificacoes":

                    resposta = """
🔔 Notificações já estão ativadas.
"""

                # =========================
                # SAIR
                # =========================

                elif data == "sair":

                    (
                        supabase
                        .table(
                            "responsaveis_oficiais"
                        )
                        .update({

                            "telegram_chat_id":
                            None

                        })
                        .eq(
                            "telegram_chat_id",
                            chat_id
                        )
                        .execute()
                    )

                    resposta = """
✅ Seu Telegram foi desvinculado com sucesso.
"""

                # =========================
                # ENVIA RESPOSTA
                # =========================

                requests.post(

                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",

                    json={

                        "chat_id": chat_id,

                        "text": resposta

                    }

                )

    except Exception as erro:

        print(
            f"Erro: {erro}"
        )

    time.sleep(1)