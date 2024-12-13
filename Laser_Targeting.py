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
import os
import targeting

# GPIO setup
GPIO.setmode(GPIO.BCM)
pins1 = [12, 16, 20, 21]
pins2 = [6, 13, 19, 26]
laser =14
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
                <label for="calibration">Calibration:</label>
                <input type="checkbox" id="calibration" name="calibrate" value="on"><br>
                <label for="xyMotor">XY Motor:</label>
                <input type="number" id="xyMotor" name="xyMotor" placeholder="Enter # of steps to rotate" required /><br>
                <label for="zMotor">Z Motor:</label>
                <input type="number" id="zMotor" name="zMotor" placeholder="Enter # of steps to rotate" required /><br>
                <input type="submit" name="adjust" value="Adjust"><br><br>
            </form>
            <form action="/" method="POST">
                <button name="led_toggle" type="submit" value="toggle">Toggle LED</button><br><br>
            </form>
            <form action="/" method="POST">
                <label for="url1">Team Locations:</label>
                <input type="text" id="url1" name="url1" placeholder="Enter a valid URL" required /><br>
                <label for="url2">Target Positions:</label>
                <input type="text" id="url2" name="url2" placeholder="Enter a valid URL" required /><br>
                <input type="submit" name="upload" value="Upload"><br><br>
            </form>
            <form action="/" method="POST">
                <button name="phaseOne" type="submit" value="PhaseOne">Phase One</button><br><br>
            </form>
            <form action="/" method="POST">
                <label for="target1">Target 1:</label>
                <input type="number" id="target1" name="target1" placeholder="Enter a Target number" required /><br>
                <label for="target2">Target 2:</label>
                <input type="number" id="target2" name="target2" placeholder="Enter a Target number" required /><br>
                <label for="target3">Target 3:</label>
                <input type="number" id="target3" name="target3" placeholder="Enter a Target number" required /><br>
                <label for="target4">Target 4:</label>
                <input type="number" id="target4" name="target4" placeholder="Enter a Target number" required /><br>
                <input type="submit" name="phaseTwo" value="PhaseTwo">
            </form>
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
        
        target_data = sorted(target_data, key=lambda item: item[0])
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
    
    radius=float(math.sqrt(math.pow(xMod,2)+math.pow(yMod,2)+math.pow(zMod,2)))
    phi=float(math.degrees(math.acos(zMod/radius))) # Phi equals verticle movement
    theta=float(math.degrees(math.atan2(yMod,xMod))) #Theta XY Plane
    return theta,phi

def orderTargets(starting_angle, angles):
    num_targets = len(angles)
    visited = [False] * num_targets
    order = []
    current_theta, current_phi = starting_angle
    for _ in range(num_targets):
        min_distance = float('inf')
        next_index = None

        for i in range(num_targets):
            if not visited[i]:
                distance = abs(current_theta - angles[i][0]) + abs(current_phi - angles[i][1])
                if rotation < min_rotation:
                    min_rotation = rotation
                    next_index = i

        visited[next_index] = True
        order.append(next_index + 1)
        current_theta, current_phi = angles[next_index]

    return order

def angleTime(angle1, angle2):
    delay=1200*1e-6 
    if angle1 > angle2:
        steps=angle1*4096/360
        delay=delay*steps
        return delay
    else:
        steps=angle2*4096/360
        delay=delay*steps
        return delay


# Web server to handle requests
def serverWebPage():
    angles=[]
    url1=None
    url2=None
    
    GPIO.output(laser,GPIO.LOW)
    targets=[]
    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()
    
    angle1 = multiprocessing.Value('d', 0.0)  # 'd' is for double (float)
    angle2 = multiprocessing.Value('d', 0.0)

    m1=targeting.Stepper(pins1,lock1,angle1)
    m2=targeting.Stepper(pins2,lock2,angle2)
    m1.zero()
    m2.zero()
    try:
        while True:
            conn, (client_ip, client_port) = s.accept()
            print(f"Connection from {client_ip}:{client_port}")
            client_message = conn.recv(2048).decode("utf-8")
            print(f"Client message:\n{client_message}")

            if "POST" in client_message:
                data = parsePostData(client_message)
                if data.get("calibrate")=="on":
                    if data.get("adjust")=="Adjust":
                        thetaM=int(data.get("xyMotor"),0)
                        phiM=int(data.get("zMotor"),0)
                        m2.rotate(thetaM)
                        m1.rotate(phiM)
                        m1.zero()
                        m2.zero()
                        print("Calibrated")
                elif data.get("led_toggle") == "toggle":
                    state=GPIO.input(laser)
                    GPIO.output(laser,not state)
                    print(f"{state}")
                elif data.get("upload")=="Upload":  # Check if "Upload" button was pressed
                    url1 = data.get("url1")
                    url2 = data.get("url2")
                    if url1 and url2:  # Only fetch data if both URLs are provided
                        print("Fetching data...")
                        angles.clear()
                        teams = gatherData(url1)
                        targets_data = gatherData(url2)
                        team_info = listTeamData(teams)
                        target_info = listTargetData(targets_data)
                        teamFound = findTeam(team_info, "Test")
                        for idx, tar in enumerate(target_info):
                            angles.append(calculateVector(teamFound, 19.5, target_info, idx))
                        print(f"angles: {angles}")
                    else:
                        print("URLs missing in POST data.")
                elif data.get("phaseOne")=="PhaseOne":
                    m1.zero()
                    m2.zero()
                    for angle in angles:
                        GPIO.output(laser,GPIO.LOW)
                        m2.goAngle(angle[0])
                        m1.goAngle(angle[1])
                        time.sleep(angleTime(angle[0],angle[1])*2.4)
                        print("Turning on laser...")
                        GPIO.output(laser, GPIO.HIGH)
                        time.sleep(3)
                        GPIO.output(laser, GPIO.LOW)
                    m1.goAngle(0.0)
                    m2.goAngle(0.0)
                        
                        
                elif data.get("phaseTwo") == "PhaseTwo":  # Ensure this matches the form's value
                    
                    try:
                        targets = [
                            int(data.get("target1", 0)),
                            int(data.get("target2", 0)),
                            int(data.get("target3", 0)),
                            int(data.get("target4", 0))
                            ]
                        targets = [t for t in targets if t > 0]
                        ordered_targets = orderTargets((0,0),[angles[t - 1] for t in targets])
                        for target_num in ordered_targets:
                            theta, phi = angles[target_num - 1]  # Adjust for zero-based indexing
                            m2.goAngle(theta)
                            m1.goAngle(phi)
                            print(f"{angles[target_num - 1]}")
                            time.sleep(angleTime(theta,phi)*2.4)
                            print("Turning on laser...")
                            GPIO.output(laser, GPIO.HIGH)
                            time.sleep(3)
                            GPIO.output(laser, GPIO.LOW)
                        m1.goAngle(0.0)
                        m2.goAngle(0.0)
                        print(f"Target {target_num} complete.")
                            
                    except ValueError:
                        print("Invalid target input. Please enter numbers only.")
                        targets = []
                

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
        
if __name__ == '__main__':

    # Use multiprocessing.Lock() to prevent a single motor from trying to 
    # execute multiple operations at the same time:
    
   
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", 8080))
    s.listen(3)
    print("Server started on port 8080.")

    # Start the server in a separate thread
    server_thread = threading.Thread(target=serverWebPage)
    server_thread.daemon = True
    server_thread.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('Shutting down')
    finally:
        GPIO.cleanup()
        print('Good Bye')
        s.close()
        server_thread.join()


