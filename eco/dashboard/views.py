# dashboard/views.py
from functools import wraps
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.http import Http404

from django.core.exceptions import FieldError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.contrib.auth import logout as auth_logout
from django.views.decorators.http import require_POST

from .models import Device, Measurement, Alert, Organization


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


def _get_organization(request):
    """
    Intenta obtener la organización desde sesión o desde el user (profile o campo organization).
    Devuelve None si no se encuentra.
    """
    org = None
    org_id = request.session.get("organization_id")
    if org_id:
        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            org = None

    if org is None and request.user.is_authenticated:
        # Profile con FK organization
        profile = getattr(request.user, "profile", None)
        if profile and getattr(profile, "organization", None):
            org = profile.organization
        # CustomUser con campo organization
        if org is None:
            org = getattr(request.user, "organization", None)

    return org


@require_POST
def logout_view(request):
    """
    Cierra sesión (POST recomendado). Limpia request.session y desloguea al user de auth.
    Redirige a 'login'.
    """
    # limpia la sesión completa (esto borra organization_id, is_logged_in, etc.)
    request.session.flush()
    # Si usás django auth también lo cerramos (no falla si no hay user)
    try:
        auth_logout(request)
    except Exception:
        pass
    messages.info(request, "Sesión cerrada.")
    return redirect('login')


@login_required
def dashboard(request):
    organization_name = request.session.get('organization_name', '')
    org = _get_organization(request)
    organization_id = org.id if org else request.session.get('organization_id')

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

    # --- Alertas por severidad (normalizamos keys) ---
    severidad_counts = {}
    try:
        sever_qs = (
            Alert.objects
            .filter(device__organization_id=organization_id)
            .values('alert_type')
            .annotate(conteo=Count('id'))
        )
        for r in sever_qs:
            key = (r.get('alert_type') or '').upper()
            severidad_counts[key] = r['conteo']
    except FieldError:
        sever_qs = (
            Alert.objects
            .filter(device__organization_id=organization_id)
            .values('severity')
            .annotate(conteo=Count('id'))
        )
        for r in sever_qs:
            key = (r.get('severity') or '').upper()
            severidad_counts[key] = r['conteo']

    # Mapeo a variables de tarjeta (soporta CRITICAL/HIGH/MEDIUM o GRAVE/ALTO/MEDIANO)
    conteo_grave   = severidad_counts.get('CRITICAL') or severidad_counts.get('GRAVE') or 0
    conteo_alto    = severidad_counts.get('HIGH') or severidad_counts.get('ALTO') or 0
    conteo_mediano = severidad_counts.get('MEDIUM') or severidad_counts.get('MEDIANO') or 0

    # --- Alertas recientes (normalizamos alert_type para la plantilla) ---
    raw_alerts_qs = (
        Alert.objects
        .filter(device__organization_id=organization_id)
        .select_related('device')
        .order_by('-created_at')[:10]
    )

    alertas_recientes = []
    for a in raw_alerts_qs:
        at = getattr(a, 'alert_type', None) or getattr(a, 'severity', None) or ''
        setattr(a, 'alert_type', at)
        alertas_recientes.append(a)

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
        fecha = getattr(m, 'fecha_hora', None) or getattr(m, 'timestamp', None) or getattr(m, 'measured_at', None) or getattr(m, 'created_at', None)
        fecha_str = fecha.strftime("%Y-%m-%d %H:%M:%S") if fecha else ''
        # valor: intenta varios nombres
        valor = getattr(m, 'valor', None)
        if valor is None:
            valor = getattr(m, 'value', None)
        if valor is None:
            valor = getattr(m, 'reading', None)
        # dispositivo
        dispositivo_nombre = getattr(m.device, 'name', str(getattr(m, 'device', '')))
        dispositivo_id = getattr(m.device, 'id', None)

        ultimas_mediciones.append({
            'fecha_hora': fecha_str,
            'valor': valor,
            'dispositivo': dispositivo_nombre,
            'device_id': dispositivo_id,
        })

    context = {
        'organization_name': organization_name or (org.name if org else "Global"),
        'dispositivos_por_categoria': dispositivos_por_categoria,
        'dispositivos_por_zona': dispositivos_por_zona,
        'alertas_por_severidad': severidad_counts,
        'alertas_recientes': alertas_recientes,
        'ultimas_mediciones': ultimas_mediciones,
        'conteo_grave': conteo_grave,
        'conteo_alto': conteo_alto,
        'conteo_mediano': conteo_mediano,
    }

    return render(request, 'dashboard.html', context)


