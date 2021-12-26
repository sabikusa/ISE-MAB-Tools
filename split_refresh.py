#!/usr/bin/env python3

import requests
import urllib3
import urllib.request
import uuid
import json
import re
import logging
from glob import glob
import os
import datetime
from netmiko import ConnectHandler
from getpass import getpass

if os.path.isfile('run.log'):
    os.remove('run.log')
logging.basicConfig(filename='run.log', level=logging.DEBUG)
logger = logging.getLogger("netmiko")

# disabling SSL error
urllib3.disable_warnings()

def print_acl_lines(acl_name, ips, section_comment):
    slash_to_mask = (
        "0.0.0.0",
        "128.0.0.0",
        "192.0.0.0",
        "224.0.0.0",
        "240.0.0.0",
        "248.0.0.0",
        "252.0.0.0",
        "254.0.0.0",
        "255.0.0.0",
        "255.128.0.0",
        "255.192.0.0",
        "255.224.0.0",
        "255.240.0.0",
        "255.248.0.0",
        "255.252.0.0",
        "255.254.0.0",
        "255.255.0.0",
        "255.255.128.0",
        "255.255.192.0",
        "255.255.224.0",
        "255.255.240.0",
        "255.255.248.0",
        "255.255.252.0",
        "255.255.254.0",
        "255.255.255.0",
        "255.255.255.128",
        "255.255.255.192",
        "255.255.255.224",
        "255.255.255.240",
        "255.255.255.248",
        "255.255.255.252",
        "255.255.255.254",
        "255.255.255.255",
    )
    print(
        "access-list {acl_name} remark {comment}".format(
            acl_name=acl_name, comment=section_comment
        )
    )
    post.write("access-list {acl_name} remark {comment}\n".format(
        acl_name=acl_name, comment=section_comment
        )
    )
    for ip in sorted(ips):
        if ":" in ip:
            # IPv6 address
            print(
                "access-list {acl_name} extended permit ip {ip} any6".format(
                    acl_name=acl_name, ip=ip
                )
            )
            post.write("access-list {acl_name} extended permit ip {ip} any6\n".format(
                acl_name=acl_name, ip=ip)
            )

        else:
            # IPv4 address.  Convert to a mask
            addr, slash = ip.split("/")
            slash_mask = slash_to_mask[int(slash)]
            print(
                "access-list {acl_name} extended permit ip {addr} {mask} any4".format(
                    acl_name=acl_name, addr=addr, mask=slash_mask
                )
            )
            post.write("access-list {acl_name} extended permit ip {addr} {mask} any4\n".format(
                acl_name=acl_name, addr=addr, mask=slash_mask
                )
            )


# Fetch the current endpoints for O365
http_res = urllib.request.urlopen(
    url="https://endpoints.office.com/endpoints/worldwide?clientrequestid={}".format(
        uuid.uuid4()
    )
)
res = json.loads(http_res.read())
o365_ips = set()
o365_fqdns = set()
for service in res:
    if (service["category"] == "Optimize" and service["serviceArea"] == "SharePoint") or (service["category"] == "Optimize" and service["serviceArea"] == "Skype"):
        for ip in service.get("ips", []):
            o365_ips.add(ip)
        for fqdn in service.get("urls", []):
            o365_fqdns.add(fqdn)

# Composing ACLs to be pushed
post = open('splits_acl2.txt', 'w')

# Generate an acl for split excluding For instance
print("##### Step 1: Create an access-list to include the split-exclude networks\n")
acl_name = "Split-Tunnel-List"
# O365 networks
print_acl_lines(
    acl_name=acl_name,
    ips=o365_ips,
    section_comment="v4 and v6 networks for Microsoft Office 365",
    )
# Microsoft Teams
# https://docs.microsoft.com/en-us/office365/enterprise/office-365-vpn-implement-split-tunnel#configuring-and-securing-teams-media-traffic
print_acl_lines(
    acl_name=acl_name,
    ips=["13.107.60.1/32"],
    section_comment="v4 address for Microsoft Teams"
    )
