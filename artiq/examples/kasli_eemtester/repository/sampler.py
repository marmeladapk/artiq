from artiq.experiment import *


class Sampler(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("sampler0")
        # self.setattr_device("urukul0_cpld")
        # self.setattr_device("urukul0_ch0")

    def run(self):
        self.data = []
        self.sample()
        for d in self.data:
            print(d)

    @kernel
    def sample(self):
        self.core.break_realtime()
        self.sampler0.init()
        #self.urukul0_cpld.init()
        #self.urukul0_ch0.init()

        #delay(1000*us)

        #self.urukul0_ch0.set(100*MHz)
        #self.urukul0_ch0.sw.on()
        #self.urukul0_ch0.set_att(10.)

        #delay(1000*us)

        #for g in range(4):
            #for ch in range(8):
        self.sampler0.set_gain_mu(0, 2)
        self.ret([self.sampler0.get_gains_mu()][0])
        delay(10*ms)
        raw = [0] * 8
        self.sampler0.sample_mu(raw)
        self.ret(raw[0])
        delay(10*ms)
        data = [0.] * 8
        for i in range(100):
            self.sampler0.sample(data)
            self.ret(data[0]*1000)
            delay(500*us)

    @rpc(flags={"async"})
    def ret(self, data):
        self.data.append(data)
