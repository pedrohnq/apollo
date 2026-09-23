from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Carteira(models.Model):
    """
    Model responsável por salvar os dados da carteira de um usuário
    """
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    saldo = models.PositiveBigIntegerField()

    def deposito(self, valor):
        if valor <= 0:
            raise ValueError("Digite um valor positivo para realizar o depósito")
        self.saldo += valor
        self.save()

    def saque(self, valor):
        if valor <= 0:
            raise ValueError("Digite um valor positivo para realizar o saque")

        if valor > self.saldo:
            raise ValueError("O valor é maior que o saldo disponível")

        self.saldo -= valor
        self.save()
