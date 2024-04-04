# python 
import hashlib
import random
from django.http import HttpResponse


# functions
# otp generation function
def generate_otp():
    otp = str(random.randint(100000, 999999))
    hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
    # Generate timestamp for 5 minutes from now
    return otp, hashed_otp

# otp verification function
def verify_otp(user_otp, stored_hashed_otp):
    hashed_user_otp = hashlib.sha256(user_otp.encode()).hexdigest()
    return hashed_user_otp == stored_hashed_otp

# delete cookie
def delete_cookie(request, cookie):
    response = HttpResponse()
    response.delete_cookie(cookie)
    return response
