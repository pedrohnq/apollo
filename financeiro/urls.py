from django.urls import path

from financeiro import views

app_name = 'financeiro'

urlpatterns = [
    path(
        'carteira/deposito-dolar/',
        # `as_view()` transforma a classe na função que o Django espera:
        # cada requisição instancia a view de novo, o que garante que nenhum
        # estado vaze entre requisições concorrentes.
        views.DepositarEmDolarView.as_view(),
        name='deposito-dolar',
    ),
]
