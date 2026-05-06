import requests
import logging

class SiepeClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.siepe.educacao.pe.gov.br"
        
        # Cabeçalhos padrão baseados nos mapeamentos do seu navegador
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0',
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': self.base_url,
            'Connection': 'keep-alive'
        })

    def fazer_login(self, usuario, senha):
        """
        Realiza o login no sistema do SIEPE e armazena os Cookies de sessão (JSESSIONID).
        """
        url_login = f"{self.base_url}/GerenciadorAcessoWeb/segurancaAction.do?actionType=ajaxLogin"
        payload = {
            'login': usuario,
            'senha': senha
        }
        try:
            headers_login = {'Referer': f"{self.base_url}/GerenciadorAcessoWeb/login.do"}
            response = self.session.post(url_login, data=payload, headers=headers_login, timeout=15)
            
            if response.status_code == 200:
                logging.info("Login processado com sucesso.")
                return True, response.text
            return False, f"Erro de comunicação. Status: {response.status_code}"
        except Exception as e:
            return False, str(e)

    def enviar_notas_siepe(self, payload_dados):
        """
        Faz o envio físico do formulário de notas para o endpoint oficial do servlet.
        """
        url_save = f"{self.base_url}/GerenciadorAcessoWeb/EWServlet.ew"
        
        # Referer obrigatório identificado nos cabeçalhos da requisição
        headers_save = {
            'Referer': 'https://www.siepe.educacao.pe.gov.br/diarioclasse/DiarioClasse.do?&dummy=1778106432709'
        }
        
        try:
            response = self.session.post(url_save, data=payload_dados, headers=headers_save, timeout=20)
            if response.status_code == 200:
                return True, "Notas integradas com sucesso!"
            return False, f"O servidor retornou um erro código {response.status_code}"
        except Exception as e:
            return False, f"Falha de conexão com o SIEPE: {str(e)}"

    def sincronizar_dataframe_ao_siepe(self, df_view, ids_contexto):
        """
        PASSO 2: Mapeia o DataFrame do Streamlit para o formato exato exigido pelo formulário do SIEPE.
        """
        # Monta a estrutura base fixa do ciclo de requisição do formulário
        payload = {
            "idAbaSelecionada": "2",
            "idAbaSelecionadaPedagogico": "2",
            "hdnMetodosCarregados": "selecionarAba",
            "ddlSerieNotaFalta": ids_contexto.get('turma_id'),
            "ddlPeriodo": ids_contexto.get('bimestre', "1"),
            "ddlDisciplina": ids_contexto.get('disciplina_id'),
            "inputConceitos": "null",
            "EWBase": ids_contexto.get('ew_base'),
            "EWId": ids_contexto.get('ew_id'),
            "EWAction": "raiseEvent",
            "EWMethod": "btnGravarNotasFaltasDisciplina_onclick",
            "dummy": ids_contexto.get('dummy')
        }

        # Varre cada linha da tabela de notas gerada na interface do App
        for _, row in df_view.iterrows():
            id_siepe = str(row['aluno_id']) # Garante o uso do ID de estudante do SIEPE
            
            # Função interna para converter o ponto flutuante do Python em string com vírgula padrão do SIEPE
            def fmt(v): 
                return str(v).replace('.', ',') if (v is not None and v > 0) else ""

            # Associa as notas AT1 a AT5 e a prova N2 (campo nota_7) aos IDs dinâmicos de cada aluno
            payload[f"nota_1_{id_siepe}"] = fmt(row['AT1'])
            payload[f"nota_2_{id_siepe}"] = fmt(row['AT2'])
            payload[f"nota_3_{id_siepe}"] = fmt(row['AT3'])
            payload[f"nota_4_{id_siepe}"] = fmt(row['AT4'])
            payload[f"nota_5_{id_siepe}"] = fmt(row['AT5'])
            payload[f"nota_7_{id_siepe}"] = fmt(row['N2'])

        # Encaminha o dicionário formatado para envio
        return self.enviar_notas_siepe(payload)