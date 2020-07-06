#By PWRScript, all code linked to stackoverflow, code adapted from mpontillo github and portmapper from kaklakariada github belongs to their owners

#UPnP Methods (for portmapper)
SBBI = "org.chris.portmapper.router.sbbi.SBBIRouterFactory"
WEUPNP = "org.chris.portmapper.router.weupnp.WeUPnPRouterFactory"
CLING = "org.chris.portmapper.router.cling.ClingRouterFactory"
DUMMY_DISCOURAGED = "org.chris.portmapper.router.dummy.DummyRouterFactory"

#Config (Modify to your needs)
RUN_TYPE = 1 # 0 - Interactive Mode, 1 - Smart Mode (Opens ports if minecraft server running, closes inactive open ports)

NOTIFICATIONS_TIMEOUT = 5
NOTIFICATIONS_THREADED = False

PORTMAPPER_USE_LIB = SBBI #Change this if ports are not been open (You can test what lib works for you testing opening portmapper.jar)

LAN_AUTOSCAN_DETECTION_TIME = 6.5 #Time to scan for a minecraft lan packet annoucing the server
LAN_FALLBACK_MODE = False #if your PC can't detect your lan minecraft server turn this to True (close any dedicated server first)

DEDICATED_SERVER_CHECK_PORTS = [25565] # Ports to check for dedicated servers (example: [25565,40000,55689])

DEDICATED_SERVER_UPnP_PORT = 52050 # Port to open via UPnP on router for dedicated servers (example: 52050)
LAN_SERVER_UPnP_PORT = 62050 # Port to open via UPnP on router for lan servers (example: 62050)

#Imported Libraries
import socket,struct,time,select,re,subprocess,pip._vendor.requests as requests, clipboard
from win10toast import ToastNotifier
from mcstatus import MinecraftServer
from colorama import init, Fore
from time import sleep

#Function on https://stackoverflow.com/a/28950776
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

#Implemented from https://github.com/mpontillo/minecraft-lan-announce/blob/master/listen.py (Base code by mpontillo)
def method_locate_local_lan_server():
    port = 4445
    bufferSize = 1500
    timeout = LAN_AUTOSCAN_DETECTION_TIME
    MCAST_GRP = "224.0.2.60"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    s.bind(('', port))
    servers = set()
    server_list = []
    start_time = time.time()
    s.setblocking(0)
    while True:
        current_time = time.time()
        (read, written, exceptions) = select.select([s], [], [s], 0.5)
        for r in read:
            msg, peer = r.recvfrom(bufferSize)
            address = peer[0]
            matches = re.findall(r'\[MOTD\](.+?)\[/MOTD\]\[AD\](\d+)\[/AD\]', msg.decode())
            for title, port in matches:
                server = f"{address}:{port}"
                serverz = {"address": address, "port": port, 'title': repr(title)}
                if server not in servers:
                    servers.add(server)
                    server_list.append(serverz)
        if len(exceptions) > 0 or current_time < start_time:
            detected_servers = server_list
            break
        if current_time >= start_time + timeout:
            detected_servers = server_list
            break
    for server in detected_servers:
        if server["address"].startswith(get_ip()) == True:
            return server

def method_locate_local_dedicated_server():
    for port in DEDICATED_SERVER_CHECK_PORTS:
        server = MinecraftServer.lookup(f'{get_ip()}:{port}')
        try:
            info = server.status()
        except:
            pass
        else:
            return {"address" : server.host,"port":server.port,'title': repr(info.description)}

#Core Functions
def get_servers_running():
    print("Trying to detect server automatically (Lan Server Method)... ".center(40), end="")
    method_1_result = method_locate_local_lan_server()
    print(Fore.GREEN + f"Found at {method_1_result['address']}:{method_1_result['port']}" + Fore.RESET if method_1_result != None else Fore.RED + "Failed (or maybe your connection type is set to public)" + Fore.RESET)

    print("Trying to detect server automatically (Dedicated Server Method)... ".center(40), end="")
    method_2_result = method_locate_local_dedicated_server()
    print(Fore.GREEN + f"Found at {method_2_result['address']}:{method_2_result['port']}" + Fore.RESET if method_2_result != None else Fore.RED + "Failed (or maybe running on other port than defined in configuration?)" + Fore.RESET)
    return method_1_result,method_2_result

