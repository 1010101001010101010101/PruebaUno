from django.contrib import admin

# Register your models here.
from dashboard.models import Category, Zone, Device, Measurement, Alert, Organization

"""
¿Qué hace esto?
Permite que esos modelos aparezcan en el panel de administración de Django.
Ahora se pueden crear, editar y eliminar registros de esas tablas desde la interfaz web sin programar nada adicional.

Resultado en el Admin:
Se muestran menús con "Categorías", "Zonas", "Dispositivos", etc.
Al ingresar, el admin genera automáticamente formularios para manejar los datos.
"""

# Configuración personalizada para cada modelo
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name',)

class ZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name',)

class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'zone', 'max_consumption', 'status')
    list_filter = ('category', 'zone', 'status')
    search_fields = ('name',)

class MeasurementAdmin(admin.ModelAdmin):
    list_display = ('device', 'value', 'timestamp', 'status')
    list_filter = ('device', 'status')
    date_hierarchy = 'timestamp'

class AlertAdmin(admin.ModelAdmin):
    list_display = ('device', 'alert_type', 'is_resolved', 'status')
    list_filter = ('alert_type', 'is_resolved', 'status')
    search_fields = ('message',)

class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'status')
    search_fields = ('name', 'email')
    # No incluimos password en list_display por seguridad
    fields = ('name', 'email', 'password', 'status')  # Campos que se mostrarán en el formulario

# Registramos los modelos con sus respectivas clases Admin
admin.site.register(Category, CategoryAdmin)
admin.site.register(Zone, ZoneAdmin)
admin.site.register(Device, DeviceAdmin)
admin.site.register(Measurement, MeasurementAdmin)
admin.site.register(Alert, AlertAdmin)
admin.site.register(Organization, OrganizationAdmin)
