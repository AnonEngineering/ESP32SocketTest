# PyPortal Socket test
# Uses ESP32 to establish a socket to a TCP port
# 
# Anon Engineering April 2020

import gc
import time
import board
import displayio
import busio
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_requests as requests
import adafruit_esp32spi_socket
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from digitalio import DigitalInOut
import adafruit_hashlib as hashlib
import json
# Get wifi details and other creds from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi credentials are kept in secrets.py.")
    print("Please create the file or add to the existing one.")
    raise

# Constants-----------------
WLAN_AP_ID = secrets["ssid"]
WLAN_AP_PW = secrets["password"]
WLAN_PJ_IP = '192.168.1.207' # Device LAN address
WLAN_PJ_PW = 'Projector1'   # Device PW
# Default ADCP port is 53595
ADCP_PORT = 53595

# Commands ---------------------------------------------------------------------------- #
# Needs CR + LF, either \x0D\x0A or \r\n
CMD_MOD =       (b'modelname ?\r\n')
CMD_SN =        (b'serialnum ?\r\n')
CMD_TIM =       (b'timer ?\r\n')
CMD_PWR_STS =   (b'power_status ?\r\n')
CMD_IN_STS =    (b'input ?\r\n')
CMD_VER =       (b'version ?\r\n')
CMD_ON =        (b'power \"on\"\r\n')
CMD_OFF =       (b'power \"off\"\r\n')
CMD_MENU =      (b'key \"menu\"\r\n')
CMD_RET =       (b'key \"return\"\r\n')
CMD_UP =        (b'key \"up\"\r\n')
CMD_DN =        (b'key \"down\"\r\n')
CMD_LEFT =      (b'key \"left\"\r\n')
CMD_RIGHT =     (b'key \"right\"\r\n')
CMD_ENT =       (b'key \"enter\"\r\n')
CMD_BLANK =     (b'key \"blank\"\r\n')
CMD_MUTE =      (b'key \"muting\"\r\n')
CMD_PTN =       (b'key \"pattern\"\r\n')
CMD_IN_A =      (b'key \"input_a\"\r\n')
CMD_IN_B =      (b'key \"input_b\"\r\n')
CMD_IN_C =      (b'key \"input_c\"\r\n')
CMD_IN_D =      (b'key \"input_d\"\r\n')
CMD_IN_N =      (b'input \"network\"\r\n')

# Functions ----------------------------------------------------------------------------#
def open_socket():
    # If socket connects then we should get NOKEY or 4 byte hash key
    print("In open_socket")
    print(esp.socket_status(0))
    #print(cmd_socket.connected())
    try:
        # sockaddr is 32 bit packed IP address
        sockaddr = socket.getaddrinfo(WLAN_PJ_IP, ADCP_PORT)[0][-1] # VPL Client mode
        cmd_socket.connect(sockaddr)
        print(esp.socket_status(0))
    except RuntimeError as e:
        print("In open_socket err, ", e)
    print()
    # Give the socket time to connect before readline in auth_check ## ESP32 reliability??? ##
    time.sleep(.1)

def close_socket():
    print("In close_socket")
    try:
        #print("Connected = ", cmd_socket.connected())
        #print("Closing socket")
        cmd_socket.close()
        #print("Connected = ", cmd_socket.connected())
    except RuntimeError as e:
        print("In close_socket err, ", e)
    print()

def auth_check():
    print("In auth_check")
    #esp.socket_status(0)
    try:
        adcp_hash = cmd_socket.readline()
        print(adcp_hash)
        if adcp_hash == (b'NOKEY'):
            print('Authentication is off.')
        else:
            print('Authentication is on.')
            adcp_hash = (adcp_hash + WLAN_PJ_PW)
            print('Hash key is: \t', adcp_hash.decode("utf-8"))
            sha_hash = gen_hash(adcp_hash)
            print('SHA256 hash is ', sha_hash)
            cmd_socket.send(sha_hash + '\r\n')
            time.sleep(.1)  # Need time between send and readline?  ## ESP32 reliability??? ##
            try:
                answer = cmd_socket.readline()  
                if answer == b'OK':
                    print("Authentication suceeded")
                else:
                    print("Authentication error!")
            except RuntimeError as e:
                print("Send hash err, ", e)
    except RuntimeError as e:
            print("Read hash err, ", e)
    print()
    
def gen_hash(auth_string):  # SHA-256
    # Create hash object
    sha_hash = hashlib.sha256()
    # Update the hash object with auth_string
    sha_hash.update(auth_string)
    return sha_hash.hexdigest()

