from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
from dashboard.models import Organization
from django.contrib.auth.hashers import make_password

# Definir el formulario dentro de views.py
class OrganizationRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Organization
        fields = ['name', 'email', 'password']
        labels = {
            'name': 'Nombre de la Organización',
            'email': 'Correo Electrónico',
            'password': 'Contraseña',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Las contraseñas no coinciden')
        
        return cleaned_data
    
    def save(self, commit=True):
        organization = super().save(commit=False)
        organization.password = make_password(self.cleaned_data['password'])
        if commit:
            organization.save()
        return organization

# Vista para el registro
def register_organization(request):
    if request.method == 'POST':
        form = OrganizationRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Organización registrada exitosamente')
            return redirect('register')
    else:
        form = OrganizationRegistrationForm()
    
    return render(request, 'register.html', {'form': form})