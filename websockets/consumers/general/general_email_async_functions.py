# python 
from decouple import config
import base64

# httpx
import httpx

# django
from django.core.cache import cache
from django.utils.translation import gettext as _

# utility functions 
from authentication.utils import generate_otp


async def send_account_confirmation_email(account):
    try:
        email_data = {
            "from": "seeran grades <accounts@" + config('MAILGUN_DOMAIN') + ">",
            "to": account.surname.title() + " " + account.name.title() + "<" + account.email_address + ">",
            "subject": "Account Creation Confirmation",
            "template": "account creation confirmation",
        }
        
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages", headers=headers, data=email_data)

        if response.status_code == 200:
            return {"message": f"account successfully created, an account confirmation email has been sent to the accounts email address. the user can now sign-in and activate the account"}
        elif response.status_code in [400, 401, 402, 403, 404]:
            return {"error": f"account successfully created, but there was an error sending an account confirmation email to the accounts email address. please open a new bug ticket with the issue, error code {response.status_code}"}
        elif response.status_code == 429:
            return {"error": "account successfully created, but there was an error sending an account confirmation email to the accounts email address, the status code recieved could indicate a rate limit issue so please wait some few minutes before creating a new account"}
        else:
            return {"error": "account successfully created, but there was an error sending an account confirmation email to the accounts email address."}
    
    except Exception as e:
        return {"error": str(e)}


async def send_one_time_pin_email(account, reason):
    try:
        otp, hashed_otp, salt = generate_otp()

        # Define your email data
        email_data = {
            "from": "seeran grades <authorization@" + config('MAILGUN_DOMAIN') + ">",
            "to": account.surname.title() + " " + account.name.title() + "<" + account.email_address + ">",
            "subject": "One Time Passcode",
            "template": "one-time passcode",
            "v:onetimecode": otp,
            "v:otpcodereason": reason
        }

        # Define your headers
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Send the email via Mailgun
        async with httpx.AsyncClient() as client:
            response = await client.post(f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages", headers=headers, data=email_data )

        if response.status_code == 200:
                
            # if the email was successfully delivered cache the hashed otp against the users 'email' address for 5 mins( 300 seconds)
            # this is cached to our redis database for faster retrieval when we verify the otp
            cache.set(account.email + 'account_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "a new OTP has been sent to your email address"}
        
        if response.status_code in [ 400, 401, 402, 403, 404 ]:
            return {"error": f"there was an error sending the email, please open a new bug ticket with the issue. error code {response.status_code}"}
        
        if response.status_code == 429:
            return {"error": f"there was an error sending the email, please try again in a few moments"}

        else:
            return {"error": "failed to send OTP to your  email address"}
    
    except Exception as e:
        return {"error": str(e)}


async def send_email_revalidation_one_time_pin_email(account):
    try:
        otp, hashed_otp, salt = generate_otp()

        # Define your email data
        email_data = {
            "from": "seeran grades <authorization@" + config('MAILGUN_DOMAIN') + ">",
            "to": account.surname.title() + " " + account.name.title() + "<" + account.email_address + ">",
            "subject": "One Time Passcode",
            "template": "one-time passcode",
            "v:onetimecode": otp,
            "v:otpcodereason": 'This OTP was generated for your account in response to your email revalidation request'
        }

        # Define your headers
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Send the email via Mailgun
        async with httpx.AsyncClient() as client:
            response = await client.post(f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages", headers=headers, data=email_data )

        if response.status_code == 200:
                
            # if the email was successfully delivered cache the hashed otp against the users 'email' address for 5 mins( 300 seconds)
            # this is cached to our redis database for faster retrieval when we verify the otp
            cache.set(account.email + 'email_revalidation_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "email sent"}
        
        if response.status_code in [ 400, 401, 402, 403, 404 ]:
            return {"error": f"there was an error sending the email, please open a new bug ticket with the issue. error code {response.status_code}"}
        
        if response.status_code == 429:
            return {"error": f"there was an error sending the email, please try again in a few moments"}
        
        else:
            return {"error": "failed to send OTP to your  email address"}

    except Exception as e:
        return {"error": str(e)}
            
