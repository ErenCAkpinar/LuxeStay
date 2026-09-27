from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password


User = get_user_model()


class SignupForm(forms.Form):
    firstName = forms.CharField(max_length=150, label="First name")
    lastName = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    terms = forms.BooleanField()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu e-posta ile zaten bir hesap var.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def save(self):
        return User.objects.create_user(
            username=self.cleaned_data["email"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data["firstName"].strip(),
            last_name=self.cleaned_data["lastName"].strip(),
        )


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    remember = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            username = email.strip().lower()
            self.user = authenticate(username=username, password=password)
            if self.user is None:
                raise forms.ValidationError("E-posta veya şifre hatalı.")

        return cleaned_data
