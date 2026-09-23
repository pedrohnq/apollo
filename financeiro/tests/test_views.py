"""
Testes de VIEW — o contrato HTTP.

A view é exercitada pelo client, não chamando o método diretamente: assim o
teste percorre roteamento, autenticação, parsing e serialização.

Verifica-se aqui o contrato (status e corpo). A aritmética da conversão já
está coberta em test_models.py.
"""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APITestCase

from financeiro.models import Carteira
from financeiro.services import CotacaoIndisponivel


class DepositarEmDolarViewTest(APITestCase):

    def setUp(self):
        self.url = reverse('financeiro:deposito-dolar')
        self.usuario = baker.make(User)
        self.carteira = baker.make(
            Carteira, usuario=self.usuario, saldo=Decimal('0.00')
        )
        self.client.force_authenticate(user=self.usuario)

    def post(self, corpo):
        return self.client.post(self.url, data=corpo, format='json')

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_deposito_valido_retorna_201_com_saldo(self, cotacao_mock):
        cotacao_mock.return_value = Decimal('5.00')

        resposta = self.post({'valor_em_dolar': '10.00'})

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            resposta.data,
            {'valor_creditado': '50.00', 'saldo_atual': '50.00'},
        )

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_deposito_valido_persiste_no_banco(self, cotacao_mock):
        cotacao_mock.return_value = Decimal('5.00')

        self.post({'valor_em_dolar': '10.00'})

        self.carteira.refresh_from_db()
        self.assertEqual(self.carteira.saldo, Decimal('50.00'))

    def test_usuario_anonimo_e_barrado(self):
        """
        403 e não 401: com SessionAuthentication não há cabeçalho de desafio
        a devolver, então o DRF usa 403. Com TokenAuthentication seria 401.
        """
        self.client.force_authenticate(user=None)

        resposta = self.post({'valor_em_dolar': '10.00'})

        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_usuario_anonimo_nao_chama_a_api(self, cotacao_mock):
        self.client.force_authenticate(user=None)

        self.post({'valor_em_dolar': '10.00'})

        cotacao_mock.assert_not_called()

    def test_corpo_nao_json_retorna_400(self):
        resposta = self.client.post(
            self.url, data='isto nao e json', content_type='application/json'
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_corpo_json_que_nao_e_objeto_retorna_400(self):
        resposta = self.client.post(self.url, data=[1, 2], format='json')

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_campo_ausente_retorna_400(self):
        resposta = self.post({'outro_campo': '10.00'})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('valor_em_dolar', resposta.data)

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_valor_negativo_retorna_400_sem_chamar_a_api(self, cotacao_mock):
        resposta = self.post({'valor_em_dolar': '-10.00'})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('valor_em_dolar', resposta.data)
        cotacao_mock.assert_not_called()

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_valor_zero_retorna_400(self, cotacao_mock):
        resposta = self.post({'valor_em_dolar': '0'})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        cotacao_mock.assert_not_called()

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_valor_nao_numerico_retorna_400(self, cotacao_mock):
        resposta = self.post({'valor_em_dolar': 'dez dolares'})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        cotacao_mock.assert_not_called()

    def test_usuario_sem_carteira_retorna_404(self):
        self.client.force_authenticate(user=baker.make(User))

        resposta = self.post({'valor_em_dolar': '10.00'})

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_api_de_cotacao_fora_do_ar_retorna_503(self, cotacao_mock):
        """503 e não 500: a falha é de dependência externa, e é temporária."""
        cotacao_mock.side_effect = CotacaoIndisponivel('API fora do ar')

        resposta = self.post({'valor_em_dolar': '10.00'})

        self.assertEqual(
            resposta.status_code, status.HTTP_503_SERVICE_UNAVAILABLE
        )

    def test_metodo_get_nao_permitido(self):
        resposta = self.client.get(self.url)

        self.assertEqual(
            resposta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_metodo_invalido_para_anonimo_e_barrado_antes_do_405(self):
        """
        O DRF checa permissão em `initial()`, antes de resolver o handler do
        verbo. Um GET anônimo recebe 403, e não 405, o que evita revelar quais
        métodos o endpoint aceita.
        """
        self.client.force_authenticate(user=None)

        resposta = self.client.get(self.url)

        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
