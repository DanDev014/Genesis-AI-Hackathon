import bcrypt
new_hash = bcrypt.hashpw(b"TempPassword123!", bcrypt.gensalt())
print(new_hash.decode())