def get_minecraft_upnp_status():
    MyOut = subprocess.Popen(['java', '-jar', 'portmapper.jar', '-lib', PORTMAPPER_USE_LIB, '-list'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    stdout, stderr = MyOut.communicate()
    dedicated_server_enabled = False
    lan_server_enabled = False
    for info in stdout.splitlines(keepends=False):
        if (info.startswith(b"UDP") or info.startswith(b"TCP")):
            if info.split()[0] == b"TCP" and str(info.split()[1]) == f"b':{DEDICATED_SERVER_UPnP_PORT}'":
                dedicated_server_enabled = True
            elif info.split()[0] == b"TCP" and str(info.split()[1]) == f"b':{LAN_SERVER_UPnP_PORT}'":
                lan_server_enabled = True
    return lan_server_enabled, dedicated_server_enabled

def enable_minecraft_upnp(open_type:str,lan_minecraft_port=25565 , server_minecraft_port=25565):
    if open_type.lower() == "lan":
        MyOut = subprocess.Popen(['java', '-jar', 'portmapper.jar', '-lib', PORTMAPPER_USE_LIB, '-add', "-externalPort", str(LAN_SERVER_UPnP_PORT), "-internalPort", str(lan_minecraft_port), "-protocol", "tcp", "-description", "Minecraft Lan Server PWR"],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        MyOut.communicate()
    elif open_type.lower() == "dedicated":
        MyOut = subprocess.Popen(['java', '-jar', 'portmapper.jar', '-lib', PORTMAPPER_USE_LIB, '-add', "-externalPort",str(DEDICATED_SERVER_UPnP_PORT), "-internalPort", str(server_minecraft_port), "-protocol", "tcp","-description", "Minecraft Dedicated Server PWR"], stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        MyOut.communicate()
    elif open_type.lower() == "all":
        MyOut = subprocess.Popen(['java', '-jar', 'portmapper.jar', '-lib', PORTMAPPER_USE_LIB, '-add', "-externalPort",str(LAN_SERVER_UPnP_PORT), "-internalPort", str(lan_minecraft_port), "-protocol", "tcp","-description", "Minecraft Lan Server PWR"], stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        MyOut.communicate()
        MyOut = subprocess.Popen(['java', '-jar', 'portmapper.jar', '-lib', PORTMAPPER_USE_LIB, '-add', "-externalPort",str(DEDICATED_SERVER_UPnP_PORT), "-internalPort", str(server_minecraft_port), "-protocol", "tcp","-description", "Minecraft Dedicated Server PWR"],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        MyOut.communicate()

def disable_minecraft_upnp(close_type:str):
    if close_type.lower() == "lan":
        MyOut = subprocess.Popen(['java', '-jar', 'portmapper.jar', '-lib', PORTMAPPER_USE_LIB, '-delete', "-externalPort",str(LAN_SERVER_UPnP_PORT), "-protocol", "tcp"], stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        MyOut.communicate()
    elif close_type.lower() == "dedicated":
        MyOut = subprocess.Popen(['java', '-jar', 'portmapper.jar', '-lib', PORTMAPPER_USE_LIB, '-delete', "-externalPort",str(DEDICATED_SERVER_UPnP_PORT), "-protocol", "tcp"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        MyOut.communicate()
    elif close_type.lower() == "all":
        MyOut = subprocess.Popen(['java', '-jar', 'portmapper.jar', '-lib', PORTMAPPER_USE_LIB, '-delete', "-externalPort",str(LAN_SERVER_UPnP_PORT), "-protocol", "tcp" ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        MyOut.communicate()
        MyOut = subprocess.Popen(['java', '-jar', 'portmapper.jar', '-lib', PORTMAPPER_USE_LIB, '-delete', "-externalPort",str(DEDICATED_SERVER_UPnP_PORT), "-protocol", "tcp" ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        MyOut.communicate()


if __name__ == '__main__':
    init()
    print(Fore.GREEN + '*' * 40 + Fore.RESET)
    print(Fore.GREEN + '*' + Fore.RESET + "PWRUPnPMineExpose".center(38) + Fore.GREEN + '*' + Fore.RESET)
    print(Fore.GREEN + '*' + Fore.RESET + "by PWRScript, Version 0.02".center(38) + Fore.GREEN + '*' + Fore.RESET)
    print(Fore.GREEN + '*' * 40 + Fore.RESET)
    sleep(1)
    toast = ToastNotifier()
    if RUN_TYPE == 0:
        #Interactive Mode
        pass

    elif RUN_TYPE == 1:
        #Opens ports if minecraft server running, closes inactive open ports
        method_1_result, method_2_result = get_servers_running()
        if method_1_result == None and method_2_result == None:
            port_temp = 0
            if LAN_FALLBACK_MODE == True:
                toast.show_toast("PWRUPnPMineExpose [LAN_FALLBACK_MODE]","We need your attention because you enabled LAN_FALLBACK_MODE and we can´t detect any server running on your computer", duration=NOTIFICATIONS_TIMEOUT, threaded=NOTIFICATIONS_THREADED)

                while not port_temp == None or port_temp != 0:
                    c = input("In which port are your minecraft lan server (leave blank if you not have any server open)? ")

                    try:
                        if c.strip() == "" or c.lower() == "none":
                            port_temp = None
                            disable_minecraft_upnp("all")
                            toast.show_toast("PWRUPnPMineExpose [DESACTIVE]","All minecraft server port forwarding roles was disabled from the router", duration=NOTIFICATIONS_TIMEOUT, threaded=NOTIFICATIONS_THREADED)
                            break

                        else:
                            port_temp = int(c)
                            if port_temp == 0 or port_temp > 65535:
                                raise ValueError
                            else:
                                enable_minecraft_upnp("lan", port_temp)
                                print(Fore.GREEN + '*' * 40 + Fore.RESET)
                                print(Fore.GREEN + '*' + Fore.RESET + f"Lan Server:{requests.get('https://api.ipify.org').text}:{LAN_SERVER_UPnP_PORT}".center(38) + Fore.GREEN + '*' + Fore.RESET)
                                print(Fore.GREEN + '*' * 40 + Fore.RESET)
                                toast.show_toast("PWRUPnPMineExpose [LAN]","Lan minecraft server port forwarding roles was enabled from the router", duration=NOTIFICATIONS_TIMEOUT, threaded=NOTIFICATIONS_THREADED)
                                clipboard.copy("*" * 40 + "\n" + "*" + "PWRUPnPMineExpose by PWRScript".center(38) + "*" + "\n" + "*" + f"Lan Server: {requests.get('https://api.ipify.org').text}:{LAN_SERVER_UPnP_PORT}".center(38) + "*" + "\n" + "*" * 40)
                                break

                    except ValueError:
                        print(Fore.RED + f"Error: Value must be a port between 1 and 65535 or None"+ Fore.RESET)
            else:
                disable_minecraft_upnp("all")
                toast.show_toast("PWRUPnPMineExpose [DESACTIVE]","All minecraft server port forwarding roles was disabled from the router", duration=NOTIFICATIONS_TIMEOUT, threaded=NOTIFICATIONS_THREADED)

        elif method_1_result != None and method_2_result != None:
            enable_minecraft_upnp("all",int(method_1_result["port"]),int(method_2_result["port"]))
            print(Fore.GREEN + '*' * 40 + Fore.RESET)
            print(Fore.GREEN + '*' + Fore.RESET + f"Dedicated Server: {requests.get('https://api.ipify.org').text}:{DEDICATED_SERVER_UPnP_PORT}".center(38) + Fore.GREEN + '*' + Fore.RESET)
            print(Fore.GREEN + '*' + Fore.RESET + f"Lan Server:{requests.get('https://api.ipify.org').text}:{LAN_SERVER_UPnP_PORT}".center(38) + Fore.GREEN + '*' + Fore.RESET)
            print(Fore.GREEN + '*' * 40 + Fore.RESET)
            toast.show_toast("PWRUPnPMineExpose [ACTIVE]", "All minecraft server port forwarding roles was enabled from the router", duration=NOTIFICATIONS_TIMEOUT, threaded=NOTIFICATIONS_THREADED)
            clipboard.copy("*" * 40 + "\n" + "*" + "PWRUPnPMineExpose by PWRScript".center(38) + "*" + "\n" + "*" + f"Lan Server: {requests.get('https://api.ipify.org').text}:{LAN_SERVER_UPnP_PORT}".center(38) + "*" + "\n"+ "*" + f"Dedicated Server: {requests.get('https://api.ipify.org').text}:{DEDICATED_SERVER_UPnP_PORT}".center(38) + "*" + "\n" + "*" * 40)

        elif method_1_result != None:
            enable_minecraft_upnp("lan", int(method_1_result["port"]))
            disable_minecraft_upnp("dedicated")
            print(Fore.GREEN + '*' * 40 + Fore.RESET)
            print(Fore.GREEN + '*' + Fore.RESET + f"Lan Server:{requests.get('https://api.ipify.org').text}:{LAN_SERVER_UPnP_PORT}".center(38) + Fore.GREEN + '*' + Fore.RESET)
            print(Fore.GREEN + '*' * 40 + Fore.RESET)
            toast.show_toast("PWRUPnPMineExpose [LAN]","Lan minecraft server port forwarding roles was enabled from the router", duration=NOTIFICATIONS_TIMEOUT, threaded=NOTIFICATIONS_THREADED)
            clipboard.copy("*" * 40 + "\n" + "*" + "PWRUPnPMineExpose by PWRScript".center(38) + "*" + "\n" + "*" + f"Lan Server: {requests.get('https://api.ipify.org').text}:{LAN_SERVER_UPnP_PORT}".center(38) + "*" + "\n" + "*" * 40)

        elif method_2_result != None:
            enable_minecraft_upnp("dedicated", int(method_2_result["port"]), int(method_2_result["port"]))
            disable_minecraft_upnp("lan")
            print(Fore.GREEN + '*' * 40 + Fore.RESET)
            print(Fore.GREEN + '*' + Fore.RESET + f"Dedicated Server: {requests.get('https://api.ipify.org').text}:{DEDICATED_SERVER_UPnP_PORT}".center(38) + Fore.GREEN + '*' + Fore.RESET)
            print(Fore.GREEN + '*' * 40 + Fore.RESET)
            toast.show_toast("PWRUPnPMineExpose [DEDICATED]","Dedicated minecraft server port forwarding roles was enabled from the router", duration=NOTIFICATIONS_TIMEOUT, threaded=NOTIFICATIONS_THREADED)
            clipboard.copy("*" * 40 + "\n" + "*" + "PWRUPnPMineExpose by PWRScript".center(38) + "*" + "\n" + "*" + f"Dedicated Server: {requests.get('https://api.ipify.org').text}:{DEDICATED_SERVER_UPnP_PORT}".center(38) + "*" + "\n" + "*" * 40)
    input("Press enter to continue... ")
    quit(0)
