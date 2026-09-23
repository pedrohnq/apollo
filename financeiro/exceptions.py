from rest_framework import status
from rest_framework.exceptions import APIException


class ServicoDeCotacaoIndisponivel(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Serviço de cotação indisponível. Tente novamente em instantes.'
    default_code = 'cotacao_indisponivel'
