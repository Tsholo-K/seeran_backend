# python 
from decouple import config
import base64
import time
# httpx
import httpx

# channels
from channels.db import database_sync_to_async

# django
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.db import  transaction
from django.db.models import Q

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from users.models import CustomUser
from auth_tokens.models import AccessToken
from email_bans.models import EmailBan
from timetables.models import Schedule
from classes.models import Classroom
from attendances.models import Absent, Late

# serializers
from timetables.serializers import SessoinsSerializer
from email_bans.serializers import EmailBansSerializer, EmailBanSerializer
from users.serializers import StudentAccountsSerializer, StudentaccountAttendanceRecordSerializer

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email
from attendances.utility_functions import get_month_dates

@database_sync_to_async
def fetch_security_info(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        return { 'multifactor_authentication': account.multifactor_authentication, 'event_emails': account.event_emails }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_schedule(schedule_id):

    try:
        schedule = Schedule.objects.get(schedule_id=schedule_id)
    
        sessions = schedule.sessions.all()
        serializer = SessoinsSerializer(sessions, many=True)
        
        return { "sessions" : serializer.data }
    
    except Schedule.DoesNotExist:
        return {"error" : "schedule with the provided ID does not exist"}
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def form_attendance_register(user, class_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=class_id, register_class=True, school=account.school)
        
        if account.role not in ['ADMIN', 'PRINCIPAL'] and classroom.teacher != account:
            return { "error" : 'unauthorized request.. only the class teacher or school admin can submit the attendance register for this class' }
        
        # Get today's date
        today = timezone.localdate()
            
        # Check if an Absent instance exists for today and the given class
        attendance = Absent.objects.filter(date=today, classroom=classroom).first()

        if attendance:
            students = attendance.absent_students.all()
            attendance_register_taken = True

        else:
            students = classroom.students.all()
            attendance_register_taken = False

        serializer = StudentAccountsSerializer(students, many=True)

        return {"students": serializer.data, "attendance_register_taken" : attendance_register_taken}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
            
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def submit_absentes(user, class_id, students):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=class_id, school=account.school, register_class=True)
        
        if account.role not in ['ADMIN', 'PRINCIPAL'] and classroom.teacher != account:
            return { "error" : 'unauthorized request.. only the class teacher or school admin can submit the attendance register for this class' }

        today = timezone.localdate()

        if Absent.objects.filter(date=today, classroom=classroom).exists():
            return {'error': 'attendance register for this class has already been subimitted today.. can not resubmit'}

        with transaction.atomic():
            register = Absent.objects.create(submitted_by=account, classroom=classroom)
            if students:
                register.absentes = True
                for student in students.split(', '):
                    register.absent_students.add(CustomUser.objects.get(account_id=student))

            register.save()
        
        return { 'message': 'attendance register successfully taken for today'}
               
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def submit_late_arrivals(user, class_id, students):

    try:
        if not students:
            return {"error" : 'invalid request.. no students provided.. at least one student is needed to be marked as late'}

        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=class_id, school=account.school, register_class=True)
        
        if account.role not in ['ADMIN', 'PRINCIPAL'] and classroom.teacher != account:
            return { "error" : 'unauthorized request.. only the class teacher or school admin can submit the attendance register for this class' }

        today = timezone.localdate()

        absentes = Absent.objects.filter(date=today, classroom=classroom).first()
        if not absentes:
            return {'error': 'attendance register for this class has not been submitted today.. can not submit late arrivals before the attendance register'}

        if absentes and not absentes.absent_students.exists():
            return {'error': 'attendance register for this class has all students present or marked as late for today.. can not submit late arrivals when all students are accounted for'}

        register = Late.objects.filter(date=today, classroom=classroom).first()
        
        with transaction.atomic():
            if not register:
                register = Late.objects.create(submitted_by=account, classroom=classroom)
                
            for student in students.split(', '):
                student = CustomUser.objects.get(account_id=student)
                absentes.absent_students.remove(student)
                register.late_students.add(student)

            absentes.save()
            register.save()

        return { 'message': 'students marked as late, attendance register successfully updated'}
               
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_month_attendance_records(user, class_id, month_name):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=class_id, school=account.school, register_class=True)
        
        if account.role not in ['ADMIN', 'PRINCIPAL'] and classroom.teacher != account:
            return { "error" : 'unauthorized request.. only the class teacher or school admin can view the attendance records for this class' }
        
        start_date, end_date = get_month_dates(month_name)

        # Query for the Absent instances where absentes is True
        absents = Absent.objects.filter(Q(date__gte=start_date) & Q(date__lt=end_date) & Q(classroom=classroom) & Q(absentes=True))

        # For each absent instance, get the corresponding Late instance
        attendance_records = []
        for absent in absents:
            late = Late.objects.filter(date=absent.date, classroom=classroom).first()
            record = {
                'date': absent.date.strftime('%Y-%m-%d'),
                'absent_students': StudentaccountAttendanceRecordSerializer(absent.absent_students.all(), many=True).data,
                'late_students': StudentaccountAttendanceRecordSerializer(late.late_students.all(), many=True).data if late else [],
            }
            attendance_records.append(record)

        return {'records': attendance_records}
               
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def fetch_email_information(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        email_bans = EmailBan.objects.filter(email=account.email).order_by('-banned_at')
        serializer = EmailBansSerializer(email_bans, many=True)
    
        return {'information' : { "email_bans" : serializer.data, 'strikes' : account.email_ban_amount, 'banned' : account.email_banned }}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def fetch_email_information(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        email_bans = EmailBan.objects.filter(email=account.email).order_by('-banned_at')
        serializer = EmailBansSerializer(email_bans, many=True)
    
        return {'information' : { "email_bans" : serializer.data, 'strikes' : account.email_ban_amount, 'banned' : account.email_banned }}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_email_ban(email, email_ban_id):

    try:
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        if cache.get(email + 'email_revalidation_otp'):
            can_request = False
        else:
            can_request = True
            
        serializer = EmailBanSerializer(email_ban)
        return { "email_ban" : serializer.data , 'can_request': can_request}
        
    except EmailBan.DoesNotExist:
        return { 'error': 'ban with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def validate_email_revalidation(user, email_ban_id):

    try:
        account = CustomUser.objects.get(account_id=user)

        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        if not email_ban.email == account.email:
            return { "error" : "invalid request, banned email different from account email" }

        if email_ban.status == 'APPEALED':
            return { "error" : "ban already appealed" }

        if not email_ban.can_appeal:
            return { "error" : "can not appeal this email ban" }
        
        if email_ban.otp_send >= 3 :
            email_ban.can_appeal = False
            email_ban.status = 'BANNED'
            email_ban.save()
            
            return { "denied" : "maximum amount of OTP sends reached, email permanently banned",  }
        
        return {'user' : account}
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except EmailBan.DoesNotExist:
        return {'error': 'ban with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def update_email_ban(email_ban_id):

    try:
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        email_ban.otp_send += 1
        if email_ban.status != 'PENDING':
            email_ban.status = 'PENDING'
        email_ban.save()
        
        return {"message": "a new OTP has been sent to your email address"}

    except EmailBan.DoesNotExist:
        return {'error': 'ban with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def verify_email_revalidate_otp(user, otp, email_ban_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        # try to get revalidation otp from cache
        hashed_otp = cache.get(account.email + 'email_revalidation_otp')
        if not hashed_otp:
            cache.delete(account.email + 'email_revalidation_attempts')
            return {"error": "OTP expired"}

        # check if both otps are valid
        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=hashed_otp):
            
            
            email_ban.status = 'APPEALED'
            account.email_banned = False
            account.save()
            email_ban.save()

            return {"message": "email successfully revalidated email ban lifted", 'status' : email_ban.status.title()}

        else:
            attempts = cache.get(account.email + 'email_revalidation_attempts', 3)
            
            # Incorrect OTP, decrement attempts and handle expiration
            attempts -= 1
            
            if attempts <= 0:

                cache.delete(account.email + 'email_revalidation_otp')
                cache.delete(account.email + 'email_revalidation_attempts')
                
                if email_ban.otp_send >= 3 :
                    email_ban.can_appeal = False
                    email_ban.status = 'BANNED'
                    email_ban.save()
                
                return {"denied": "maximum OTP verification attempts exceeded.."}
            
            cache.set(account.email + 'email_revalidation_attempts', attempts, timeout=300)  # Update attempts with expiration

            return {"error": f"revalidation error, incorrect OTP.. {attempts} attempts remaining"}
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except EmailBan.DoesNotExist:
        return {'error': 'ban with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}
    

@database_sync_to_async
def update_email(user, new_email, authorization_otp, access_token):
    
    try:
        if CustomUser.objects.filter(email=new_email).exists():
            return {"error": "an account with the provided email address already exists"}
        
        account = CustomUser.objects.get(account_id=user)
        
        if new_email == account.email:
            return {"error": "cannot set current email as new email"}
    
        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "OTP expired, taking you back to email verification.."}
    
        if not verify_user_otp(authorization_otp, hashed_authorization_otp):
            return {"denied": "incorrect authorization OTP, action forrbiden"}
            
        if not validate_user_email(new_email):
            return {'error': 'Invalid email format'}
    
        EmailBan.objects.filter(email=account.email).delete()
        
        account.email = new_email
        account.email_ban_amount = 0
        account.save()
        
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "email changed successfully"}
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def update_password(user, new_password, authorization_otp, access_token):
    
    try:
        account = CustomUser.objects.get(account_id=user)
    
        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "OTP expired, taking you back to email verification.."}
    
        if not verify_user_otp(authorization_otp, hashed_authorization_otp):
            return {"denied": "incorrect authorization OTP, action forrbiden"}
    
        account.set_password(new_password)
        account.save()
        
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "password changed successfully"}
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except Exception as e:
        return {"error": {str(e)}}
    

@database_sync_to_async
def verify_email(email):

    try:
        validate_email(email)
        
        account = CustomUser.objects.get(email=email)
        
        # check if users email is banned
        if account.email_banned:
            return { "error" : "your email address has been banned.. request denied"}
        
        return {'user' : account}
    
    except CustomUser.DoesNotExist:
        return {'error': 'invalid email address'}

    except ValidationError:
        return {"error": "invalid email address"}
        
    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def verify_password(user, password):
    
    try:
        account = CustomUser.objects.get(account_id=user)
        
        # check if the users email is banned
        if account.email_banned:
            return { "error" : "your email address has been banned, request denied"}
            
        # Validate the password
        if not check_password(password, account.password):
            return {"error": "invalid password, please try again"}
        
        return {"user" : account}
       
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def verify_otp(user, otp):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        stored_hashed_otp_and_salt = cache.get(account.email + 'account_otp')

        if not stored_hashed_otp_and_salt:
            cache.delete(account.email + 'account_otp_attempts')
            return {"denied": "OTP expired.. please generate a new one"}

        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            
            # OTP is verified, prompt the user to set their password
            cache.delete(account.email)
            
            authorization_otp, hashed_authorization_otp, salt = generate_otp()
            cache.set(account.email + 'authorization_otp', (hashed_authorization_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "OTP verified successfully..", "authorization_otp" : authorization_otp}
        
        else:

            attempts = cache.get(account.email + 'account_otp_attempts', 3)
            
            # Incorrect OTP, decrement attempts and handle expiration
            attempts -= 1
            
            if attempts <= 0:
                cache.delete(account.email + 'account_otp')
                cache.delete(account.email + 'account_otp_attempts')
                
                return {"denied": "maximum OTP verification attempts exceeded.."}
            
            cache.set(account.email + 'account_otp_attempts', attempts, timeout=300)  # Update attempts with expiration

            return {"error": f"incorrect OTP.. {attempts} attempts remaining"}
       
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
 
    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def update_multi_factor_authentication(user, toggle):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        if account.email_banned:
            return { "error" : "your email has been banned"}
    
        account.multifactor_authentication = toggle
        account.save()
        
        return {'message': 'Multifactor authentication {} successfully'.format('enabled' if toggle else 'disabled')}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def log_user_out(access_token):
         
    try:
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
        
        return {"message": "logged you out successful"}
    
    except TokenError as e:
        return {"error": str(e)}

    except Exception as e:
        return {"error": str(e)}


async def send_account_confirmation_email(user):
    
    try:
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
            return {"message": f"an account confirmation email has been sent to the users email address"}
            
        else:
            return {"error": "failed to send OTP to users email address"}
    
    except Exception as e:
        return {"error": str(e)}


async def send_one_time_pin_email(user, reason):
    
    try:
        otp, hashed_otp, salt = generate_otp()

        # Define your Mailgun API URL
        mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"

        # Define your email data
        email_data = {
            "from": "seeran grades <authorization@" + config('MAILGUN_DOMAIN') + ">",
            "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
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
            response = await client.post( mailgun_api_url, headers=headers, data=email_data )

        if response.status_code == 200:
                
            # if the email was successfully delivered cache the hashed otp against the users 'email' address for 5 mins( 300 seconds)
            # this is cached to our redis database for faster retrieval when we verify the otp
            cache.set(user.email + 'account_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "a new OTP has been sent to your email address"}
        
        if response.status_code in [ 400, 401, 402, 403, 404 ]:
            return {"error": f"there was an error sending the email, please open a new bug ticket with the issue. error code {response.status_code}"}
        
        if response.status_code == 429:
            return {"error": f"there was an error sending the email, please try again in a few moments"}

        else:
            return {"error": "failed to send OTP to your  email address"}
    
    except Exception as e:
        return {"error": str(e)}


async def send_email_revalidation_one_time_pin_email(user):
    
    try:
        otp, hashed_otp, salt = generate_otp()

        # Define your Mailgun API URL
        mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"

        # Define your email data
        email_data = {
            "from": "seeran grades <authorization@" + config('MAILGUN_DOMAIN') + ">",
            "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
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
            response = await client.post( mailgun_api_url, headers=headers, data=email_data )

        if response.status_code == 200:
                
            # if the email was successfully delivered cache the hashed otp against the users 'email' address for 5 mins( 300 seconds)
            # this is cached to our redis database for faster retrieval when we verify the otp
            cache.set(user.email + 'email_revalidation_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "email sent"}
        
        if response.status_code in [ 400, 401, 402, 403, 404 ]:
            return {"error": f"there was an error sending the email, please open a new bug ticket with the issue. error code {response.status_code}"}
        
        if response.status_code == 429:
            return {"error": f"there was an error sending the email, please try again in a few moments"}
        
        else:
            return {"error": "failed to send OTP to your  email address"}

    except Exception as e:
        return {"error": str(e)}
            
