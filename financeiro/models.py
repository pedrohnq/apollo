from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import User
from django.db import models

from financeiro.services import buscar_cotacao_dolar

CENTAVOS = Decimal('0.01')


def para_decimal(valor):
    """
    Converte valor para Decimal de forma segura.

    O `str()` no meio não é decorativo: `Decimal(5.35)` a partir de um float
    produz 5.3499999999999996447286321199499070644378662109375, porque floats
    binários não representam decimais exatamente. `Decimal('5.35')` é exato.
    Em código financeiro essa diferença vira centavo errado no extrato.
    """
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


class Carteira(models.Model):
    """
    Model responsável por salvar os dados da carteira de um usuário
    """
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )

    def __str__(self):
        return f'Carteira de {self.usuario.username}: R$ {self.saldo}'

    def deposito(self, valor):
        valor = para_decimal(valor)
        if valor <= 0:
            raise ValueError("Digite um valor positivo para realizar o depósito")
        self.saldo += valor
        self.save()

    def saque(self, valor):
        valor = para_decimal(valor)
        if valor <= 0:
            raise ValueError("Digite um valor positivo para realizar o saque")

        if valor > self.saldo:
            raise ValueError("O valor é maior que o saldo disponível")

        self.saldo -= valor
        self.save()

    def deposito_em_dolar(self, valor_em_dolar):
        """
        Converte um valor em dólar para reais pela cotação atual e deposita.

        Retorna o valor em reais efetivamente creditado.

        A validação acontece ANTES da chamada à API de propósito: não faz
        sentido gastar uma requisição de rede para descobrir que o valor
        era negativo. Isso também torna o teste do caso inválido independente
        de qualquer mock.
        """
        valor_em_dolar = para_decimal(valor_em_dolar)
        if valor_em_dolar <= 0:
            raise ValueError("Digite um valor positivo para realizar o depósito")

        cotacao = buscar_cotacao_dolar()
        valor_em_reais = (valor_em_dolar * cotacao).quantize(
            CENTAVOS, rounding=ROUND_HALF_UP
        )

        self.deposito(valor_em_reais)
        return valor_em_reais
