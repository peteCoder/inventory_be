from rest_framework import serializers
from .models import Profile, User



class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            # "username",
            "email",
            "groups",
            "user_permissions",
            "last_login",
            "date_joined",
            "is_staff",
            "is_active",
            "is_superuser",
            "role",
            "password",
            # "code",
        ]

    def create(self, validated_data):
        # Hash the password before saving the user
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user