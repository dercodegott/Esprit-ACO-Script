import requests
import json
import time
from discord_webhook import DiscordWebhook
import os
import sys
from bs4 import BeautifulSoup
from datetime import datetime


with open(os.path.join(sys.path[0], "config.json"), "r") as f:
    data = json.load(f)

headers = {'User-Agent': 'Mozilla/5.0'}
s=requests.Session()    
request_URL= data['request_URL']
product_URL= data['product_URL']
webhook_URL = data['Webhook']
instock_delay = data['instock_Delay']
oos_delay = data['OOS_Delay']
billing_email = data['billing_Email']
billing_country = data['billing_Country']
firstName = data['firstName']
lastName = data['lastName']
availability = False
dateimeObj = datetime.now()

atc_URL = 'https://www.esprit.at/on/demandware.store/Sites-EspritCentralHub-Site/de_AT/Cart-AddProduct'
submitBilling_URL = 'https://www.esprit.at/on/demandware.store/Sites-EspritCentralHub-Site/de_AT/CheckoutServices-SubmitBilling'
submitShipping_URL = 'https://www.esprit.at/on/demandware.store/Sites-EspritCentralHub-Site/de_AT/CheckoutShippingServices-SubmitShipping'
submitPayment_URL = "https://www.esprit.at/on/demandware.store/Sites-EspritCentralHub-Site/de_AT/CheckoutServices-SubmitPayment"
submitOrder_URL = 'https://www.esprit.at/on/demandware.store/Sites-EspritCentralHub-Site/de_AT/CheckoutServices-PlaceOrder'


def monitor():
    while availability == False:
        r = requests.get(request_URL)
        response = json.loads(r.text)
        stock = response['product']['inventoryRecord']
        if stock > 0:
            DiscordWebhook(webhook_URL, content= f"There are {stock} items left in stock.").execute()
            print(datetime.now(), f"There are {stock} items left in stock.")
            addToCart()
            break

        else:
            print("OOS")
            time.sleep(oos_delay)

def getCSRFToken():
    
    s.get(product_URL)
    soup = BeautifulSoup(s.get(product_URL).text, features="html.parser")
    csrf = soup.find("input", value=True)["value"] 
    return csrf

def getPid():
    r = requests.get(request_URL)
    response = json.loads(r.text)
    pid = response['product']['id']
    return pid


def addToCart():
        print(datetime.now(), ' Adding to Cart')
        payload = {'pid':getPid(), 'quantity': 2.0, 'csrf_token': getCSRFToken(), 'options': '[]'}
        x = s.post(atc_URL, data = payload)
        response = json.loads(x.text)
        cartChecker = response['cart']['numItems']
        global shipmentUUID
        shipmentUUID = response['cart']['items'][0]['shipmentUUID']
  
        if cartChecker > 0:
            print (datetime.now(), ' Going to checkout')
            checkout()

def checkout():
    billingData = {
    'shipmentUUID': shipmentUUID,
    'billingEmail': billing_email,
    'billingCountry': billing_country,
    'dwfrm_billing_addressFields_AT_firstName': firstName,
    'dwfrm_billing_addressFields_AT_lastName': lastName,
    'dwfrm_profile_customer_gender': '1',
    'dwfrm_profile_customer_birthday': '1999-01-01',
    'dwfrm_billing_contactInfoFields_email': billing_email,
    'dwfrm_billing_addressFields_AT_country': billing_country,
    'dwfrm_billing_addressFields_AT_address1':'test',
    'dwfrm_billing_addressFields_AT_houseNumber': '1',
    'dwfrm_billing_addressFields_AT_address2':'',
    'dwfrm_billing_addressFields_AT_postalCode': '4040',
    'dwfrm_billing_addressFields_AT_city': 'Linz',
    'csrf_token': getCSRFToken(),
    'localizedNewAddressTitle':'Neue Adresse'
    }
    print (datetime.now(), " Submitting Billing")
    submitBillingRequest=s.post(submitBilling_URL, data = billingData)
    response = json.loads(submitBillingRequest.text)

    if submitBillingRequest.status_code == 200:
        shippingData = {
            'originalShipmentUUID': shipmentUUID,
            'shipmentUUID': shipmentUUID,
            'dwfrm_shipping_shippingAddress_shippingMethodID': 'standardPostAT_AT',
            'csrf_token': getCSRFToken()
        }
        submitShippingRequest= s.post(submitShipping_URL, data = shippingData)
        response = json.loads(submitShippingRequest.text)
        print(datetime.now(), " Submitting Shipping")

    if submitShippingRequest.status_code == 200:
        paymentData = {
            'csrf_token': getCSRFToken(),
            'payment-method': 'PAYPAL',
            'dwfrm_billing_giftcard_cardnumber':'',
            'dwfrm_billing_giftcard_pin':'',
            'dwfrm_billing_paymentMethod': 'PAYPAL'
        }
        print(datetime.now(), " Submitting Payment")
        paymentRequest = s.post(submitPayment_URL, data = paymentData)
        response = json.loads(paymentRequest.text)
    
    if paymentRequest.status_code == 200:
        submitOrder = s.post(submitOrder_URL)
        response = json.loads(submitOrder.text)
        paypalLink = response['continueUrl']
        print(datetime.now(), ' Checkout Successful')
        DiscordWebhook(webhook_URL, content= paypalLink).execute()

monitor()