from flask_login import UserMixin

class User(UserMixin):
    def __init__ (self, sub , username, name, email, client_roles, realm_roles):
        self.id = sub 
        self.sub = sub 
        self. username = username
        self.name = name
        self.email = email
        self.client_roles = client_roles 
        self.realm_roles = realm_roles