def home(request):
    return render(request, 'home.html')


@login_required
def devices_by_category(request):
    org = _get_organization(request)
    organization_id = org.id if org else request.session.get('organization_id')
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
    org = _get_organization(request)
    organization_id = org.id if org else request.session.get('organization_id')
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
    org = _get_organization(request)
    organization_id = org.id if org else request.session.get('organization_id')
    if not organization_id:
        messages.error(request, 'Sesión inválida. Por favor, inicia sesión nuevamente.')
        return redirect('login')

    alerts_qs = (
        Alert.objects
        .filter(device__organization_id=organization_id)
        .select_related('device')
        .order_by('-created_at')
    )

    # Paginación: ?page=
    page = request.GET.get('page', 1)
    paginator = Paginator(alerts_qs, 20)  # 20 por página
    try:
        alerts_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        alerts_page = paginator.page(1)

    # Normalizar alert_type en cada objeto (para compatibilidad con plantilla)
    alerts_list = []
    for a in alerts_page:
        at = getattr(a, 'alert_type', None) or getattr(a, 'severity', None) or ''
        setattr(a, 'alert_type', at)
        alerts_list.append(a)

    return render(request, 'alerts.html', {
        'alertas': alerts_list,
        'paginator': paginator,
        'page_obj': alerts_page,
    })


@login_required
def measurements(request):
    org = _get_organization(request)
    organization_id = org.id if org else request.session.get('organization_id')
    if not organization_id:
        messages.error(request, 'Sesión inválida. Por favor, inicia sesión nuevamente.')
        return redirect('login')

    # Queryset original (para plantillas que esperan objetos)
    measurements_qs = (
        Measurement.objects
        .filter(device__organization_id=organization_id)
        .select_related('device')
        .order_by('-timestamp')
    )

    # --- Serializamos una lista de dicts (para plantillas que esperan fecha/valor en claves específicas) ---
    ultimas_mediciones = []
    for m in measurements_qs[:50]:  # serializamos las primeras 50 para la tabla/paginado posterior
        fecha = getattr(m, 'fecha_hora', None) or getattr(m, 'timestamp', None) or getattr(m, 'measured_at', None) or getattr(m, 'created_at', None)
        fecha_str = fecha.strftime("%Y-%m-%d %H:%M:%S") if fecha else ''

        valor = getattr(m, 'valor', None)
        if valor is None:
            valor = getattr(m, 'value', None)
        if valor is None:
            valor = getattr(m, 'reading', None)
        # fallback a string para evitar mostrar vacío
        if valor is None:
            valor = ''

        dispositivo_nombre = getattr(m.device, 'name', str(getattr(m, 'device', '')))
        dispositivo_id = getattr(m.device, 'id', None)

        ultimas_mediciones.append({
            'fecha_hora': fecha_str,
            'valor': valor,
            'dispositivo': dispositivo_nombre,
            'device_id': dispositivo_id,
            'raw': m,  # opcional: dejo el objeto original por si lo necesitas en la plantilla
        })

    # Paginación sobre el queryset original (mantiene comportamiento actual)
    page = request.GET.get('page', 1)
    paginator = Paginator(measurements_qs, 50)
    try:
        measurements_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        measurements_page = paginator.page(1)

    return render(request, 'measurements.html', {
        'mediciones': measurements_page,      # queryset paginado (m.device, m.timestamp, m.value...)
        'ultimas_mediciones': ultimas_mediciones,  # lista serializada con fecha/valor/dispositivo
        'paginator': paginator,
        'page_obj': measurements_page,
    })


@login_required
def devices_list(request):
    org = _get_organization(request)
    organization_id = org.id if org else request.session.get('organization_id')
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
    org = _get_organization(request)
    organization_id = org.id if org else request.session.get('organization_id')
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
