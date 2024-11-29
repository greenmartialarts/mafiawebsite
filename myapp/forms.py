from django import forms
from .models import Room, Player, BugReport
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RoomCreationForm(forms.ModelForm):
    password = forms.CharField(
        max_length=128, 
        required=False,
        widget=forms.PasswordInput(),
        help_text="Optional: Set a password to make this room private"
    )

    class Meta:
        model = Room
        fields = ['room_name', 'password']

class JoinRoomForm(forms.Form):
    room_code = forms.CharField(max_length=6, min_length=6)
    password = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.PasswordInput()
    )

class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['name']

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your first name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your last name'})
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email address'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email

class BugReportForm(forms.ModelForm):
    class Meta:
        model = BugReport
        fields = ['title', 'description', 'steps_to_reproduce', 'priority']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'steps_to_reproduce': forms.Textarea(attrs={'rows': 4}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True
            
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email