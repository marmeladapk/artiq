import sys
from artiq.experiment import *
from bitstring import BitArray
from random import randint


class dio_test(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        # self.setattr_device("led0")
        ttls = ["ttl" + str(x) for x in range(40)]
        for s in ttls:
            self.setattr_device(s)
        self.setattr_device("i2c_switch0")
        self.setattr_device("i2c_rj45_dir")

        self.i2c_switch0.set(4)
        self.i2c_rj45_dir.set(0x00)
        self.i2c_switch0.set(3)
        self.i2c_rj45_dir.set(0x01)

        n = BitArray(uint=randint(0, 255), length=8)
        print(n[0])

    @kernel
    def run(self):
        start_time = now_mu() + self.core.seconds_to_mu(500*ms)
        while self.core.get_rtio_counter_mu() < start_time:
            pass
        ttls = [self.ttl1, self.ttl2, self.ttl3, self.ttl4,
                self.ttl5, self.ttl6, self.ttl7, self.ttl9, self.ttl10,
                self.ttl11, self.ttl12, self.ttl13, self.ttl14, self.ttl15,
                self.ttl16, self.ttl17, self.ttl18, self.ttl19, self.ttl20,
                self.ttl21, self.ttl22, self.ttl23]
        self.core.reset()
        self.io_test()

    @kernel
    def io_test(self):
        eem2 = [self.ttl0, self.ttl1, self.ttl2, self.ttl3, self.ttl4,
                self.ttl5, self.ttl6, self.ttl7]
        eem3 = [self.ttl8, self.ttl9, self.ttl10,
                self.ttl11, self.ttl12, self.ttl13, self.ttl14, self.ttl15]

        for ttl in eem2:
            ttl.input()
        for ttl in eem3:
            ttl.output()
        input = self.ttl0
        output = self.ttl8

        delay(1 * us)

        n = BitArray(uint=randint(0, 255), length=8)
        print(n[0])

        # self.core.break_realtime()
        for i in range(0, 3):
            output.off()
            # if n[0]:
            #     output.on()
            # else:
            #     output.off()
            delay(200 * us)
            input.sample_input()

            output.on()
            delay(200 * us)
            input.sample_input()

        r = []
        for i in range(0, 6):
            r = r + [input.sample_get()]
        delay(1 * 1000 * ms)
        print(r)