import RPi.GPIO as GPIO
import threading
import socket


LED_Pins = [12, 18, 19] 
GPIO.setmode(GPIO.BCM)
brightnesses = []
for pin in LED_Pins:
    GPIO.setup(pin, GPIO.OUT)
    pwm = GPIO.PWM(pin, 500) 
    pwm.start(0) 
    brightnesses.append(pwm)

brightness_level= [0, 0, 0]  

def web_page():
    html = """
    <html>
<head><meta charset="utf-8"><title>LED</title></head>
<body>
    <form action="/" method="POST">
        Brightness Level: <br>
        <input type="range" name="brightness" min="0" max="100" value="0" class="slider"><br><br>
        
        <input type="radio" name="led_select" value="0" class="radio" checked> LED 1 (<span id="led1_val">""" + str(brightness_level[0]) + """%</span>)<br>
        <input type="radio" name="led_select" value="1" class="radio"> LED 2 (<span id="led2_val">""" + str(brightness_level[1]) + """%</span>)<br>
        <input type="radio" name="led_select" value="2" class="radio"> LED 3 (<span id="led3_val">""" + str(brightness_level[2]) + """%</span>)<br><br>
        
        <button type="submit" class="button">Change Brightness</button>
    </form>
</body>
</html>
    """
    return bytes(html, 'utf-8')

def parsePostData(data):
    data_dict = {}
    body = data.split('\r\n\r\n')[1]  
    pairs = body.split('&')
    for pair in pairs:
        key, value = pair.split('=')
        data_dict[key] = value
    return data_dict

def serverWebPage():
    try:
         while True:
            conn, (client_ip, client_port) = s.accept()
            print(f'Connection from {client_ip} on client port {client_port}')
            client_message = conn.recv(2048).decode('utf-8')
            print(f'Message from client:\n{client_message}')

            if 'POST' in client_message:
                data = parsePostData(client_message)
                led_index = int(data.get("led_select", 0))
                brightness = int(data.get("brightness", 0))

                brightness_level[led_index] = brightness
                brightnesses[led_index].ChangeDutyCycle(brightness)

           
            try:
                conn.send(b'HTTP/1.1 200 OK\r\n')
                conn.send(b'Content-Type: text/html\r\n')
                conn.send(b'Connection: close\r\n\r\n')
                conn.sendall(web_page())
                print("Response sent successfully.")
            except BrokenPipeError:
                print("Client disconnected before response was sent.")
            finally:
                conn.close()
    except Exception as e:
        print(e)
    finally:
        conn.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 8080))  
s.listen(3)  

webpageThread = threading.Thread(target=serverWebPage)
webpageThread.daemon = True
webpageThread.start()

try:
    while True:
        pass
except KeyboardInterrupt:
    print('Shutting down')
    for pwm in brightnesses:
        pwm.stop()
    GPIO.cleanup()
    webpageThread.join()
    s.close()
    
