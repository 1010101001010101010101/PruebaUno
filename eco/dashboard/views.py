from functools import wraps
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.http import Http404

from django.core.exceptions import FieldError

from .models import Device, Measurement, Alert


def login_required(view_func):
    """
    Simple decorator de sesión (usa request.session['is_logged_in']).
    Redirige a 'login' si no hay sesión válida.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_logged_in', False):
            messages.error(request, 'Debes iniciar sesión para acceder a esta página')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def dashboard(request):
    organization_name = request.session.get('organization_name', '')
    organization_id = request.session.get('organization_id')

    if not organization_id:
        messages.error(request, 'Sesión inválida. Por favor, inicia sesión nuevamente.')
        return redirect('login')

    # --- Dispositivos por categoría (dict: nombre -> conteo) ---
    try:
        categorias_qs = (
            Device.objects
            .filter(organization_id=organization_id)
            .values('category__name')
            .annotate(conteo=Count('id'))
        )
        dispositivos_por_categoria = {c['category__name'] or 'Sin categoría': c['conteo'] for c in categorias_qs}
    except FieldError:
        # si category no es FK con name
        categorias_qs = (
            Device.objects
            .filter(organization_id=organization_id)
            .values('category')
            .annotate(conteo=Count('id'))
        )
        dispositivos_por_categoria = {c.get('category') or 'Sin categoría': c['conteo'] for c in categorias_qs}

    # --- Dispositivos por zona (dict: nombre -> conteo) ---
    try:
        zonas_qs = (
            Device.objects
            .filter(organization_id=organization_id)
            .values('zone__name')
            .annotate(conteo=Count('id'))
        )
        dispositivos_por_zona = {z['zone__name'] or 'Sin zona': z['conteo'] for z in zonas_qs}
    except FieldError:
        zonas_qs = (
            Device.objects
            .filter(organization_id=organization_id)
            .values('zone')
            .annotate(conteo=Count('id'))
        )
        dispositivos_por_zona = {z.get('zone') or 'Sin zona': z['conteo'] for z in zonas_qs}

    # --- Alertas por severidad (dict alert_type -> conteo) ---
    severidad_qs = (
        Alert.objects
        .filter(device__organization_id=organization_id)
        .values('alert_type')
        .annotate(conteo=Count('id'))
    )
    alertas_por_severidad = {s.get('alert_type') or 'Sin tipo': s['conteo'] for s in severidad_qs}

    # --- Alertas recientes (QuerySet para usar atributos y device.name en template) ---
    alertas_recientes = (
        Alert.objects
        .filter(device__organization_id=organization_id)
        .select_related('device')
        .order_by('-created_at')[:10]
    )

    # --- Últimas mediciones: transformadas a dicts con claves esperadas por template ---
    ultimas_med_qs = (
        Measurement.objects
        .filter(device__organization_id=organization_id)
        .select_related('device')
        .order_by('-timestamp')[:10]
    )

    ultimas_mediciones = []
    for m in ultimas_med_qs:
        # fecha_hora: intenta varios nombres comunes
        fecha = getattr(m, 'fecha_hora', None) or getattr(m, 'timestamp', None) or getattr(m, 'created_at', None)
        # valor: intenta varios nombres
        valor = getattr(m, 'valor', None)
        if valor is None:
            valor = getattr(m, 'value', None)
        if valor is None:
            # fallback a cualquier campo numérico/str disponible (no obligatorio)
            valor = getattr(m, 'reading', None)

        dispositivo_nombre = None
        dispositivo_id = None
        if getattr(m, 'device', None):
            dispositivo_nombre = getattr(m.device, 'name', str(m.device))
            dispositivo_id = getattr(m.device, 'id', None)

        ultimas_mediciones.append({
            'fecha_hora': fecha,
            'valor': valor,
            'dispositivo': dispositivo_nombre,
            'device_id': dispositivo_id,  # por si en plantilla quieres linkear
        })

    context = {
        'organization_name': organization_name,
        'dispositivos_por_categoria': dispositivos_por_categoria,
        'dispositivos_por_zona': dispositivos_por_zona,
        'alertas_por_severidad': alertas_por_severidad,
        'alertas_recientes': alertas_recientes,
        'ultimas_mediciones': ultimas_mediciones,
    }

    return render(request, 'dashboard.html', context)


def home(request):
    return render(request, 'home.html')


@login_required
def devices_by_category(request):
    organization_id = request.session.get('organization_id')
    if not organization_id:
        messages.error(request, 'Sesión inválida. Por favor, inicia sesión nuevamente.')
        return redirect('login')

    try:
        categorias = (
            Device.objects
            .filter(organization_id=organization_id)
            .values('category__name')
            .annotate(conteo=Count('id'))
        )
        dispositivos_por_categoria = {c['category__name'] or 'Sin categoría': c['conteo'] for c in categorias}
    except FieldError:
        categorias = (
            Device.objects
            .filter(organization_id=organization_id)
            .values('category')
            .annotate(conteo=Count('id'))
        )
        dispositivos_por_categoria = {c.get('category') or 'Sin categoría': c['conteo'] for c in categorias}

    return render(request, 'devices_by_category.html', {
        'dispositivos_por_categoria': dispositivos_por_categoria
    })


@login_required
def devices_by_zone(request):
    organization_id = request.session.get('organization_id')
    if not organization_id:
        messages.error(request, 'Sesión inválida. Por favor, inicia sesión nuevamente.')
        return redirect('login')

    try:
        zonas = (
            Device.objects
            .filter(organization_id=organization_id)
            .values('zone__name')
            .annotate(conteo=Count('id'))
        )
        dispositivos_por_zona = {z['zone__name'] or 'Sin zona': z['conteo'] for z in zonas}
    except FieldError:
        zonas = (
            Device.objects
            .filter(organization_id=organization_id)
            .values('zone')
            .annotate(conteo=Count('id'))
        )
        dispositivos_por_zona = {z.get('zone') or 'Sin zona': z['conteo'] for z in zonas}

    return render(request, 'devices_by_zone.html', {
        'dispositivos_por_zona': dispositivos_por_zona
    })


@login_required
def alerts(request):
    organization_id = request.session.get('organization_id')
    if not organization_id:
        messages.error(request, 'Sesión inválida. Por favor, inicia sesión nuevamente.')
        return redirect('login')

    alerts_qs = (
        Alert.objects
        .filter(device__organization_id=organization_id)
        .select_related('device')
        .order_by('-created_at')[:50]
    )
    return render(request, 'alerts.html', {'alertas': alerts_qs})


@login_required
def measurements(request):
    organization_id = request.session.get('organization_id')
    if not organization_id:
        messages.error(request, 'Sesión inválida. Por favor, inicia sesión nuevamente.')
        return redirect('login')

    # mantenemos el queryset (la plantilla measurements.html espera m.device.id y m.device.name)
    measurements_qs = (
        Measurement.objects
        .filter(device__organization_id=organization_id)
        .select_related('device')
        .order_by('-timestamp')[:50]
    )
    return render(request, 'measurements.html', {'mediciones': measurements_qs})


@login_required
def devices_list(request):
    organization_id = request.session.get('organization_id')
    if not organization_id:
        messages.error(request, 'Sesión inválida. Por favor, inicia sesión nuevamente.')
        return redirect('login')

    category = request.GET.get('category', '')
    # intentar recuperar categorías tanto si category es FK (category__name) o campo simple
    try:
        categories = Device.objects.filter(organization_id=organization_id).values_list('category__name', flat=True).distinct()
    except FieldError:
        categories = Device.objects.filter(organization_id=organization_id).values_list('category', flat=True).distinct()

    devices = Device.objects.filter(organization_id=organization_id)
    if category:
        # intentamos filtrar por category__name y si falla, por category directo
        try:
            devices = devices.filter(category__name=category)
        except FieldError:
            devices = devices.filter(category=category)

    return render(request, 'devices_list.html', {
        'dispositivos': devices,
        'categorias': categories,
        'categoria_seleccionada': category,
    })


@login_required
def device_detail(request, id):
    organization_id = request.session.get('organization_id')
    if not organization_id:
        messages.error(request, 'Sesión inválida. Por favor, inicia sesión nuevamente.')
        return redirect('login')

    dispositivo = get_object_or_404(Device, pk=id)

    # Verificar que el dispositivo pertenezca a la organización del usuario
    if dispositivo.organization_id != organization_id:
        raise Http404("Dispositivo no encontrado")

    mediciones = Measurement.objects.filter(device=dispositivo).order_by('-timestamp')
    alertas = Alert.objects.filter(device=dispositivo).order_by('-created_at')
    return render(request, 'device_detail.html', {
        'dispositivo': dispositivo,
        'mediciones': mediciones,
        'alertas': alertas,
    })
