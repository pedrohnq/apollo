from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import User
from django.db import models

from financeiro.services import buscar_cotacao_dolar

CENTAVOS = Decimal('0.01')


def para_decimal(valor):
    if isinstance(valor, Decimal):
        return valor
    # O str() é necessário: Decimal(5.35) a partir de um float dá 5.34999...
    return Decimal(str(valor))


class Carteira(models.Model):
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
        """Converte pela cotação atual, credita e retorna o valor em reais."""
        valor_em_dolar = para_decimal(valor_em_dolar)
        if valor_em_dolar <= 0:
            raise ValueError("Digite um valor positivo para realizar o depósito")

        cotacao = buscar_cotacao_dolar()
        valor_em_reais = (valor_em_dolar * cotacao).quantize(
            CENTAVOS, rounding=ROUND_HALF_UP
        )

        self.deposito(valor_em_reais)
        return valor_em_reais
