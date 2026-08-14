def get_identity(user):
    return {
        "id" : user.id,
        "username" : user.username,
        "name" : user.name,
        "email" : user.email
        
    }