import time
import multiprocessing
from RPi import GPIO

GPIO.setmode(GPIO.BCM)


class Stepper:
    # Class attributes:
    seq = [0b0001, 0b0011, 0b0010, 0b0110, 0b0100, 0b1100, 0b1000, 0b1001]  # CCW sequence
    stepsPerDegree = 4096 / 360  # 4096 steps/rev * 1/360 rev/deg

    def __init__(self, pins, lock, delay=1200):
        self.delay = delay  # delay between motor steps [us]
        self.pins = pins  # motor drive pins (4-element list)
        self.angle = multiprocessing.Value('f', 0)  # current output shaft angle
        self.seq_state = 0  # track position in sequence
        self.lock = lock  # multiprocessing lock

        for p in self.pins:
            GPIO.setup(p, GPIO.OUT)

    # Signum function:
    def __sgn(self, x):
        if x == 0:
            return (0)
        else:
            return (int(abs(x) / x))

    # Move a single step in the motor sequence:
    def __step(self, dir, angle):
        seq = Stepper.seq[self.seq_state]
        self.seq_state += dir  # increment/decrement the step
        self.seq_state %= 8  # ensure result stays in [0,7]
        for idx in range(4):
            GPIO.output(self.pins[idx], seq & 1 << idx)
        angle.value += dir / Stepper.stepsPerDegree
        angle.value %= 360  # limit to [0,360) range

    # Move multiple steps:
    def __steps(self, num_steps, dir, angle):
        for s in range(num_steps):  # take the steps
            self.__step(dir, angle)
            time.sleep(1200/ 1e6)

    # Move relative angle from current position:
    def __rotate(self, delta, lock, angle):
        lock.acquire()  # wait until the lock is available
        num_steps = int(abs(delta))  # find the right # of steps
        dir = self.__sgn(delta)  # find the direction (+/-1)
        self.__steps(num_steps, dir, angle)
        lock.release()

    def __goAngle(self, new_angle, lock, angle):
        lock.acquire()  # wait until the lock is available
        new_angle %= 360  # force new_angle to [0,360) range
        delta = (new_angle - angle.value) % 360
        if abs(delta) > 180: delta = delta - 360
        num_steps = int(Stepper.stepsPerDegree * abs(delta))  # find the right # of steps
        dir = self.__sgn(delta)  # find the direction (+/-1)
        self.__steps(num_steps, dir, angle)
        lock.release()

    # Move to angle relative to current position:
    def rotate(self, delta):
        p = multiprocessing.Process(target=self.__rotate, args=(delta, self.lock, self.angle))
        p.start()

    # Move to absolute angle, taking the shortest possible path:
    def goAngle(self, new_angle):
        p = multiprocessing.Process(target=self.__goAngle, args=(new_angle, self.lock, self.angle))
        p.start()

    # Set the motor zero point
    def zero(self):
        self.angle.value = 0

