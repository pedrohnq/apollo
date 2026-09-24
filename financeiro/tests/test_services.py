"""
Testes de FUNÇÃO — a camada mais baixa.

Aqui não há banco de dados nem HTTP real. Usamos `SimpleTestCase` em vez de
`TestCase` justamente para deixar isso explícito: o Django recusa acesso ao
banco nesta classe, então se alguém acidentalmente introduzir uma query aqui,
o teste falha em vez de ficar lento silenciosamente.

Este é o arquivo onde o conceito de MOCK aparece de forma mais pura.
"""

from decimal import Decimal
from unittest.mock import patch, Mock

import requests
from django.test import SimpleTestCase

from financeiro.services import (
    CotacaoIndisponivel,
    URL_COTACAO,
    TIMEOUT_SEGUNDOS,
    buscar_cotacao_dolar,
)


def resposta_falsa(json_retornado, status=200):
    """
    Constrói um dublê de `requests.Response`.

    Note que NÃO usamos a classe real do requests. Um Mock só precisa oferecer
    a mesma superfície que o código sob teste consome — aqui, `.json()` e
    `.raise_for_status()`. Isso é o princípio do "duck typing" aplicado a testes.
    """
    resposta = Mock()
    resposta.status_code = status
    resposta.json.return_value = json_retornado
    resposta.raise_for_status.return_value = None
    return resposta


class BuscarCotacaoDolarTest(SimpleTestCase):

    @patch('financeiro.services.requests.get')
    def test_retorna_cotacao_como_decimal(self, get_mock):
        """
        O caminho feliz.

        Repare no alvo do patch: 'financeiro.services.requests.get', e não
        'requests.get'. A regra é "onde é USADO, não onde é DEFINIDO". O patch
        substitui o atributo no namespace de quem chama; apontar para a
        biblioteca original não teria efeito sobre este módulo.
        """
        get_mock.return_value = resposta_falsa({'USDBRL': {'bid': '5.35'}})

        cotacao = buscar_cotacao_dolar()

        self.assertEqual(cotacao, Decimal('5.35'))
        self.assertIsInstance(cotacao, Decimal)

    @patch('financeiro.services.requests.get')
    def test_chama_api_com_url_e_timeout_corretos(self, get_mock):
        """
        Verificar COMO o mock foi chamado, não só o que ele retornou.

        O timeout é o caso clássico de algo que só um teste assim protege:
        sem ele, uma API lenta trava um worker do gunicorn indefinidamente,
        e nenhum teste de valor de retorno detectaria a ausência.
        """
        get_mock.return_value = resposta_falsa({'USDBRL': {'bid': '5.35'}})

        buscar_cotacao_dolar()

        get_mock.assert_called_once_with(URL_COTACAO, timeout=TIMEOUT_SEGUNDOS)

    @patch('financeiro.services.requests.get')
    def test_erro_de_rede_vira_cotacao_indisponivel(self, get_mock):
        """
        `side_effect` faz o mock LEVANTAR a exceção em vez de retornar valor.

        Simular uma rede fora do ar é impossível num teste real — e é
        exatamente por isso que o mock existe.
        """
        get_mock.side_effect = requests.ConnectionError('rede fora do ar')

        with self.assertRaises(CotacaoIndisponivel):
            buscar_cotacao_dolar()

    @patch('financeiro.services.requests.get')
    def test_status_de_erro_vira_cotacao_indisponivel(self, get_mock):
        resposta = resposta_falsa({}, status=500)
        resposta.raise_for_status.side_effect = requests.HTTPError('500')
        get_mock.return_value = resposta

        with self.assertRaises(CotacaoIndisponivel):
            buscar_cotacao_dolar()

    @patch('financeiro.services.requests.get')
    def test_json_sem_a_chave_esperada_vira_cotacao_indisponivel(self, get_mock):
        """
        Contratos de API mudam sem aviso. Este teste garante que uma mudança
        no formato vire um erro nosso, tratável, e não um KeyError cru
        vazando como erro 500 para o usuário.
        """
        get_mock.return_value = resposta_falsa({'formato': 'inesperado'})

        with self.assertRaises(CotacaoIndisponivel):
            buscar_cotacao_dolar()

    @patch('financeiro.services.requests.get')
    def test_valor_nao_numerico_vira_cotacao_indisponivel(self, get_mock):
        get_mock.return_value = resposta_falsa({'USDBRL': {'bid': 'abc'}})

        with self.assertRaises(CotacaoIndisponivel):
            buscar_cotacao_dolar()