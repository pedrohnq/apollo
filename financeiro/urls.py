from django.urls import path

from financeiro import views

app_name = 'financeiro'

urlpatterns = [
    path(
        'carteira/deposito-dolar/',
        views.DepositarEmDolarView.as_view(),
        name='deposito-dolar',
    ),
]
