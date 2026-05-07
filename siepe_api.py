import requests
import logging
import time

class SiepeClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.siepe.educacao.pe.gov.br"
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.base_url,
            'Connection': 'keep-alive'
        })

    def fazer_login(self, usuario, senha):
        """Realiza login e captura o Cookie JSESSIONID automaticamente."""
        url_login = f"{self.base_url}/GerenciadorAcessoWeb/segurancaAction.do?actionType=ajaxLogin"
        payload = {'login': usuario, 'senha': senha}
        try:
            # O Referer é crucial para o SIEPE aceitar o POST de login
            headers = {'Referer': f"{self.base_url}/GerenciadorAcessoWeb/login.do"}
            response = self.session.post(url_login, data=payload, headers=headers, timeout=15)
            
            if response.status_code == 200 and "sucesso" in response.text.lower():
                logging.info("Sessão iniciada no SIEPE.")
                return True, "Login realizado com sucesso."
            return False, "Usuário ou senha inválidos no SIEPE."
        except Exception as e:
            return False, f"Erro de conexão: {str(e)}"

    def sincronizar_dataframe_ao_siepe(self, df_view, ids_contexto):
        """Transforma o DataFrame em um POST multi-aluno para o EWServlet."""
        url_save = f"{self.base_url}/GerenciadorEficiencia/EWServlet.ew"
        
        # O parâmetro 'dummy' é um timestamp para evitar cache
        ts_dummy = str(int(time.time() * 1000))
        
        payload = {
            "idAbaSelecionada": "2",
            "hdnMetodosCarregados": "selecionarAba",
            "ddlSerieNotaFalta": ids_contexto.get('turma_id'),
            "ddlPeriodo": ids_contexto.get('bimestre', "1"),
            "ddlDisciplina": ids_contexto.get('disciplina_id'),
            "EWBase": ids_contexto.get('ew_base'),
            "EWId": ids_contexto.get('ew_id'),
            "EWAction": "raiseEvent",
            "EWMethod": "btnGravarNotasFaltasDisciplina_onclick",
            "dummy": ts_dummy
        }

        count_alunos = 0
        for _, row in df_view.iterrows():
            # USANDO O ID DO ESTUDANTE (8 DÍGITOS) DO SUPABASE
            # Certifique-se que a coluna no DF se chama 'id_siepe'
            id_aluno = str(row.get('id_siepe', ''))
            
            if not id_aluno or id_aluno == 'None':
                continue

            def fmt(v):
                if pd.isna(v) or v is None: return ""
                # O SIEPE exige vírgula e formato string
                return str(float(v)).replace('.', ',')

            # Mapeamento dos campos conforme o padrão do formulário SIEPE
            payload[f"nota_1_{id_aluno}"] = fmt(row.get('AT1'))
            payload[f"nota_2_{id_aluno}"] = fmt(row.get('AT2'))
            payload[f"nota_3_{id_aluno}"] = fmt(row.get('AT3'))
            payload[f"nota_4_{id_aluno}"] = fmt(row.get('AT4'))
            payload[f"nota_5_{id_aluno}"] = fmt(row.get('AT5'))
            payload[f"nota_7_{id_aluno}"] = fmt(row.get('N2')) # Campo da Prova/N2
            count_alunos += 1

        try:
            # Referer dinâmico para mimetizar a navegação real
            headers_save = {'Referer': f"{self.base_url}/diarioclasse/DiarioClasse.do?&dummy={ts_dummy}"}
            response = self.session.post(url_save, data=payload, headers=headers_save, timeout=30)
            
            if response.status_code == 200:
                if "caixaAviso" in response.text:
                    return True, f"Sucesso! {count_alunos} alunos sincronizados."
                return False, "O servidor processou, mas não confirmou a gravação."
            return False, f"Erro no servidor SIEPE: {response.status_code}"
        except Exception as e:
            return False, f"Falha na integração: {str(e)}"