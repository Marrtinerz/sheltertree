from django.contrib import admin
from .models import Country, State 
# Register your models here.

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
        list_display = ('name', 'code')

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
        list_display = ('name', 'country')