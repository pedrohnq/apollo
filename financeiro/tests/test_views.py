# """
# Testes de VIEW — o contrato HTTP.

# A view não é testada chamando a função Python diretamente, e sim através do
# `self.client`, que percorre middlewares, roteamento de URL e serialização.
# É isso que torna o teste capaz de pegar uma rota mal registrada ou um
# middleware que interfere na resposta.

# O que se verifica aqui é o CONTRATO: status code e corpo da resposta. A
# aritmética da conversão já foi coberta em test_models.py — repeti-la aqui
# seria duplicação que dobra o custo de manutenção sem aumentar a cobertura real.
# """

# import json
# from decimal import Decimal
# from unittest.mock import patch

# from django.contrib.auth.models import User
# from django.test import TestCase
# from django.urls import reverse
# from model_bakery import baker

# from financeiro.models import Carteira
# from financeiro.services import CotacaoIndisponivel


# class DepositarEmDolarViewTest(TestCase):

#     def setUp(self):
#         self.url = reverse('financeiro:deposito-dolar')
#         self.usuario = baker.make(User)
#         self.carteira = baker.make(
#             Carteira, usuario=self.usuario, saldo=Decimal('0.00')
#         )
#         self.client.force_login(self.usuario)

#     def post(self, corpo):
#         return self.client.post(
#             self.url, data=json.dumps(corpo), content_type='application/json'
#         )

#     @patch('financeiro.models.buscar_cotacao_dolar')
#     def test_deposito_valido_retorna_201_com_saldo(self, cotacao_mock):
#         cotacao_mock.return_value = Decimal('5.00')

#         resposta = self.post({'valor_em_dolar': '10.00'})

#         self.assertEqual(resposta.status_code, 201)
#         self.assertEqual(
#             resposta.json(),
#             {'valor_creditado': '50.00', 'saldo_atual': '50.00'},
#         )

#     @patch('financeiro.models.buscar_cotacao_dolar')
#     def test_deposito_valido_persiste_no_banco(self, cotacao_mock):
#         cotacao_mock.return_value = Decimal('5.00')

#         self.post({'valor_em_dolar': '10.00'})

#         self.carteira.refresh_from_db()
#         self.assertEqual(self.carteira.saldo, Decimal('50.00'))

#     def test_usuario_anonimo_recebe_401(self):
#         self.client.logout()

#         resposta = self.post({'valor_em_dolar': '10.00'})

#         self.assertEqual(resposta.status_code, 401)

#     @patch('financeiro.models.buscar_cotacao_dolar')
#     def test_usuario_anonimo_nao_chama_a_api(self, cotacao_mock):
#         self.client.logout()

#         self.post({'valor_em_dolar': '10.00'})

#         cotacao_mock.assert_not_called()

#     def test_corpo_nao_json_retorna_400(self):
#         resposta = self.client.post(
#             self.url, data='isto nao e json', content_type='application/json'
#         )

#         self.assertEqual(resposta.status_code, 400)

#     def test_campo_ausente_retorna_400(self):
#         resposta = self.post({'outro_campo': '10.00'})

#         self.assertEqual(resposta.status_code, 400)
#         self.assertIn('valor_em_dolar', resposta.json()['erro'])

#     @patch('financeiro.models.buscar_cotacao_dolar')
#     def test_valor_negativo_retorna_400(self, cotacao_mock):
#         cotacao_mock.return_value = Decimal('5.00')

#         resposta = self.post({'valor_em_dolar': '-10.00'})

#         self.assertEqual(resposta.status_code, 400)

#     def test_usuario_sem_carteira_retorna_404(self):
#         outro = baker.make(User)
#         self.client.force_login(outro)

#         resposta = self.post({'valor_em_dolar': '10.00'})

#         self.assertEqual(resposta.status_code, 404)

#     @patch('financeiro.models.buscar_cotacao_dolar')
#     def test_api_de_cotacao_fora_do_ar_retorna_503(self, cotacao_mock):
#         """
#         503 e não 500: a falha é de dependência externa, é temporária, e o
#         cliente pode tentar de novo. Um 500 sinalizaria bug nosso.
#         """
#         cotacao_mock.side_effect = CotacaoIndisponivel('API fora do ar')

#         resposta = self.post({'valor_em_dolar': '10.00'})

#         self.assertEqual(resposta.status_code, 503)

#     def test_metodo_get_nao_permitido(self):
#         resposta = self.client.get(self.url)

#         self.assertEqual(resposta.status_code, 405)

#     def test_metodo_invalido_para_anonimo_retorna_401_e_nao_405(self):
#         """
#         Documenta a ordem de checagem introduzida pela class-based view.

#         A autenticação mora no `dispatch`, que roda ANTES do roteamento por
#         verbo HTTP. Logo, um GET anônimo recebe 401, não 405. Além de ser a
#         ordem correta, evita revelar a clientes não autenticados quais métodos
#         o endpoint aceita.
#         """
#         self.client.logout()

#         resposta = self.client.get(self.url)

#         self.assertEqual(resposta.status_code, 401)
