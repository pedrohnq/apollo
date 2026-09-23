"""
Testes de MODEL — regras de negócio que tocam o banco.

Aqui entra o model_bakery. O ganho dele fica claro ao comparar:

    # sem baker
    usuario = User.objects.create_user(
        username='teste', email='t@t.com', password='123'
    )
    carteira = Carteira.objects.create(usuario=usuario, saldo=Decimal('100.00'))

    # com baker
    carteira = baker.make(Carteira, saldo=Decimal('100.00'))

O baker preenche todos os campos obrigatórios com valores válidos e cria as
relações (aqui, o User) automaticamente. Você declara APENAS o que importa
para o teste em questão — o resto vira ruído que esconde a intenção.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from model_bakery import baker

from financeiro.models import Carteira, para_decimal
from financeiro.services import CotacaoIndisponivel


class ParaDecimalTest(TestCase):
    """Função pura: nenhum mock necessário, nenhum banco envolvido."""

    def test_converte_float_sem_erro_de_ponto_flutuante(self):
        # O ponto central: Decimal(5.35) daria 5.34999999999999964...
        self.assertEqual(para_decimal(5.35), Decimal('5.35'))

    def test_converte_int(self):
        self.assertEqual(para_decimal(10), Decimal('10'))

    def test_mantem_decimal_inalterado(self):
        original = Decimal('1.23')
        self.assertIs(para_decimal(original), original)


class CarteiraStrTest(TestCase):

    def test_representacao_textual(self):
        """
        `__str__` é o que aparece no admin e nos logs. Barato de testar e,
        quando quebra, quebra numa tela que ninguém cobre com teste.
        """
        carteira = baker.make(
            Carteira, usuario__username='pedro', saldo=Decimal('100.00')
        )

        self.assertEqual(str(carteira), 'Carteira de pedro: R$ 100.00')


class DepositoTest(TestCase):

    def setUp(self):
        self.carteira = baker.make(Carteira, saldo=Decimal('100.00'))

    def test_soma_ao_saldo(self):
        self.carteira.deposito(Decimal('50.00'))

        self.assertEqual(self.carteira.saldo, Decimal('150.00'))

    def test_persiste_no_banco(self):
        """
        `deposito` chama `save()`. Sem o refresh_from_db, estaríamos testando
        apenas o atributo em memória — e um `save()` esquecido passaria batido.
        """
        self.carteira.deposito(Decimal('50.00'))
        self.carteira.refresh_from_db()

        self.assertEqual(self.carteira.saldo, Decimal('150.00'))

    def test_valor_zero_levanta_erro(self):
        with self.assertRaises(ValueError):
            self.carteira.deposito(Decimal('0'))

    def test_valor_negativo_levanta_erro(self):
        with self.assertRaises(ValueError):
            self.carteira.deposito(Decimal('-10.00'))

    def test_valor_invalido_nao_altera_saldo(self):
        """
        Testar o efeito colateral, não só a exceção: garante que a validação
        acontece ANTES da mutação do estado.
        """
        with self.assertRaises(ValueError):
            self.carteira.deposito(Decimal('-10.00'))

        self.carteira.refresh_from_db()
        self.assertEqual(self.carteira.saldo, Decimal('100.00'))


class SaqueTest(TestCase):

    def setUp(self):
        self.carteira = baker.make(Carteira, saldo=Decimal('100.00'))

    def test_subtrai_do_saldo(self):
        self.carteira.saque(Decimal('30.00'))

        self.assertEqual(self.carteira.saldo, Decimal('70.00'))

    def test_saque_do_saldo_exato_e_permitido(self):
        """Teste de borda: o limite é `>`, não `>=`."""
        self.carteira.saque(Decimal('100.00'))

        self.assertEqual(self.carteira.saldo, Decimal('0.00'))

    def test_valor_maior_que_saldo_levanta_erro(self):
        with self.assertRaises(ValueError):
            self.carteira.saque(Decimal('100.01'))

    def test_valor_negativo_levanta_erro(self):
        with self.assertRaises(ValueError):
            self.carteira.saque(Decimal('-10.00'))


class DepositoEmDolarTest(TestCase):
    """
    Note o alvo do patch: 'financeiro.models.buscar_cotacao_dolar'.

    O models.py importou a função com `from ... import`, criando uma referência
    própria no namespace dele. Patchear 'financeiro.services.buscar_cotacao_dolar'
    NÃO teria efeito, porque models.py já guardou a referência original.
    É o erro de mock mais comum que existe.
    """

    def setUp(self):
        self.carteira = baker.make(Carteira, saldo=Decimal('0.00'))

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_converte_pela_cotacao_e_credita(self, cotacao_mock):
        cotacao_mock.return_value = Decimal('5.00')

        creditado = self.carteira.deposito_em_dolar(Decimal('10.00'))

        self.assertEqual(creditado, Decimal('50.00'))
        self.assertEqual(self.carteira.saldo, Decimal('50.00'))

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_arredonda_para_centavos(self, cotacao_mock):
        """
        10.00 * 5.37 = 53.70 exato; usamos um valor que gera dízima.
        3.33 * 5.37 = 17.8821 → deve virar 17.88 (ROUND_HALF_UP).
        """
        cotacao_mock.return_value = Decimal('5.37')

        creditado = self.carteira.deposito_em_dolar(Decimal('3.33'))

        self.assertEqual(creditado, Decimal('17.88'))
        self.assertEqual(creditado.as_tuple().exponent, -2)

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_arredonda_meio_centavo_para_cima(self, cotacao_mock):
        """
        1.00 * 5.125 = 5.125 → ROUND_HALF_UP leva a 5.13.
        O padrão do Python é ROUND_HALF_EVEN, que daria 5.12. A escolha é
        explícita no model e este teste a trava.
        """
        cotacao_mock.return_value = Decimal('5.125')

        creditado = self.carteira.deposito_em_dolar(Decimal('1.00'))

        self.assertEqual(creditado, Decimal('5.13'))

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_acumula_sobre_saldo_existente(self, cotacao_mock):
        cotacao_mock.return_value = Decimal('5.00')
        self.carteira.saldo = Decimal('100.00')
        self.carteira.save()

        self.carteira.deposito_em_dolar(Decimal('10.00'))

        self.assertEqual(self.carteira.saldo, Decimal('150.00'))

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_valor_negativo_nao_chama_a_api(self, cotacao_mock):
        """
        Asserção sobre a AUSÊNCIA de chamada.

        Isso verifica uma decisão de design: validar antes de gastar rede.
        Um teste que só checasse o ValueError passaria mesmo se a ordem
        estivesse invertida.
        """
        with self.assertRaises(ValueError):
            self.carteira.deposito_em_dolar(Decimal('-1.00'))

        cotacao_mock.assert_not_called()

    @patch('financeiro.models.buscar_cotacao_dolar')
    def test_falha_na_cotacao_propaga_e_nao_altera_saldo(self, cotacao_mock):
        cotacao_mock.side_effect = CotacaoIndisponivel('API fora do ar')

        with self.assertRaises(CotacaoIndisponivel):
            self.carteira.deposito_em_dolar(Decimal('10.00'))

        self.carteira.refresh_from_db()
        self.assertEqual(self.carteira.saldo, Decimal('0.00'))
