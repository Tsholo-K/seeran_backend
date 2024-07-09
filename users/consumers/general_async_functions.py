# python 
from decouple import config
import base64

# httpx
import httpx


async def send_account_confirmation_email(self, user):
    mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"
    email_data = {
        "from": "seeran grades <accounts@" + config('MAILGUN_DOMAIN') + ">",
        "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
        "subject": "Account Creation Confirmation",
        "template": "account creation confirmation",
    }
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post( mailgun_api_url, headers=headers, data=email_data )
        
    if response.status_code == 200:
        return {"message": "principal account created successfully"}
        
    else:
        return {"error": "failed to send OTP to users email address"}