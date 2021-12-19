#!

mport requests
import urllib3
import xml.dom.minidom
import argparse
import json

'''This script is simple API caller for MAC lookup to ISE'''

#disabling SSL error
urllib3.disable_warnings()

parser = argparse.ArgumentParser(description='MAC registration checker')
parser.add_argument('MAC', type=str, help='put MAC you wish to check')
arg = parser.parse_args()

url = 'https://PAN:9060/ers/config/endpoint/name/'
hdr = {
        'Accept': 'application/json',
        'Authorization': 'Basic ****',
        'Content-Type': 'application/json'
        }

url2 = 'https://szlnm189dha:9060/ers/config/identitygroup/'


def check(MAC):
    """ MAC lookup tool """
    try:
        res = requests.get(url + MAC, headers = hdr, verify = False)
        print('response code :', res.status_code, "\n")
        output = res.text
        joutput = json.loads(output)
        group = requests.get(url2 + joutput['ERSEndPoint']['groupId'], headers = hdr, verify = False)
        groupid = json.loads(group.text)
        name = groupid['IdentityGroup']['name']
        print(output, "\n")
        print("Identity Group : ", name)
    except json.decoder.JSONDecodeError:
        pass
    
if __name__ == '__main__':
    check(arg.MAC)
