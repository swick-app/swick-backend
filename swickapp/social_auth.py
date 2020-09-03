from .models import Customer, Server

# Create either a customer or a server based on user_type parameter in request
def create_user_by_type(backend, user, request, response, *args, **kwargs):
    # Create new Server object in database if it does not exist
    if (request['user_type'] == 'server' and
        not Server.objects.filter(user_id = user.id)):
        Server.objects.create(user_id = user.id)
    # Create new Customer object in database if it does not exist
    elif (request['user_type'] == 'customer' and
        not Customer.objects.filter(user_id = user.id)):
        Customer.objects.create(user_id = user.id)
