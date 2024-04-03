
# python 
import hashlib
import random



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

# invalidate user tokens function
def invalidate_tokens(user):
    try:
        # Clear the user's access & refresh token
        user.refresh_token = None
        user.access_token = None
        user.save()
    except Exception:
        # Handle any errors appropriately
        pass    


