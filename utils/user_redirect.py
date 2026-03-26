from accounts.models import User

def get_user_redirect_url(user):
    if user.user_type == User.CITIZEN:
        return 'citizen_dashboard'
    elif user.user_type == User.OFFICE:
        return 'office_dashboard'
    elif user.user_type == User.ADMINISTRATOR:
        return 'admin_dashboard'
    else:
        return 'sign-in'