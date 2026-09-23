from decimal import Decimal

from rest_framework import serializers


class DepositoEmDolarSerializer(serializers.Serializer):
    valor_em_dolar = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
    )


class DepositoRealizadoSerializer(serializers.Serializer):
    valor_creditado = serializers.DecimalField(max_digits=12, decimal_places=2)
    saldo_atual = serializers.DecimalField(max_digits=12, decimal_places=2)
