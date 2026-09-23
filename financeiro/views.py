from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from financeiro.exceptions import ServicoDeCotacaoIndisponivel
from financeiro.models import Carteira
from financeiro.serializers import (
    DepositoEmDolarSerializer,
    DepositoRealizadoSerializer,
)
from financeiro.services import CotacaoIndisponivel


class DepositarEmDolarView(APIView):
    """
    POST /api/carteira/deposito-dolar/

    Converte um valor em dólar pela cotação atual e credita na carteira
    do usuário autenticado.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        entrada = DepositoEmDolarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        carteira = Carteira.objects.filter(usuario=request.user).first()
        if carteira is None:
            raise NotFound('Usuário não possui carteira')

        try:
            valor_creditado = carteira.deposito_em_dolar(
                entrada.validated_data['valor_em_dolar']
            )
        except CotacaoIndisponivel as erro:
            raise ServicoDeCotacaoIndisponivel(str(erro))

        saida = DepositoRealizadoSerializer(
            {'valor_creditado': valor_creditado, 'saldo_atual': carteira.saldo}
        )
        return Response(saida.data, status=status.HTTP_201_CREATED)
