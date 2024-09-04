from django.urls import path
from .views import (
    create_user_view, 
    user_profile, 
    forget_password_view_email, 
    verify_user_upon_registration,
    verify_user_retry_code,
    login_view,
    logout_view,

)

urlpatterns = [
    path('users/', create_user_view, name="create_user_view"),
    path('login/', login_view, name="login_view"),
    path('logout/', logout_view, name="logout_view"),
    path('verify-user-upon-registration/', verify_user_upon_registration, name="verify_user_upon_registration"), # code, user_id

    path('profile/', user_profile, name="user_profile"),
    
    path('forget-password-with-email/', forget_password_view_email, name="forget_password_view_email"), # email
    path('verify-user-retry-code/', verify_user_retry_code, name="verify_user_retry_code"), # user_id
    

]
