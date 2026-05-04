import urllib.request
import urllib.parse
import json

def send_intouch_sms(recipients, message):
    """
    Sends an SMS using Intouch SMS API.
    recipients: string or list of strings (e.g., '+25078...')
    message: string
    """
    url = "https://www.intouchsms.co.rw/api/sendsms/.json"
    token = "9c8b0939b5c4a0a3048dbc98d04005ca2802d72f"
    
    if isinstance(recipients, list):
        recipients = ",".join(recipients)
    
    # Clean phone number if needed (ensure it starts with 250)
    # Simple logic for Rwanda (+2507XXX or 07XXX)
    clean_recipients = []
    for r in recipients.split(','):
        r = r.strip()
        if r.startswith('07'):
            r = '250' + r[1:]
        elif r.startswith('+250'):
            r = r[1:]
        clean_recipients.append(r)
    
    data = {
        "recipients": ",".join(clean_recipients),
        "message": message,
        "sender": "IntouchSMS", # Default sender ID
    }
    
    # Based on common usage of this API with tokens:
    # Some use it as a query param or in the body.
    # We'll try common parameters.
    
    params = {
        "token": token,
        "recipients": ",".join(clean_recipients),
        "message": message,
        "sender": "IntouchSMS"
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    
    import ssl
    context = ssl._create_unverified_context()
    
    try:
        req = urllib.request.Request(full_url, method="GET")
        with urllib.request.urlopen(req, context=context) as response:
            res_data = response.read().decode('utf-8')
            return json.loads(res_data)
    except Exception as e:
        print(f"SMS Send Error: {e}")
        return {"success": False, "error": str(e)}
