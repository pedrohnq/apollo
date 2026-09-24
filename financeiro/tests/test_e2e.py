"""
Teste END-TO-END — o fluxo completo do usuário.

A diferença em relação aos testes unitários está no alvo do mock:

    unitário:  patch('financeiro.models.buscar_cotacao_dolar')
               substitui código nosso, isola a unidade

    e2e:       patch('financeiro.services.requests.get')
               substitui só a fronteira externa real

Aqui `buscar_cotacao_dolar` roda de verdade, incluindo parsing e conversão.
O teste percorre view → serializer → model → service → banco, exercitando a
integração entre camadas.
"""

from decimal import Decimal
from unittest.mock import patch, Mock

import requests
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from financeiro.models import Carteira


def resposta_da_api(cotacao):
    resposta = Mock()
    resposta.json.return_value = {'USDBRL': {'bid': cotacao}}
    resposta.raise_for_status.return_value = None
    return resposta


class FluxoCompletoDepositoEmDolarTest(APITestCase):

    @patch('financeiro.services.requests.get')
    def test_jornada_completa_do_usuario(self, get_mock):
        usuario = User.objects.create_user(username='pedro', password='senha-segura')
        carteira = Carteira.objects.create(usuario=usuario, saldo=Decimal('0.00'))

        self.assertTrue(
            self.client.login(username='pedro', password='senha-segura')
        )

        url = reverse('financeiro:deposito-dolar')

        # US$ 100 a 5.20 = R$ 520.00
        get_mock.return_value = resposta_da_api('5.20')
        resposta = self.client.post(url, {'valor_em_dolar': '100.00'}, format='json')

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data['valor_creditado'], '520.00')

        # US$ 50 a 5.50 = R$ 275.00, acumulando sobre o anterior
        get_mock.return_value = resposta_da_api('5.50')
        resposta = self.client.post(url, {'valor_em_dolar': '50.00'}, format='json')

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data['saldo_atual'], '795.00')

        carteira.refresh_from_db()
        carteira.saque(Decimal('295.00'))

        carteira.refresh_from_db()
        self.assertEqual(carteira.saldo, Decimal('500.00'))
        self.assertEqual(get_mock.call_count, 2)

    @patch('financeiro.services.requests.get')
    def test_indisponibilidade_da_api_nao_corrompe_o_saldo(self, get_mock):
        usuario = User.objects.create_user(username='ana', password='senha-segura')
        carteira = Carteira.objects.create(usuario=usuario, saldo=Decimal('300.00'))
        self.client.login(username='ana', password='senha-segura')

        get_mock.side_effect = requests.ConnectionError('rede fora do ar')

        resposta = self.client.post(
            reverse('financeiro:deposito-dolar'),
            {'valor_em_dolar': '100.00'},
            format='json',
        )

        self.assertEqual(
            resposta.status_code, status.HTTP_503_SERVICE_UNAVAILABLE
        )

        carteira.refresh_from_db()
        self.assertEqual(carteira.saldo, Decimal('300.00'))