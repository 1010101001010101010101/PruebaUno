from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from dashboard.models import Organization

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            # Buscar la organización por email
            organization = Organization.objects.get(email=email)
            
            # Verificar la contraseña
            if check_password(password, organization.password):
                # Guardar información de la organización en la sesión
                request.session['organization_id'] = organization.id
                request.session['organization_name'] = organization.name
                request.session['is_logged_in'] = True
                
                messages.success(request, f'Bienvenido, {organization.name}')
                return redirect('dashboard')
            else:
                return render(request, 'login.html', {'error_message': 'Contraseña incorrecta'})
                
        except Organization.DoesNotExist:
            return render(request, 'login.html', {'error_message': 'No existe una organización con ese correo electrónico'})
    
    return render(request, 'login.html')

def logout_view(request):
    # Eliminar datos de sesión
    if 'organization_id' in request.session:
        del request.session['organization_id']
    if 'organization_name' in request.session:
        del request.session['organization_name']
    if 'is_logged_in' in request.session:
        del request.session['is_logged_in']
    
    messages.success(request, 'Has cerrado sesión correctamente')
    return redirect('home')

def password_reset_view(request):
    return render(request, 'password-reset.html')