# Cisco Webex - Per https://help.webex.com/en-us/WBX000028782/Network-Requirements-for-Webex-Teams-Services
webex_url = 'https://help.webex.com/en-us/WBX000028782/Network-Requirements-for-Webex-Teams-Services'
webex = requests.get(webex_url, verify=False)
webex_body = webex.text
wip1 = re.findall('\d+[.]\d+[.]\d+[.]\d+[/]\d+', webex_body)
webex_ips = list(set(wip1))

print_acl_lines(
    acl_name=acl_name,
    ips=webex_ips,
    section_comment="IPv4 and IPv6 destinations for Cisco Webex",
)

zourl = 'https://assets.zoom.us/docs/ipranges/ZoomMeetings.txt'
zoom = requests.get(zourl, verify=False)
zoom_ips = zoom.text
with open('zoom_ips.txt', 'w') as f:
    f.write(zoom_ips)

print_acl_lines(
    acl_name=acl_name,
    ips= open('zoom_ips.txt'),
    section_comment="IPv4 for Zoom meeting"
)


# Edited. April 1st 2020
# Per advice from Microsoft they do NOT advise using dynamic split tunneling for their properties related to Office 365
#
print(
    "\n\n##### Step 2: Create an Anyconnect custom attribute for dynamic split excludes\n"
)
print("SKIP.  Per Microsoft as of April 2020 they advise not to dynamically split fqdn related to Office365")
#print(
#    """
#webvpn
#  anyconnect-custom-attr dynamic-split-exclude-domains description dynamic-split-exclude-domains
#
#anyconnect-custom-data dynamic-split-exclude-domains saas {}
#""".format(
#        ",".join([re.sub(r"^\*\.", "", f) for f in o365_fqdns])
#    )
#)
#

# Closing the file
post.close()

endstate = glob('splits*.txt')
endstate.sort()


if os.path.isfile('esacl.txt'):
    os.remove('esacl.txt')

with open('esacl.txt', 'w') as outfile:
    for file in endstate:
        with open(file) as infile:
            outfile.write(infile.read())

    outfile.write('\n')



print("\n##### Step 3: Push the latest ACL shown above plus Kaltura/Adaptiva for the split exclude in the group-policy on ASAs\n")


user_name = input("Enter your username to SSH: ")
pwd = getpass()
secret = getpass(prompt = 'Enable password:')

device1 = {
    'device_type': 'cisco_asa',
    'host': 'x.x.x.x',
    'username': user_name,
    'password': pwd,
    'secret': secret
}
device2 = {
    'device_type': 'cisco_ios',
    'host': 'x.x.x.x',
    'username': user_name,
    'password': pwd,
    'secret': secret
}
device3 = {
    'device_type': 'cisco_asa',
    'host': 'x.x.x.x',
    'username': user_name,
    'password': pwd,
    'secret': secret
}
device4 = {
    'device_type': 'cisco_asa',
    'host': 'x.x.x.x',
    'username': user_name,
    'password': pwd,
    'secret': secret
}

ASA = [device1, device2, device3, device4]
acl = 'esacl.txt'
today = datetime.datetime.today()
ymd = today.strftime('%y-%m-%d-%H%M')

def main():
    ''' this function acts swapping the ACL with latest one generated in the script '''
    for i in ASA:
        net_connect = ConnectHandler(**i)
        try:
            print('Pushing the latest ACL...')
            output = net_connect.send_config_from_file(acl)
            net_connect.save_config()
            with open(f'/derectory/you/wishtosaveat/{ymd}_audit.log', 'a') as f:
                f.write(output + f'\n\nRAN at {today}\n')
            print(f'{net_connect.find_prompt()} === > OK')
            net_connect.disconnect()
        except:
            print('Skipping this target due to a login failure...\n')
            net_connect.disconnect()
            continue



if __name__ == '__main__':
    main()

print('''

         FINISH        
        
''')
print(today)
