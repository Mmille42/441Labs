import time
import multiprocessing
from RPi import GPIO
import socket
import numpy as np
import urllib.request
from urllib.parse import unquote
import threading
import math
import json
import targeting

# GPIO setup
GPIO.setmode(GPIO.BCM)
pins1 = [13, 16, 19, 20]
pins2 = [17, 22, 23, 24]
laser =10
GPIO.setup(laser, GPIO.OUT)
GPIO.output(laser,GPIO.LOW)

# HTML for the web server
def web_page():
    html = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>Laser Targets</title>
    </head>
    <body>
        <form action="/" method="POST">
            <button name="led_toggle" type="submit" value="toggle">Toggle LED</button><br><br>
        </form>
        <form action="/" method="POST">
            <label for="url1">Team Locations:</label>
            <input type="text" id="url1" name="url1" placeholder="Enter a valid URL" required /><br><br>
            <label for="url2">Target Positions:</label>
            <input type="text" id="url2" name="url2" placeholder="Enter a valid URL" required /><br><br>
            <input type="submit" value="Upload">
        </form>
        <form action="/" method="POST">
            <button name="phaseOne" type="submit" value="phase">Phase One</button><br><br>
        </form>
        <form actions="/" method="POST">
            <label for="target1">Target 1:</label>
            <input type="text" id="target1" name="target1" placeholder="Enter a Target number" required /><br><br>
            <label for="target2">Target 2:</label>
            <input type="text" id="target2" name="target2" placeholder="Enter a Target number" required /><br><br>
            <label for="target3">Target 3:</label>
            <input type="text" id="target3" name="target3" placeholder="Enter a Target number" required /><br><br>
            <label for="target4">Target 4:</label>
            <input type="text" id="target4" name="target4" placeholder="Enter a Target number" required /><br><br>
            <input type="submit" value="PhaseTwo">
    </body>
    </html>
    """
    return bytes(html, 'utf-8')

# Parse POST data manually
def parsePostData(data):
    data_dict = {}
    body = data.split('\r\n\r\n')[1]
    pairs = body.split('&')
    for pair in pairs:
        key, value = pair.split('=')
        data_dict[key] = value
    return data_dict

def gatherData(url):
    try:
        decoded_url = unquote(url)
        with urllib.request.urlopen(decoded_url, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return {}
    
def listTeamData(data):
    team_data = []
    for team in data:
        team_name = team.get("Team Name", f"Team {len(team_data) + 1}")
        x = float(team.get('x', 0))
        y = float(team.get('y', 0))
        team_data.append([team_name, x, y])
    return team_data
        
def listTargetData(data):
    target_data = []
    for target in data:
        target_number = int(target.get('number', len(target_data) + 1))  # Use 'number' if available, else auto-generate
        x = float(target.get('x', 0))
        y = float(target.get('y', 0))
        z = float(target.get('z', 0))
        target_data.append([target_number, x, y, z])
    return target_data

def findTeam(teams, team_name):
    for team in teams:
        if team[0] == team_name:  # Check if the first element matches the target name
            return team
    return None

def calculateVector(teamLocation,height,targets,index):
    locX=teamLocation[1]
    locY=teamLocation[2]
    locZ=height
    xCord=targets[index][1]
    yCord=targets[index][2]
    zCord=targets[index][3]
    xMod=xCord-locX
    yMod=yCord-locY
    zMod=zCord-locZ
    
    radius=math.sqrt(math.pow(xMod,2)+math.pow(yMod,2)+math.pow(zMod,2))
    phi=math.degrees(math.acos(zMod/radius)) # Phi equals verticle movement
    theta=math.degrees(math.atan2(yMod,xMod)) #Theta XY Plane
    return theta,phi
    



# Web server to handle requests
def server_web_page():
    angles=[]
    GPIO.output(laser,GPIO.LOW)
    targets=[]
    try:
        while True:
            conn, (client_ip, client_port) = s.accept()
            print(f"Connection from {client_ip}:{client_port}")
            client_message = conn.recv(2048).decode("utf-8")
            print(f"Client message:\n{client_message}")

            if "POST" in client_message:
                data = parsePostData(client_message)
                
                if data.get("led_toggle") == "toggle":
                    state=GPIO.input(laser)
                    GPIO.output(laser,not state)
                    print(f"{state}")
                elif data.get("url1") and data.get("url2"):
                    url1 = data.get("url1")
                    url2 = data.get("url2")
                elif data.get("phaseTwo") == "phasetwo":  # Moved this block up
                    try:
                        targets = [
                            int(data.get("target1", 0)),
                            int(data.get("target2", 0)),
                            int(data.get("target3", 0)),
                            int(data.get("target4", 0))]
                    except ValueError:
                        print("Invalid target input. Please enter numbers only.")
                        targets = []
                    
                elif data.get("phaseOne")=="phaseOne":
                    print(f"targets: {targets}")
                elif data.get("phaseTwo") == "phasetwo":  # Moved this block up
                    try:
                        targets = [
                        int(data.get("target1", 0)),
                        int(data.get("target2", 0)),
                        int(data.get("target3", 0)),
                        int(data.get("target4", 0))]
            except ValueError:
                print("Invalid target input. Please enter numbers only.")
                targets = []

                    
                if url1 and url2:
                    print("Fetching data...")
                    angles.clear()
                    teams = gatherData(url1)
                    targets = gatherData(url2)
                    team_info=listTeamData(teams)
                    target_info=listTargetData(targets)
                    teamFound=findTeam(team_info, "Test")
                    for idx, tar in enumerate(target_info):
                        angles.append(calculateVector(teamFound,25.0,target_info,idx))
                    print(f"angles:{angles}")
                else:
                    print("URLs missing in POST data.")
                    print(f"angles:{angles}")

            try:
                conn.sendall(b"HTTP/1.1 200 OK\r\n")
                conn.sendall(b"Content-Type: text/html\r\n")
                conn.sendall(b"Connection: close\r\n\r\n")
                conn.sendall(web_page())
            except BrokenPipeError:
                print("Client disconnected before response was sent.")
            finally:
                conn.close()
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        conn.close()
if __name__ == "__main__":
    # Initialize the server socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", 8080))
    s.listen(3)
    print("Server started on port 8080.")

    # Start the server in a separate thread
    server_thread = threading.Thread(target=server_web_page)
    server_thread.daemon = True
    server_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down server.")
    finally:
        GPIO.cleanup()
        s.close()
        server_thread.join()

