import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from financeiro.models import Carteira
from financeiro.services import CotacaoIndisponivel


# Em class-based views, decorators de função não podem ser aplicados direto na
# classe: `method_decorator` faz a ponte. O `name='dispatch'` aplica o decorator
# ao método que recebe TODA requisição, antes do roteamento por verbo HTTP.
@method_decorator(csrf_exempt, name='dispatch')
class DepositarEmDolarView(View):
    """
    POST /api/carteira/deposito-dolar/
    Corpo: {"valor_em_dolar": "10.00"}

    Converte o valor pela cotação atual e credita na carteira do usuário logado.

    O csrf_exempt está aqui porque é uma API consumida por cliente externo,
    não por formulário HTML. Numa API real isso seria substituído por
    autenticação por token, que dispensa CSRF por não usar cookie de sessão.

    Note que não há mais `require_POST`: a View só roteia para os métodos que
    a classe define. Como só existe `post`, qualquer outro verbo cai no
    `http_method_not_allowed` do Django e vira 405 automaticamente.
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Autenticação antes do roteamento por verbo.

        Fazer isso aqui, e não dentro de `post`, tem uma consequência
        deliberada: qualquer requisição anônima é barrada antes de o Django
        sequer decidir qual método chamar. É o lugar natural para uma regra
        que vale para a view inteira — e, quando surgirem `get` ou `delete`,
        não há risco de esquecer a checagem em algum deles.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'erro': 'Autenticação necessária'}, status=401)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            corpo = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'erro': 'JSON inválido'}, status=400)

        if 'valor_em_dolar' not in corpo:
            return JsonResponse(
                {'erro': 'Campo "valor_em_dolar" é obrigatório'}, status=400
            )

        try:
            carteira = Carteira.objects.get(usuario=request.user)
        except Carteira.DoesNotExist:
            return JsonResponse({'erro': 'Usuário não possui carteira'}, status=404)

        try:
            valor_creditado = carteira.deposito_em_dolar(corpo['valor_em_dolar'])
        except ValueError as erro:
            # Cobre tanto valor negativo quanto valor não numérico vindo do JSON.
            return JsonResponse({'erro': str(erro)}, status=400)
        except CotacaoIndisponivel as erro:
            # 503: a falha é de um serviço do qual dependemos, não do cliente.
            return JsonResponse({'erro': str(erro)}, status=503)

        return JsonResponse(
            {
                'valor_creditado': str(valor_creditado),
                'saldo_atual': str(carteira.saldo),
            },
            status=201,
        )