def send_command(selected_cmd):
    print("In send_command")
    if cmd_socket.connected():  # Fails if socket couldn't be opened
        time.sleep(.1)  ## ESP32 reliability???##
        try:
            print("Sending ", selected_cmd, "to", WLAN_PJ_IP)
            cmd_socket.send(selected_cmd)
            time.sleep(.1)  ## ESP32 reliability??? ##
            adcp_reply = cmd_socket.readline()
            time.sleep(.1)  ## ESP32 reliability??? ##
            print(adcp_reply)
            return adcp_reply
        except (AttributeError, RuntimeError) as e:
            print("send_command err: ", e)
    print()

def get_status():
    print("In get_status")
    try:
        answer = send_command(CMD_MOD)
        print(answer.decode("utf-8").strip('"'))
        answer = send_command(CMD_SN)
        print(answer.decode("utf-8").strip('"'))
        # Parse JSON
        answer = send_command(CMD_TIM)
        try:
            jtest = json.loads(answer)   # jtest is list of dicts, load is binary, loads is string
            ops_time = jtest[0]["operation"]
            lite_time = jtest[1]["light_src"]
            print("Ops Time: \t", ops_time)
            print("Lite Time:  ", lite_time)
        except (RuntimeError, TypeError, ValueError) as e:
            print(e)
        except IndexError as i:
            # Index doesn't exist, skip it.
            print("Index error - no entry for key, skip it.")
        # Parse JSON
        answer = send_command(CMD_VER)
        try:
            jtest = json.loads(answer)   # jtest is list of dicts, load is binary, loads is string
            main_rom = jtest[0]["main"]
            print("Main ROM: ", main_rom)
            nvm_rom = jtest[1]["main_data"]
            print("NVM ROM:  ", nvm_rom)
            sub_rom = jtest[2]["sub"]
            print("Sub ROM:  ", sub_rom)
            ext_rom = jtest[3]["ext"]
            print("EXT ROM:  ", ext_rom)
        except (RuntimeError, TypeError, ValueError) as e:
            print(e)
        except IndexError as i:
            # Index doesn't exist, skip it.
            print("Index error - no entry for key, skip it.")
        answer = send_command(CMD_IN_STS)
        print(answer.decode("utf-8").upper().strip('"'))
        answer = send_command(CMD_PWR_STS)
        print(answer.decode("utf-8").upper().strip('"'))
    except (AttributeError, RuntimeError) as e:
        print("In get_status err, ", e)
    print()

# Setup ESP32 --------------------------------------------------------------------------#
# PyPortal pre-defined ESP32 Pins :
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
# Set up the ESP32 co-processor
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
# Set up a socket for the ESP32
requests.set_socket(socket, esp)

# WiFi setup ---------------------------------------------------------------------------#
print("ESP32 Socket Test")
gc.collect()
print("Free memory: ", gc.mem_free())
print()

# Very interesting - for test! (In Artie Johnson voice)
esp._debug #= 2 # = 1 to 3, levels of debug...

if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
    print("ESP32 found and in idle mode")
    # Get the ESP32 fw version number, remove trailing byte off the returned bytearray
    # and then convert it to a string for prettier printing
    firmware_version = "".join([chr(b) for b in esp.firmware_version[:-1]])
    print("Firmware version: ", firmware_version)
    print("MAC addr:", [hex(i) for i in esp.MAC_address])
    print()

print("Scanning for APs...")
for ap in esp.scan_networks():
    print("%s\t\tRSSI: %d" % (str(ap["ssid"], "utf-8"), ap["rssi"]))
print()

while not esp.is_connected:
    try:
        #esp.connect_AP(PJ_AP, PJ_PW)           # AP mode
        esp.connect_AP(WLAN_AP_ID, WLAN_AP_PW)  # Client mode
    except RuntimeError as e:
        print("Could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(esp.ssid, "utf-8"))   #, "\tRSSI:", esp.rssi)
print("PyPortal DHCP assignment", esp.pretty_ip(esp.ip_address))
print()
time.sleep(1)
try:
    cmd_socket = socket.socket() # or (socket.AF_INET, socket.SOCK_STREAM)
except RuntimeError as e:
    print(e)

# "Setup" ------------------------------------------------------------------------------#
print("Initializing...")
print()

# Open a socket to the device
open_socket()
# See if we need to generate a SHA256 hash
#auth_check()
# Get the various params
#get_status()
# Close the socket
close_socket()

print("Init done...")
gc.collect()
print("Free memory: ", gc.mem_free())
print()

# Main program loop --------------------------------------------------------------------#
#while True:
    #pass
