from flask_login import UserMixin

class User(UserMixin):
    def __init__(self,sub,username,name,email,realm_roles,client_roles):
        self.id = sub
        self.username = username
        self.name = name
        self.email = email 
        self.realm_roles = realm_roles
        self.client_roles = client_roles