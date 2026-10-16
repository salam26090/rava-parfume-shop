from getpass import getpass
from werkzeug.security import generate_password_hash
print('ADMIN_PASSWORD_HASH=' + generate_password_hash(getpass('Choose admin password: ')))
