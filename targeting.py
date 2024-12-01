import time
import multiprocessing
from RPi import GPIO
import socket
import threading

class Stepper:

  # Class attributes:
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001] # CCW sequence
    stepsPerDegree = 4096/360    # 4096 steps/rev * 1/360 rev/deg

    def __init__(self, pins, lock, angle, delay=1200):
        self.delay = delay         # delay between motor steps [us]
        self.pins = pins           # motor drive pins (4-element list)
        self.angle = angle
        self.current_angle=0 # shared angle using multiprocessing.Value
        self.seq_state = 0         # track position in sequence
        self.lock = lock           # multiprocessing lock      # multiprocessing lock

        for p in self.pins:
          GPIO.setup(p,GPIO.OUT)

  # Signum function:
    def __sgn(self, x):
        if x == 0: return(0)
        else: return(int(abs(x)/x))

  # Move a single +/-1 step in the motor sequence:
    def __step(self, dir):
        seq = Stepper.seq[self.seq_state]
        self.seq_state += dir          # increment/decrement the step
        self.seq_state %= 8            # ensure result stays in [0,7]
        for idx in range(4):
            GPIO.output(self.pins[idx], seq & 1<<idx)

    # THE FOLLOWING LINES WILL NOT ACTUALLY CHANGE THE ANGLE ATTRIBUTE! 
    # NOT A PROBLEM FOR RELATIVE MOVEMENT SINCE WE DON'T NEED TO KNOW
    # THE ABSOLUTE ANGLE, BUT THIS WILL BE A PROBLEM WHEN TRYING TO
    # IMPLEMENT THE goAngle() METHOD!!!  
    #
    # HINT: THINK ABOUT USING A multiprocessing.value() AS AN
    # INSTANCE ATTRIBUTE TO HOLD THE CURRENT ANGLE INSTEAD OF 
    # A REGULAR FLOAT...
    #
        self.current_angle += dir/Stepper.stepsPerDegree
        self.current_angle %= 360              # limit to [0,359.9+] range

  # Move relative angle from current position:
    def __rotate(self, delta, lock):
        lock.acquire()                 # wait until the lock is available
        numSteps = int(Stepper.stepsPerDegree * abs(delta))    # find the right # of steps
        dir = self.__sgn(delta)        # find the direction (+/-1)
        for s in range(numSteps):      # take the steps
          self.__step(dir)
          time.sleep(self.delay/1e6)
        lock.release()

  # Move relative angle from current position:
    def rotate(self, delta):
        time.sleep(0.1)
        p = multiprocessing.Process(target=self.__rotate, args=(delta,self.lock))
        p.start()

  # Move to an absolute angle taking the shortest possible path:
    def __goAngle(self, angle, lock):
        angle = angle % 360
        # Calculate the angle difference using the current angle in multiprocessing.Value
        delta = (angle - self.angle.value) % 360
        self.angle.value=angle
        if delta > 180:
            delta -= 360
        
        lock.acquire()  # wait until the lock is available
        numSteps = int(Stepper.stepsPerDegree * abs(delta))  # find the right # of steps
        dir = self.__sgn(delta)  # find the direction (+/-1)
        for s in range(numSteps):  # take the steps
            self.__step(dir)
            time.sleep(self.delay / 1e6)

        # Update the angle in multiprocessing.Value after movement
        
        lock.release()

    def goAngle(self, angle):
        time.sleep(0.1)
        p = multiprocessing.Process(target=self.__goAngle, args=(angle, self.lock))
        p.start()
        print(self.angle.value)
        
        
        

  # Set the motor zero point
    def zero(self):
        self.angle.value = 0
