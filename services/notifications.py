import logging

logger = logging.getLogger(__name__)

def send_sms(phone: str, message: str):
    """
    Simulation Mode: Prints the SMS directly to the backend terminal.
    """
    print(f"\n" + "═"*50)
    print(f"📱 NEW SMS NOTIFICATION TRIGGERED")
    print(f"═"*50)
    print(f"To:      +91 {phone}")
    print(f"From:    CityShakti Notifications (VMID: NIC-SMS)\n")
    print(f"Message  |\n         | {message}")
    print("═"*50 + "\n")


def send_email(email: str, subject: str, message: str):
    """
    Simulation Mode: Prints the Email directly to the backend terminal
    with simulated Rich HTML formatting.
    """
    print(f"\n" + "═"*70)
    print(f"📧 NEW EMAIL DISPATCHED")
    print(f"═"*70)
    print(f"To:      {email}")
    print(f"From:    no-reply@cityshakti.gov.in")
    print(f"Subject: {subject}\n")
    print(f"---------------------- HTML MESSAGE BODY ----------------------")
    print(f"|")
    print(f"| CITYSHAKTI - Smart Civic Monitoring")
    print(f"|")
    for line in message.split('\\n'):
        print(f"| {line}")
    print(f"|")
    print(f"| This is an automated notification. Do not reply.")
    print(f"| _Secured by National Informatics Centre (NIC)_")
    print(f"---------------------------------------------------------------")
    print("═"*70 + "\n")

