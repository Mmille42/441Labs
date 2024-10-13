import RPi.GPIO as GPIO
import time

class Shifter:
    def __init__(self, serialPin, clockPin, latchPin):
        self.serialPin = serialPin
        self.clockPin = clockPin
        self.latchPin = latchPin
        
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.serialPin, GPIO.OUT)
        GPIO.setup(self.latchPin, GPIO.OUT, initial=0)  # Start latch & clock low
        GPIO.setup(self.clockPin, GPIO.OUT, initial=0)
    
    def __ping(self, p):
        GPIO.output(p, 1)
        time.sleep(0)
        GPIO.output(p, 0)
        
    def shiftByte(self, b):
        for i in range(8):
            GPIO.output(self.serialPin, b & (1 << i))
            self.__ping(self.clockPin)
        self.__ping(self.latchPin)

shifter = Shifter(serialPin=23, clockPin=25, latchPin=24)

try:
    while 1:
        for i in range(2**8):
            shifter.shiftByte(i)
            time.sleep(0.5)
except:
        GPIO.cleanup()
