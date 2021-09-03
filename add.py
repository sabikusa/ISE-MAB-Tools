#!usr/bin/env python3

from datetime import datetime
import sys
import xml.dom.minidom
import requests
import urllib3


# USAGE: add.py aa:bb:cc:dd:ee:ff 00:11:22:33:44:55 repeat MAC as you wish
# as a disclaimer that the mac limit of argv is unknown as not tested yet


# disabling SSL error
urllib3.disable_warnings()

# URI to call API to
url = "https://pan_node:9060/ers/config/endpoint/bulk"

headers = {
  'Accept': 'application/xml',
  'Authorization': 'Basic your account',
  'Content-Type': 'application/xml'
}

today  datetime.today()
ymd = today.strftime('%y-%m-%d-%H%M')

def main():
    """ Function for Simple MAC registration """
    args = sys.argv
    payload = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><ns4:endpointBulkRequest operationType="create"\
    resourceMediaType="vnd.com.cisco.ise.identity.endpoint.1.0+xml" xmlns:ns4="identity.ers.ise.cisco.com" xmlns:xsi=\
        "http://www.w3.org/2001/XMLSchema-instance"><ns4:resourcesList>'
    payload2 = "</ns4:resourcesList></ns4:endpointBulkRequest>"
    for ise, arg in enumerate(args[1:]):
        ep = f"<ns4:endpoint><groupId>groupid</groupId><mac>{arg}</mac>\
            <staticGroupAssignment>true</staticGroupAssignment>\
            <staticProfileAssignment>false</staticProfileAssignment></ns4:endpoint>"
        payload += ep
        print('-' * 30)
        print('#{:02}'.format(ise))
        print('MAC:', arg)

    payload += payload2


    # calling an API to ISE with the parameter
    response = requests.put(url, headers = headers, data = payload, verify = False)

    # getting a bulk status based on the response header from ISE
    inquiry = requests.get(response.headers['Location'], headers = headers, verify = False)
    output = xml.dom.minidom.parseString(inquiry.text)
    prett = output.toprettyxml()
    with open(f'/directory/you/wanna/save_at/{ymd}_audit.log', 'w') as f:
        f.write(prett + f'\n\nRAN at {today}\n')
    print("-" * 30 + "\n" + str(datetime.now()) + "\nresponse_status = ", response.status_code, "\n")
    print(prett)

if __name__ == '__main__':
    main()
