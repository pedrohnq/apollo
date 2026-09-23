"""
Teste END-TO-END — o fluxo completo do usuário.

A diferença essencial em relação aos testes anteriores está no ALVO DO MOCK.

    Testes unitários:  patch('financeiro.models.buscar_cotacao_dolar')
                       → substitui código NOSSO, isola a unidade

    Teste end-to-end:  patch('financeiro.services.requests.get')
                       → substitui apenas a FRONTEIRA externa real

Aqui `buscar_cotacao_dolar` roda de verdade, incluindo o parsing do JSON e a
conversão para Decimal. Só a chamada de rede é interceptada. O teste percorre
view → model → service → parsing → banco, exercitando a integração entre as
camadas — que é exatamente o que testes unitários, por construção, não cobrem.

Mockar a rede mesmo no E2E não é trapaça: um teste que dependesse da API real
falharia sem internet, seria lento, e quebraria quando a cotação mudasse.
Testes precisam ser determinísticos.
"""

import json
from decimal import Decimal
from unittest.mock import patch, Mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from financeiro.models import Carteira


def resposta_da_api(cotacao):
    resposta = Mock()
    resposta.json.return_value = {'USDBRL': {'bid': cotacao}}
    resposta.raise_for_status.return_value = None
    return resposta


class FluxoCompletoDepositoEmDolarTest(TestCase):
    """
    Cenário: um usuário se cadastra, deposita dólares duas vezes com cotações
    diferentes, saca parte do valor e confere o saldo final.
    """

    @patch('financeiro.services.requests.get')
    def test_jornada_completa_do_usuario(self, get_mock):
        # --- 1. Usuário e carteira zerada ---
        usuario = User.objects.create_user(username='pedro', password='senha-segura')
        carteira = Carteira.objects.create(usuario=usuario, saldo=Decimal('0.00'))

        # --- 2. Login pela camada HTTP real ---
        login_ok = self.client.login(username='pedro', password='senha-segura')
        self.assertTrue(login_ok)

        url = reverse('financeiro:deposito-dolar')

        # --- 3. Primeiro depósito: US$ 100 a 5.20 = R$ 520.00 ---
        get_mock.return_value = resposta_da_api('5.20')
        resposta = self.client.post(
            url,
            data=json.dumps({'valor_em_dolar': '100.00'}),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.json()['valor_creditado'], '520.00')

        # --- 4. Segundo depósito, cotação diferente: US$ 50 a 5.50 = R$ 275.00 ---
        get_mock.return_value = resposta_da_api('5.50')
        resposta = self.client.post(
            url,
            data=json.dumps({'valor_em_dolar': '50.00'}),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.json()['saldo_atual'], '795.00')

        # --- 5. Saque direto no model ---
        carteira.refresh_from_db()
        carteira.saque(Decimal('295.00'))

        # --- 6. Saldo final conferido no banco ---
        carteira.refresh_from_db()
        self.assertEqual(carteira.saldo, Decimal('500.00'))

        # --- 7. A API externa foi chamada exatamente duas vezes ---
        self.assertEqual(get_mock.call_count, 2)

    @patch('financeiro.services.requests.get')
    def test_indisponibilidade_da_api_nao_corrompe_o_saldo(self, get_mock):
        """
        O caminho triste completo: a API externa cai no meio da jornada.

        O que se verifica é que a falha atravessa todas as camadas
        corretamente — virando 503 na borda HTTP — sem deixar o saldo
        num estado inconsistente.
        """
        import requests

        usuario = User.objects.create_user(username='ana', password='senha-segura')
        carteira = Carteira.objects.create(usuario=usuario, saldo=Decimal('300.00'))
        self.client.login(username='ana', password='senha-segura')

        get_mock.side_effect = requests.ConnectionError('rede fora do ar')

        resposta = self.client.post(
            reverse('financeiro:deposito-dolar'),
            data=json.dumps({'valor_em_dolar': '100.00'}),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 503)

        carteira.refresh_from_db()
        self.assertEqual(carteira.saldo, Decimal('300.00'))
