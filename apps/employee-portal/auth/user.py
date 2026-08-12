from flask_login import UserMixin

class User(UserMixin):
    def __init__(self,sub,username,name,email):
        self.id = sub
        self.username = username
        self.name = name
        self.email = email 