import sys
# sys.path.append('/home/pawel/artiq-dev/kasli-i2c')
# from i2c_switch import *
from artiq.experiment import *


class dio_test(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        # self.setattr_device("led0")
        # self.setattr_device("ttl0")  # eem0.0
        # self.setattr_device("ttl8")  # eem1.0
        ttls = ["ttl" + str(x) for x in range(15 + 1)]
        for s in ttls:
            self.setattr_device(s)
        self.setattr_device("i2c_switch0")
        self.setattr_device("i2c_rj45_dir")

        # I2C init using kasli-i2c
        mask = 0x13  # in, in,in  Out, In, In, out, out
        # gpio = GpioController()
        # gpio.open_from_url('ftdi://ftdi:4232h/3', mask)
        # port = I2CPort(gpio)
        # switch = i2c_switch(port)
        #
        # rj45 = I2CDevice(port, 0x3E)
        # switch.enable_eem(0)
        # rj45.i2c_write_byte_to(0x00)  # high - output
        #
        # switch.enable_eem(1)
        # rj45.i2c_write_byte_to(0x01)
        # gpio.close()


    @kernel
    def run(self):
        self.i2c_switch0.set(5)
        self.i2c_rj45_dir.set2(0x00)

        self.i2c_switch0.set(7)
        self.i2c_rj45_dir.set2(0xFF)
        start_time = now_mu() + self.core.seconds_to_mu(500*ms)
        while self.core.get_rtio_counter_mu() < start_time:
            pass
        inputs = [
            # self.ttl0,
            # self.ttl1,
            self.ttl2,
            self.ttl3,
            self.ttl4,
            # self.ttl5,
            # self.ttl6,
            # self.ttl7,
        ]
        outputs = [
            # self.ttl8, self.ttl9,
            self.ttl10,
            self.ttl11,
            self.ttl12,
            # self.ttl13,
            # self.ttl14,
            # self.ttl15
        ]
                #self.ttl16]#, self.ttl17, self.ttl18, self.ttl19, self.ttl20,
                #self.ttl21, self.ttl22, self.ttl23]
        self.core.reset()
        # self.ttl8.output()
        for n in outputs:
            n.output()

        for n in inputs:
            n.input()
        # self.ttl0.input()
        delay(10*us)



        # delay(1000 * ms)

        # self.i2c_switch0.set(7)
        # # write 0x00 to set direction (inputs)
        # self.i2c_rj45_dir.set(0x00)
        #
        # self.i2c_switch0.set(5)
        # # write 0x01 to set direction (output)
        # self.i2c_rj45_dir.set(0x01)
        # delay(1000*ms)
        # self.core.break_realtime()
        j = 3
        for i in range(0, j):
            # self.ttl8.off()
            for n in outputs:
                n.off()
                delay(200 * us)
            # self.ttl0.sample_input()
            for n in inputs:
                n.sample_input()

            # self.ttl8.on()
            for n in outputs:
                n.on()
                delay(200 * us)
            # self.ttl0.sample_input()
            for n in inputs:
                n.sample_input()

        r = []

        for i in range(6):
            for n in inputs:
                r = r + [n.sample_get()]
            # r = r + [self.ttl0.sample_get()]
            delay(1 * ms)

        print(r)
        expected0 = [0] * len(inputs) + [1] * len(inputs)
        expected = []
        for i in range(j):
            expected = expected + expected0
        # print(expected)
        if r == expected:
            print("Passed!")