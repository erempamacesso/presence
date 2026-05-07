import requests
import pandas as pd
import time

class SiepeClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.siepe.educacao.pe.gov.br"
        
        # Simulando um navegador real
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        })

    def fazer_login(self, usuario, senha):
        """
        Realiza o login no SIEPE pelo endpoint AJAX oficial, aceitando letras e números.
        """
        try:
            # 1. Puxa a página inicial para gerar os cookies (JSESSIONID)
            self.session.get(f"{self.base_url}/GerenciadorAcessoWeb/login.do", timeout=10)

            # 2. Faz o POST no endpoint correto de login do governo
            dummy_time = str(int(time.time() * 1000))
            url_login = f"{self.base_url}/GerenciadorAcessoWeb/segurancaAction.do?actionType=ajaxLogin&dummy={dummy_time}"
            
            payload = {
                'login': usuario,
                'senha': senha
            }
            
            headers_login = {
                'Referer': f"{self.base_url}/GerenciadorAcessoWeb/login.do",
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # Executa a tentativa de login
            response = self.session.post(url_login, data=payload, headers=headers_login, timeout=15)
            
            if response.status_code == 200:
                texto_resp = response.text.lower()
                # Verifica se o portal devolveu mensagem de erro de senha
                if "inválido" in texto_resp or "erro" in texto_resp or "incorreto" in texto_resp:
                    return False, "Usuário ou senha incorretos."
                
                # 3. Prova de fogo: Tenta abrir a página principal do diário de classe
                res_home = self.session.get(f"{self.base_url}/diarioclasse/DiarioClasse.do")
                if "Sair" in res_home.text or "Minhas Turmas" in res_home.text or "Agamenon" in res_home.text:
                    return True, "Login realizado com sucesso!"
                else:
                    return False, "A senha passou, mas o portal bloqueou o acesso ao Diário."
                    
            return False, f"Erro de comunicação com o portal: Status {response.status_code}"
        except Exception as e:
            return False, f"Erro de conexão com a internet: {str(e)}"

    def sincronizar_dataframe_ao_siepe(self, df_view, ids_contexto):
        """
        Transforma o DataFrame em um payload compatível e envia as notas direto pro Diário.
        """
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
            "dummy": ids_contexto.get('dummy', str(int(time.time() * 1000)))
        }

        # Converte as notas dos alunos para o formato que o SIEPE aceita (com vírgula)
        for _, row in df_view.iterrows():
            id_aluno = str(row.get('id_siepe', row.get('aluno_id')))
            
            def fmt(v): 
                try:
                    val = float(v)
                    return f"{val:.1f}".replace('.', ',') if val > 0 else ""
                except: return ""

            payload[f"nota_1_{id_aluno}"] = fmt(row.get('AT1', 0))
            payload[f"nota_2_{id_aluno}"] = fmt(row.get('AT2', 0))
            payload[f"nota_3_{id_aluno}"] = fmt(row.get('AT3', 0))
            payload[f"nota_4_{id_aluno}"] = fmt(row.get('AT4', 0))
            payload[f"nota_5_{id_aluno}"] = fmt(row.get('AT5', 0))
            payload[f"nota_7_{id_aluno}"] = fmt(row.get('N2', 0))

        # Endpoint correto para salvar as notas
        url_save = f"{self.base_url}/diarioclasse/EWServlet.ew"
        headers_save = {
            'Referer': f"{self.base_url}/diarioclasse/DiarioClasse.do",
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        try:
            response = self.session.post(url_save, data=payload, headers=headers_save, timeout=25)
            if response.status_code == 200:
                return True, "🚀 NOTAS SALVAS COM SUCESSO NO PORTAL DO GOVERNO!"
            return False, f"Falha ao salvar no servidor: {response.status_code}"
        except Exception as e:
            return False, f"Erro de rede ao salvar: {str(e)}"