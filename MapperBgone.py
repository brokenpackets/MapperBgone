#!/usr/bin/env python
import requests
import json

###### User Variables

username = 'admin'
password = 'Arista123'
server1 = 'https://192.168.255.50'
dryrun = True

configlet_blacklist = ['LAB_VXLAN-Activate',]

###### Do not modify anything below this line. Or do, I'm not a cop.
connect_timeout = 10
headers = {"Accept": "application/json",
           "Content-Type": "application/json"}
requests.packages.urllib3.disable_warnings()
session = requests.Session()

def login(url_prefix, username, password):
    authdata = {"userId": username, "password": password}
    headers.pop('APP_SESSION_ID', None)
    response = session.post(url_prefix+'/web/login/authenticate.do', data=json.dumps(authdata),
                            headers=headers, timeout=connect_timeout,
                            verify=False)
    cookies = response.cookies
    headers['APP_SESSION_ID'] = response.json()['sessionId']
    if response.json()['sessionId']:
        return response.json()['sessionId']

def logout(url_prefix):
    response = session.post(url_prefix+'/web/login/logout.do')
    return response.json()

def get_inventory(url_prefix):
    response = session.get(url_prefix+'/cvpservice/inventory/devices')
    if response.json():
        return response.json()

def get_configlets_by_device(url_prefix,deviceMac):
    response = session.get(url_prefix+'/cvpservice/provisioning/getConfigletsByNetElementId.do?netElementId='+deviceMac+'&startIndex=0&endIndex=0')
    return response.json()

def get_configlet_by_name(url_prefix,configletname):
    response = session.get(url_prefix+'/cvpservice/configlet/getConfigletByName.do?name='+configletname)
    return response.json()

def search_configlets(url_prefix,configlets_to_remove):
    configletKeys = {}
    for configletname in configlets_to_remove:
        response = session.get(url_prefix+'/cvpservice/configlet/searchConfiglets.do?type=static&queryparam='+configletname+'&startIndex=0&endIndex=0')
        configletInfo = response.json()['data'][0]
        configletKeys.update({configletInfo['name']:configletInfo['key']})
    return configletKeys

def get_temp_configs(url_prefix,nodeId):
    response = session.get(url_prefix+'/cvpservice/provisioning/getTempConfigsByNetElementId.'
                                      'do?netElementId='+nodeId)
    return response.json()

def save_topology(url_prefix):
    response = session.post(url_prefix+'/cvpservice/provisioning/v2/saveTopology.do', data=json.dumps([]))
    return response.json()

def apply_configlets(url_prefix,nodeName,nodeIp,deviceMac,cnames,ckeys,igConfigletNames,igConfigletKeys):
    # Remove the blacklisted configlets from the arrays.
    info = 'MapperBgone: Removing configlets from: '+nodeName
    info_preview = '<b>Configlet Removal:</b> from Device '+nodeName
    tempData = json.dumps({
        'data': [{'info': info,
                  'infoPreview': info_preview,
                  'note': '',
                  'action': 'associate',
                  'nodeType': 'configlet',
                  'nodeId': '',
                  'configletList': ckeys,
                  'configletNamesList': cnames,
                  'ignoreConfigletNamesList': igConfigletNames,
                  'ignoreConfigletList': igConfigletKeys,
                  'configletBuilderList': [],
                  'configletBuilderNamesList': [],
                  'ignoreConfigletBuilderList': [],
                  'ignoreConfigletBuilderNamesList': [],
                  'toId': deviceMac,
                  'toIdType': 'netelement',
                  'fromId': '',
                  'nodeName': '',
                  'fromName': '',
                  'toName': nodeName,
                  'nodeIpAddress': nodeIp,
                  'nodeTargetIpAddress': nodeIp,
                  'childTasks': [],
                  'parentTask': ''}]})

    response = session.post(url_prefix+'/cvpservice/ztp/addTempAction.do?format=topology&queryParam=&nodeId=root', data=tempData)
    #return tempData
    return response.json()

print '###### Logging into Server 1'
login(server1, username, password)
print '###### Getting list of devices'
allDevices = get_inventory(server1)
configlets_to_remove = search_configlets(server1, configlet_blacklist)
print configlets_to_remove
for device in allDevices:
    nodeName = device['fqdn']
    nodeId = device['systemMacAddress']
    nodeIp = device['ipAddress']
    configlets = get_configlets_by_device(server1, nodeId)
    cnames = []
    ckeys = []
    try:
        for configlet in configlets['configletList']:
            cnames.append(configlet['name'])
            ckeys.append(configlet['key'])
        for item in configlets_to_remove.keys():
            if item in cnames:
                cnames.remove(item)
                print 'Removing Configlet '+item+' from '+nodeName
                for item in configlets_to_remove.values():
                    if item in ckeys:
                        ckeys.remove(item)
                if dryrun == False:
                    output = apply_configlets(server1,nodeName,nodeIp,nodeId,cnames,ckeys,configlets_to_remove.keys(),configlets_to_remove.values())
                    print output
                    save = save_topology(server1)
    except:
        print "failure on "+nodeName
        pass
logout(server1)
print '##### Complete'
