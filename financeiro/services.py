"""
Integrações com serviços externos.

Este módulo existe separado dos models por um motivo que fica evidente nos testes:
tudo que fala com o mundo externo (rede, disco, relógio) é o que precisa ser
substituído por mock. Isolar essas chamadas num único lugar dá um alvo óbvio
para o `patch` e evita espalhar `requests.get` pelo código de negócio.
"""

from decimal import Decimal, InvalidOperation

import requests

URL_COTACAO = 'https://economia.awesomeapi.com.br/json/last/USD-BRL'
TIMEOUT_SEGUNDOS = 5


class CotacaoIndisponivel(Exception):
    """
    Erro de domínio para qualquer falha na obtenção da cotação.

    Traduzir exceções da biblioteca (requests) para uma exceção nossa é
    deliberado: o resto da aplicação não precisa saber que usamos `requests`,
    e se um dia trocarmos de cliente HTTP nada mais quebra.
    """


def buscar_cotacao_dolar():
    """
    Retorna a cotação de compra do dólar em reais, como Decimal.

    Levanta CotacaoIndisponivel se a API não responder ou responder
    em formato inesperado.
    """
    try:
        resposta = requests.get(URL_COTACAO, timeout=TIMEOUT_SEGUNDOS)
        resposta.raise_for_status()
    except requests.RequestException as erro:
        raise CotacaoIndisponivel(f'Falha ao consultar a cotação: {erro}') from erro

    try:
        dados = resposta.json()
        return Decimal(dados['USDBRL']['bid'])
    except (ValueError, KeyError, TypeError, InvalidOperation) as erro:
        raise CotacaoIndisponivel(
            f'Resposta da API de cotação em formato inesperado: {erro}'
        ) from erro
