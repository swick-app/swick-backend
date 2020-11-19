from django.http import JsonResponse
from rest_framework.decorators import api_view

from .models import User


@api_view(['POST'])
def update_info(request):
    """
    header:
        Authorization: Token ...
    params:
        name
        email
    return:
        status
    """
    # Update name
    request.user.name = request.POST["name"]
    request.user.save()
    # Update email
    email = request.POST["email"]
    # Check if email is already taken
    try:
        user = User.objects.get(email=email)
        if user != request.user:
            return JsonResponse({"status": "email_already_taken"})
    # If email is not taken
    except User.DoesNotExist:
        request.user.email = email
        request.user.save()
        return JsonResponse({"status": "success"})
