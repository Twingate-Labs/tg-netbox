import json
import requests
import ipaddress

netbox_url = "http://XXX.XXX.XXX.XXX/api"
twingate_url = "https://XXXXXXXXX.twingate.com/api/graphql/"
twingate_token = "XXXXXXXXXXXXXXX"
netbox_token = "XXXXXXXXXXX"

netbox_headers = {
    "Authorization": f"Token {netbox_token}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

twingate_headers = {
    'X-API-KEY': (twingate_token),
    'Content-Type': 'application/json',
    'Cookie': 'csrftoken=BfevZbn9nAsnJIekbalPWSfwbg1bSNIg'
}

# dictonary of the twingate api http bodies
body = {
    "resource": {
        "query": """
    query getResources {
        resources {
            edges {
                node {
                    id
                    name                    

                }
            }
        }
    }
    """
    },
    "group": {
        "query": """
        {
            groups(after: null, first:100) {
                edges {
                    node {
                        id
                        name
                        createdAt
                        updatedAt
                        isActive
                        type
                        users {
                            edges{
                                node{
                                    id
                                    email
                                    firstName
                                    lastName
                                }
                            }
                        }
                        
                    }
                }
                
            }
        }
    """
    },
    "network": {
        "query": """
        {
             remoteNetworks(after: null, first:100) {
                edges {
                    node {
                        id
                        name
                        createdAt
                        updatedAt
                    }
                }
                
            }
        }
    """
    }
}

# Get device with tag from netbox
netbox_response = requests.get(f"{netbox_url}/dcim/devices?tag=twingate", headers=netbox_headers)
if netbox_response.status_code == 200:
    netbox_data = json.loads(netbox_response.text)
else:
    print(f"Error getting devices from Netbox: {netbox_response.text}")


# Get Twingate resources
response = requests.post(twingate_url, json=body["resource"], headers=twingate_headers)
twingate_resources = [d['node'] for d in response.json()["data"]["resources"]["edges"]]

# Get Twingate groups
response = requests.post(twingate_url, json=body["group"], headers=twingate_headers)
twingate_groups = [d['node'] for d in response.json()["data"]["groups"]["edges"]]

# Get Twingate remote networks
response = requests.post(twingate_url, json=body["network"], headers=twingate_headers)
twingate_networks = [d['node'] for d in response.json()["data"]["remoteNetworks"]["edges"]]


for device in netbox_data['results']:
    device_name = device['name']
    device_ip = device['primary_ip']['address']
    tenant_name = device['tenant']['name']
    device_ip = ipaddress.IPv4Address(device_ip.split("/")[0])

    if device_name in [d['name'] for d in twingate_resources]:
        print(f"{device_name} is a Twingate resource already, skipping.")
        break

    group = [d for d in twingate_groups if tenant_name == d['name']]
    remote_network = [d for d in twingate_networks if tenant_name == d['name']]

    # confirm the group and remote network exist in Twingate
    if len(group) == 0:
        print(f"Group {tenant_name} not found in Twingate")
        if len(remote_network) == 0:
            print(f"RemoteNetworks {tenant_name} not found in Twingate")
        break

    query = f"""
        mutation {{
        resourceCreate(address:"{device_ip}", groupIds:"{group[0]["id"]}", name:"{device_name}", remoteNetworkId:"{remote_network[0]["id"]}")    
        {{
        error
        ok
        }}
        }}
        """

    response = requests.post(twingate_url, json={'query': query}, headers=twingate_headers)

    # Check for successful response from Twingate API
    response = json.loads(response.text)
    if response["data"][list(response["data"].keys())[0]]["ok"]:
        print(f"Successfully added device (Twingate resource) {device_name}.")
    else:
        print(f"Failed to add device (Twingate resource) {device_name}. Error: {response['data'][list(response['data'].keys())[0]]['error']}")

    print("Script Completed.")

