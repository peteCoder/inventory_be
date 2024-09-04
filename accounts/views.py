# Django
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model

from cloudinary.uploader import upload
from decouple import config

# Rest Framework
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes, parser_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser

from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .serializers import UserProfileSerializer

from .models import Profile

from .helpers import (
    check_email, 
    check_password,
    send_registration_code_mail,
    generate_4_digit_code,
    check_if_code_matches,

)

from .permissions import IsUserVerified


# Global User
User = get_user_model()


@api_view(['POST'])
def create_user_view(request):
    if request.method == 'POST':
        email = request.data.get("email")
        password = request.data.get("password", None)
        password2 = request.data.get("password2", None)
        first_name = request.data.get("first_name", None)
        last_name = request.data.get("last_name", None)
        phone_number = request.data.get("phone_number")
        gender = request.data.get("gender")
        address = request.data.get("address")
        birth_date = request.data.get("birth_date", None)
        bio = request.data.get("bio", None)

        # Check for missing fields
        if not email:
            return Response({"detail": "Email is a required field"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not password:
            return Response({"detail": "Password is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not password2:
            return Response({"detail": "Confirm Password is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if password != password2:
            return Response({"detail": "Passwords must match"}, status=status.HTTP_400_BAD_REQUEST)

        GENDER_CHOICES = ["male", "female"]
        
        if gender not in GENDER_CHOICES:
            return Response({"detail": "Gender is required and must be either a male or female"}, status=status.HTTP_400_BAD_REQUEST)

    
        if not all([first_name, last_name]):
            return Response({"detail": "First Name and Last Name are all required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate email and password using Django validators
        email_valid_status = check_email(email)
        password_valid_status = check_password(password)

        if not email_valid_status.status:
            return Response({"detail": " ".join(email_valid_status.error_messages)}, status=status.HTTP_400_BAD_REQUEST)

        if not password_valid_status.status:
            return Response({"detail": " ".join(password_valid_status.error_messages)}, status=status.HTTP_400_BAD_REQUEST)

        # Lastly Check if user already exists
        existing_user = User.objects.filter(email=email)
        if len(existing_user) > 1 or existing_user:
            return Response({
                "detail": "User with email already exists."
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Finally create user Create user
            code = generate_4_digit_code()

            data = request.data
            user = User.objects.create(email=email)
            user.code = code
            user.set_password(password)

            user.save()

            
            

            user.profile.first_name = first_name
            user.profile.last_name = last_name
            user.profile.phone_number = phone_number
            user.profile.gender = gender
            user.profile.birth_date = birth_date
            user.profile.address = address
            user.profile.bio = bio

            user.profile.save()
            user.save()

            token_key = user.auth_token.key
            print(data)
            user_details = {
                "message": f"A verification code was sent to {user.email}",
                # "auth_token": token_key,
                "user_id": user.id,
                "email": user.email,
                "permissions": {
                    "is_superuser": user.is_superuser,
                    "is_manager": user.role == "manager",
                    "is_cashier": user.role == "cashier",
                }
            }

            send_registration_code_mail(code, user.email)
            

            return Response(user_details, status=status.HTTP_201_CREATED)
    else:
        return Response({"detail": "HTTP method is not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)



# Forget Password view
@api_view(['POST'])
def forget_password_view_email(request):
    """
    This view sends password reset code to user's email
    
    """
    # Get user email
    data = request.data
    email = data.get("email")
    code_generated = generate_4_digit_code()
    # Check if user with email exists in the database
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"detail": "User with email does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Set the code in the user email
    user.code = code_generated
    user.save()

    # Here we should sent a verification code to user for confirmation of their identity
    # Send code verification to provided email
    response_gotten_from_code = send_registration_code_mail(code_generated, email)

    # Return a response
    if response_gotten_from_code == 200:
        return Response({"message": "Code was sent to your email", "user_id": user.id}, status=status.HTTP_200_OK)
    else:
        # Here the status code could be any respond coming from email backend
        return Response({"detail": "Encountered an issue sending email. Retry!", "user_id": user.id}, status=response_gotten_from_code)
    


# Verify user registration
@api_view(['POST'])
def verify_user_upon_registration(request):
    """Verifies a user upon registration using the provided code"""
    data = request.data
    code = data.get("code")
    user_id = data.get("user_id")

    # Check if user exists in database
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"detail": "User does not exist."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        is_correct_code = check_if_code_matches(user.code, code)
        if is_correct_code:
            user.is_verified = True
            user.code = None
            user.save()
            return Response({
                "message": "Account has been verified successfully. Proceed to login.",
            }, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "User code is invalid"}, status=status.HTTP_400_BAD_REQUEST)
    except AssertionError:
        return Response({"detail": "Values must be valid integers"}, status=status.HTTP_400_BAD_REQUEST)



# Retry Verify user registration
@api_view(['POST'])
def verify_user_retry_code(request):
    """
    Resend verification code to user mail
    All that is needed to perform this task is the user_id
    """
    data = request.data
    user_id = data.get("user_id")
    # Generate and send new profile code
    code_generated = generate_4_digit_code()

    # Check if user exists
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        # print("User does not exist.")
        return Response({"detail": "Invalid user id. User does not exist."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Send some code to user email
    user.code = code_generated
    user.save()

    response_gotten_from_code = send_registration_code_mail(code_generated, user.email)
    if response_gotten_from_code == 200:
        return Response({"message": "Code was resent to your email"}, status=status.HTTP_200_OK)
    else:
        # Here the status code could be any respond coming from email backend
        return Response({"detail": "Encountered an issue sending email. Retry!"}, status=response_gotten_from_code)




# GET AND UPDATE USER PROFILE
@api_view(['GET', 'PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def user_profile(request):
    user = request.user

    if request.method == 'GET':
        if user:
            user_profile_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.profile.first_name,
                "last_name": user.profile.last_name,
                "birth_date": user.profile.birth_date,
                "image_url": user.profile.image_url,
                "bio": user.profile.bio,
                "role": user.role,
                "permissions": {
                    "is_superuser": user.is_superuser,
                    "is_manager": user.role == "manager",
                    "is_cashier": user.role == "cashier",
                    "is_verified": user.is_verified,
                }
            }
            return Response(user_profile_data, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Authorization header not found in the request."}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PUT":
        # Profile details
        first_name = request.data.get("first_name", user.profile.first_name)
        last_name = request.data.get("last_name", user.profile.last_name)
        phone_number = request.data.get("phone_number", user.profile.phone_number)
        address = request.data.get("address", user.profile.address)
        gender = request.data.get("gender", user.profile.gender)
        role = request.data.get("role", user.role)
        birth_date = request.data.get("birth_date", user.profile.birth_date)
        bio = request.data.get("bio", user.profile.bio)

        # Handle the image upload to Cloudinary
        image = request.FILES.get('image', None)

        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({"detail": "Profile was not  found"}, status=status.HTTP_404_NOT_FOUND)
        
        if image:
            try:
                upload_result = upload(image)
                uploaded_image_secure_url = upload_result.get("secure_url")
                profile.image = uploaded_image_secure_url  # Save Cloudinary URL to profile's image_url field
            except Exception as e:
                return Response({"detail": "Image upload failed", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

        profile.first_name = first_name
        profile.last_name = last_name
        profile.phone_number = phone_number
        profile.address = address
        profile.gender = gender
        profile.birth_date = birth_date
        profile.bio = bio
        
        profile.save()

        serializer = UserProfileSerializer(profile)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    else:
        return Response({"message": "Method not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


# CHANGE LOGGED IN USER PASSWORD
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def change_user_password(request):
    data = request.data
    
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    confirm_new_password = data.get("confirm_new_password")


    # Check if both fields are provided
    if not all([old_password, new_password, confirm_new_password]):
        return Response({"detail": " ".join(["old_password, new_password and confirm_new_password fields are required."])}, status=status.HTTP_400_BAD_REQUEST)
    
    if new_password != confirm_new_password:
        return Response({"detail": " ".join(["Passwords do not match."])}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user exists
    # It is highly unlikely that user does not
    # exist given the token
    try:
        user = User.objects.get(id=request.user.id)
    except User.DoesNotExist:
        return Response({"detail": " ".join(["Invalid user credentials. User does not exist."])}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if old_passwordd and new_password are a match
    if old_password == new_password:
        return Response({"detail": " ".join(["New password must be different from the previous passwords. "])}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if old_password field is correct or wrong
    if not user.check_password(old_password):
        return Response({"detail": " ".join(["Old Password entered is incorrect"])}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if passwords meet the django validation score
    password_valid_status = check_password(new_password, user=request.user)
    if password_valid_status.status == False:
        return Response({
            "detail": " ".join([
                error_message for error_message in password_valid_status.error_messages
            ])
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Finally update password
    user.set_password(new_password)
    user.save()
    return Response({"message": "Password was successfully updated."}, status=status.HTTP_200_OK)


# USER LOGOUT VIEW
@api_view(['POST'])
def login_view(request):
    data = request.data
    email = data.get("email")
    password = data.get("password")

    if not all([email, password]):
        return Response({'detail': "User email and password are required."}, status=status.HTTP_400_BAD_REQUEST)
    
    email_valid_status = check_email(email)
    password_valid_status = check_password(password)

    if not email_valid_status.status:
        return Response({"detail": " ".join(email_valid_status.error_messages)}, status=status.HTTP_400_BAD_REQUEST)

    if not password_valid_status.status:
        return Response({"detail": " ".join(password_valid_status.error_messages)}, status=status.HTTP_400_BAD_REQUEST)

    # Check if user with email exists
    users = User.objects.filter(email=email)

    user = users.first()

    user_exists = users.exists()

    if not user_exists:
        return Response({"detail": "User with email does not exist. "}, status=status.HTTP_400_BAD_REQUEST)
    
    if not user.check_password(password):
        return Response({"detail": "User password is not correct"}, status=status.HTTP_400_BAD_REQUEST)

    oldTokens = Token.objects.filter(user__id=user.id)
    for token in oldTokens:
        token.delete()

    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'user_id': user.pk,
        'email': user.email,
        "permissions": {
            "is_superuser": user.is_superuser,
            "is_manager": user.role == "manager",
            "is_cashier": user.role == "cashier",
            "is_verified": user.is_verified,
        }
    })



# USER LOGOUT VIEW
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout_view(request):
    user = request.user
    # Check if the Authorization header is present in the request

    if 'Authorization' in request.headers:
        # Extract the token from the Authorization header
        auth_header = request.headers['Authorization']
        _, token = auth_header.split()  # Assuming the token is separated by a space after "Token"
        
        # Check if the token exists in the database
        try:
            user_token = Token.objects.get(key=token)
            user_token.delete()
        except Token.DoesNotExist:
            return Response({"detail": "Invalid token."}, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)
    else:
        return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
























