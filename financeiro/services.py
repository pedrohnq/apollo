from decimal import Decimal, InvalidOperation

import requests

URL_COTACAO = 'https://economia.awesomeapi.com.br/json/last/USD-BRL'
TIMEOUT_SEGUNDOS = 5


class CotacaoIndisponivel(Exception):
    """Falha ao obter a cotação, seja por rede ou por formato inesperado."""


def buscar_cotacao_dolar():
    """Retorna a cotação de compra do dólar em reais, como Decimal."""
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
