from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Province, District, Sector, Village

class UserSignUpForm(UserCreationForm):
    full_name = forms.CharField(max_length=255, required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    national_id = forms.CharField(max_length=20, required=False)
    email = forms.EmailField(required=False)
    
    # We'll use simple CharFields or ModelChoiceFields for location depending on how we handle JS
    # For now, let's use ModelChoiceFields to match the hierarchy
    province = forms.ModelChoiceField(queryset=Province.objects.all(), required=False)
    district = forms.ModelChoiceField(queryset=District.objects.all(), required=False)
    sector = forms.ModelChoiceField(queryset=Sector.objects.all(), required=False)
    village = forms.ModelChoiceField(queryset=Village.objects.all(), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('full_name', 'phone_number', 'national_id', 'email', 'province', 'district', 'sector', 'village')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.full_name = self.cleaned_data['full_name']
        user.phone_number = self.cleaned_data['phone_number']
        user.national_id = self.cleaned_data['national_id']
        user.email = self.cleaned_data['email']
        user.province = self.cleaned_data['province']
        user.district = self.cleaned_data['district']
        user.sector = self.cleaned_data['sector']
        user.village = self.cleaned_data['village']
        user.user_type = 'citizen'
        if commit:
            user.save()
        return user

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number or Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
class UserProfileUpdateForm(forms.ModelForm):
    province = forms.ModelChoiceField(
        queryset=Province.objects.all(),
        required=False,
        empty_label="Select Province",
        widget=forms.Select(attrs={
            'class': 'form-select form-control',
            'id': 'province',
            'aria-label': 'Select Province',
        })
    )
    district = forms.ModelChoiceField(
        queryset=District.objects.none(),
        required=False,
        empty_label="Select District",
        widget=forms.Select(attrs={
            'class': 'form-select form-control',
            'id': 'district',
            'aria-label': 'Select District',
        })
    )
    sector = forms.ModelChoiceField(
        queryset=Sector.objects.none(),
        required=False,
        empty_label="Select Sector",
        widget=forms.Select(attrs={
            'class': 'form-select form-control',
            'id': 'sector',
            'aria-label': 'Select Sector',
        })
    )
    village = forms.ModelChoiceField(
        queryset=Village.objects.none(),
        required=False,
        empty_label="Select Village",
        widget=forms.Select(attrs={
            'class': 'form-select form-control',
            'id': 'village',
            'aria-label': 'Select Village',
        })
    )

    class Meta:
        model = User
        fields = ['full_name', 'phone_number', 'email', 'gender', 'profile_picture', 'province', 'district', 'sector', 'village']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'floatingInput1'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'floatingInput4'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'id': 'floatingInput3'}),
            'gender': forms.Select(attrs={'class': 'form-select form-control', 'id': 'floatingSelect8', 'aria-label': 'Select Gender'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form__file bottom-0', 'id': 'upload-files'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # On POST: expand querysets so submitted IDs pass validation
        data = args[0] if args else None
        if data:
            province_id = data.get('province')
            district_id = data.get('district')
            sector_id = data.get('sector')
            if province_id:
                self.fields['district'].queryset = District.objects.filter(province_id=province_id)
            if district_id:
                self.fields['sector'].queryset = Sector.objects.filter(district_id=district_id)
            if sector_id:
                self.fields['village'].queryset = Village.objects.filter(sector_id=sector_id)
        # On GET: pre-populate from saved instance
        elif self.instance and self.instance.pk:
            if self.instance.province:
                self.fields['district'].queryset = District.objects.filter(province=self.instance.province)
            if self.instance.district:
                self.fields['sector'].queryset = Sector.objects.filter(district=self.instance.district)
            if self.instance.sector:
                self.fields['village'].queryset = Village.objects.filter(sector=self.instance.sector)
