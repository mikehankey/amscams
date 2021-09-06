import os
import boto3
import botocore.exceptions
import hmac
import hashlib
import base64
import json
from lib.PipeUtil import save_json_file, load_json_file, cfe
pool_id = "us-east-1_AhZZf7mAc"
app_client_id = "5l2pl11sdre3vnlrg9krejlvbg"
app_client_secret = "7dn17sg2896i8cvgk0u5c0turguibpk4242q5tuivk74rdjkokq"

os.environ["COGNITO_JWKS"] =str({"keys":[{"alg":"RS256","e":"AQAB","kid":"eR4ccpMdmsgmt+ZM7TP6v/NsllBEs3thTCkghG6vCCw=","kty":"RSA","n":"0dGCVuxEff3DAHRimiRlMSe1zO_ZclVYtVGVIKj6Yw_6j9epeuQBLh9o8gqyDzjO0DTBA53UA4xjmPX_XcPPHFt-tYii5_aF2VDNnE9DPc5Nyi3RGa1YkHfwpouAv3DwJSAd6yrJ1eCETtoUcza06ppUhMq1FZcbOIcUvLOJwiQelER8BzK5ow4jTDN77GRPHUjihampmUBQeEqXkSsyXKqDQimduasy3lsZaxXIGHTGJvzpjUPUdlAHKRW_aCwy3hcOyQPHSRsaLswsomTvhCUZdv-HQ5kRzg-lkoUdFcttIWcQ83zgoNWOOJnu7I5HEFtV4Y6Awj8q3PwSzsJktQ","use":"sig"},{"alg":"RS256","e":"AQAB","kid":"3bV2tESxNMdDmBwFcpipJu99bHEAUtb+UES2F0Dpolw=","kty":"RSA","n":"wprsPAvikaXbKhJeFwDs8PA494o_AKdDuPh0HLd8fNhr8Bx192C87dCIm8AH3UQR-rNVNBDtOUeo-7xtNBN2j_S0iD-AqSyAbxDBCELYF1LaHaFiK9V6YSkTRuAStmj7xxvHoMnvT-C6w2byDVbiBr3hv1J3eeK7F0MwQQPSSVNzxjPQCxFkZppz-qZgIk2wRLIkiz6KFsenJDAtoLXfV0DRdx4a7i3yEK-32lg3WnW-P527zWXbbF7St8zn-NsZ93KS8o3r2igWnyK2n4lYMTHbPvATH4vB9L0lPoltrC3TW1JShT--n6mMCWaCGiXljm7SLq5V15JRz_awLPmy3Q","use":"sig"}]})
        
        

info_url = "https://cognito-idp.us-east-1.amazonaws.com/" + pool_id + "/.well-known/jwks.json"
client = boto3.client('cognito-idp')

def get_secret_hash(username):
    msg = username + app_client_id 
    dig = hmac.new(str(app_client_secret).encode('utf-8'), 
        msg = str(msg).encode('utf-8'), digestmod=hashlib.sha256).digest()
    d2 = base64.b64encode(dig).decode()
    return d2

def signup_new_user(username, password, email, phone, op_name):
    print("SIGNUP:", username, password, email,phone,op_name)
    data = {}
    data['sgn_username'] = username
    data['email'] = email
    data['phone'] = phone
    data['op_name'] = op_name
    #if True:
    try:
        response = client.sign_up(
            ClientId=app_client_id,
            SecretHash=get_secret_hash(username),
            Username=username,
            Password=password,
            UserAttributes=[
            {
                'Name': 'email',
                'Value': email
            },
            {
                'Name': 'phone_number',
                'Value': phone
            },
            {
                'Name': 'name',
                'Value': op_name
            }
            ])
    except client.exceptions.UsernameExistsException as e:
        print("error", e)
        return {"error": True, 
               "success": False, 
               "message": "This username already exists", 
               "data": None}
    #if False:
    except client.exceptions.InvalidPasswordException as e:
        
        return {"error": True, 
               "success": False, 
               "message": "Password should have Caps,\
                          Special chars, Numbers", 
               "data": None}
    #if False:
    except client.exceptions.UserLambdaValidationException as e:
        return {"error": False, 
               "success": True, 
               "message": "Email already exists", 
               "data": None}
    
    #if False:
    except Exception as e:
        return {"error": True, 
                "success": False, 
                "message": str(e), 
               "data": None}
    
    #if False:
    return {"error": False, 
            "success": True, 
            "message": "Signup complete. You will be notified when your account has been activated. ", 
            "data": data}

    print(response)


def resend_code(username):
    try:
        response = client.resend_confirmation_code(
        ClientId=app_client_id,
        SecretHash=get_secret_hash(username),
        Username=username)
    except client.exceptions.UserNotFoundException:
        return {"error": True, "success": False, "message":   "Username doesnt exists"}
        
    except client.exceptions.InvalidParameterException:
        return {"error": True, "success": False, "message": "User is already confirmed"}
    
    except Exception as e:
        return {"error": True, "success": False, "message": f"Unknown error {e.__str__()} "}
    print(response)  
    return  {"error": False, "success": True}

def verify_new_user(username, code):
    print("VVVV:", username, code)
    try:
        response = client.confirm_sign_up(
            ClientId=app_client_id,
            SecretHash=get_secret_hash(username),
            Username=username,
            ConfirmationCode=code
        )
        return(response)
    except client.exceptions.UserNotFoundException:
        return {"error": True, "success": False, "message": "Username doesnt exists"}
    except client.exceptions.CodeMismatchException:
        return {"error": True, "success": False, "message": "Invalid Verification code"}
        
    except client.exceptions.NotAuthorizedException:
        return {"error": True, "success": False, "message": "User is already confirmed"}
    
    except Exception as e:
        return {"error": True, "success": False, "message": f"Unknown error {e.__str__()} "}

def initiate_auth(username, password):
    secret_hash = get_secret_hash(username)
    try:
      resp = client.admin_initiate_auth(
                 UserPoolId=pool_id,
                 ClientId=app_client_id,
                 AuthFlow='ADMIN_NO_SRP_AUTH',
                 AuthParameters={
                     'USERNAME': username,
                     'SECRET_HASH': secret_hash,
                     'PASSWORD': password,
                  },
                ClientMetadata={
                  'username': username,
                  'password': password,
              })
    except client.exceptions.NotAuthorizedException:
        return None, "The username or password is incorrect"
    except client.exceptions.UserNotConfirmedException:
        return None, "User is not confirmed"
    except Exception as e:
        return None, e.__str__()
    return resp, None

def get_user_details(access_token):
    try: 
    #if True:
       response = client.get_user(
          AccessToken=access_token
       )
       return(response)
    except:
        print(client.exceptions.keys())


# signup new user
#username = "mhankey"
#password = "M1k3r0ck$"
#email = "mike.hankey@gmail.com"
#phone = "+14109059187"
#name = "Mike Hankey"
#resp = signup_new_user(username, password, email, phone, name)
# print resp

# function call for verify new user
#code = "020920"
#resp = verify_new_user(username, code)
#print(resp)


#resend_code("mhankey")

#login_info,msg = initiate_auth(username, password)
#print(login_info)
#details = get_user_details(login_info['AuthenticationResult']['AccessToken'])
#session_data = {}
#session_data['login_info'] = login_info
#session_data['details'] = details
#for attr in details['UserAttributes']:
#   print(attr['Name'])
#   if attr['Name'] == 'sub':
#      session_id = attr['Value']

#save_json_file("sessions/" + session_id, session_data)
#exit()

