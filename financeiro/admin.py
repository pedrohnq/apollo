from django.contrib import admin

from financeiro.models import Carteira


@admin.register(Carteira)
class CarteiraAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'saldo')
    search_fields = ('usuario__username',)
