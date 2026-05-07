import requests
import pandas as pd
import logging
import time
import re

class SiepeClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.siepe.educacao.pe.gov.br"
        
        # User-agent atualizado
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0',
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        })
        
        # Variáveis globais para guardar os IDs mágicos do portal
        self.ew_base = ""
        self.ew_id = ""

    def _extrair_tokens(self, texto_html):
        """
        O 'Olho' do robô: Caça os novos EWBase e EWId na resposta do servidor.
        """
        match_base = re.search(r'EWBase.*?[\'"]?(\d{8,12})[\'"]?', texto_html)
        match_id = re.search(r'EWId.*?[\'"]?(\d{8,12})[\'"]?', texto_html)
        
        if match_base: self.ew_base = match_base.group(1)
        if match_id: self.ew_id = match_id.group(1)
        
        return self.ew_base, self.ew_id

    def fazer_login(self, usuario, senha):
        """
        Realiza o login no SIEPE.
        """
        try:
            # Puxa os cookies iniciais
            self.session.get(f"{self.base_url}/GerenciadorAcessoWeb/login.do", timeout=10)
            
            url_login = f"{self.base_url}/GerenciadorAcessoWeb/login.do"
            payload_login = {
                "acao": "C",
                "cpf": usuario,
                "senha": senha
            }
            res_login = self.session.post(url_login, data=payload_login, timeout=10)
            
            if "Sair" in res_login.text or "Bem-vindo" in res_login.text or "Agamenon" in res_login.text:
                return True, "Login realizado com sucesso."
            return False, "Usuário ou senha incorretos."
        except Exception as e:
            return False, f"Erro de conexão: {str(e)}"

    def iniciar_robo_navegacao(self):
        """
        Faz a sequência COMPLETA de navegação invisível até a tela de notas.
        """
        url_ew = f"{self.base_url}/diarioclasse/EWServlet.ew"
        headers_post = {
            'request-type': '2',
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/diarioclasse/DiarioClasse.do'
        }

        # Atualiza a sessão para aceitar os POSTs de navegação
        self.session.headers.update(headers_post)

        # PASSO 1: Acessar o diário
        print("1. Abrindo Diário...")
        res = self.session.get(f'{self.base_url}/diarioclasse/DiarioClasse.do')
        self._extrair_tokens(res.text)

        # PASSO 2: Selecionar Escola (Agamenon: 606137)
        print("2. Selecionando Escola...")
        payload_escola = {
            "unidadeSelecionada": "606137", "EWBase": self.ew_base, "EWId": self.ew_id,
            "EWAction": "raiseEvent", "EWMethod": "selecionarUnidade", "dummy": str(int(time.time() * 1000))
        }
        res = self.session.post(url_ew, data=payload_escola)
        self._extrair_tokens(res.text)

        # PASSO 3: Pesquisar Turmas (2026)
        print("3. Pesquisando Turmas...")
        payload_pesquisa = {
            "txtAno": "2026", "EWBase": self.ew_base, "EWId": self.ew_id,
            "EWAction": "raiseEvent", "EWMethod": "btnPesquisar_onclick", "dummy": str(int(time.time() * 1000))
        }
        res = self.session.post(url_ew, data=payload_pesquisa)
        self._extrair_tokens(res.text)

        # PASSO 4: Clicar na Turma 2º A (ID interno: 260007983)
        print("4. Entrando na Turma 2º A...")
        payload_turma = {
            "hdnIdTurma": "260007983", "txtAno": "2026", "EWBase": self.ew_base, "EWId": self.ew_id,
            "EWAction": "raiseEvent", "EWMethod": "selecionarTurma", "dummy": str(int(time.time() * 1000))
        }
        res = self.session.post(url_ew, data=payload_turma)
        self._extrair_tokens(res.text)

        # PASSO 5: Abrir Aba de Notas (Aba 2)
        print("5. Abrindo Aba de Notas...")
        payload_aba = {
            "idAbaSelecionada": "2", "idAbaSelecionadaPedagogico": "2", "hdnMetodosCarregados": "selecionarAba",
            "EWBase": self.ew_base, "EWId": self.ew_id, "EWAction": "raiseEvent", "EWMethod": "selecionarAba", 
            "dummy": str(int(time.time() * 1000))
        }
        res = self.session.post(url_ew, data=payload_aba)
        self._extrair_tokens(res.text)

        print(f"Sucesso! Navegação concluída. Último EWId capturado: {self.ew_id}")
        return True

    def sincronizar_dataframe_ao_siepe_final(self, df_view, config_siepe):
        """
        Envia as notas usando a sessão que o robô acabou de criar.
        """
        payload = {
            "idAbaSelecionada": "2",
            "idAbaSelecionadaPedagogico": "2",
            "hdnMetodosCarregados": "selecionarAba",
            "ddlSerieNotaFalta": config_siepe.get('turma_id', '2483'),
            "ddlPeriodo": config_siepe.get('bimestre', '1'),
            "ddlDisciplina": config_siepe.get('disciplina_id', '1132'),
            "inputConceitos": "null",
            "EWBase": self.ew_base,
            "EWId": self.ew_id,       
            "EWHome": "",
            "EWAction": "raiseEvent",
            "EWMethod": "btnGravarNotasFaltasDisciplina_onclick",
            "dummy": str(int(time.time() * 1000))
        }

        # Varre os alunos
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

        url_ew = f"{self.base_url}/diarioclasse/EWServlet.ew"
        res = self.session.post(url_ew, data=payload)
        
        if res.status_code == 200:
            return True, "NOTAS SALVAS COM SUCESSO NO PORTAL DO GOVERNO!"
        return False, f"Falha ao salvar: {res.status_code}"