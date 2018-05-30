from artiq.experiment import *
from artiq.coredevice.sampler import adc_mu_to_volt
from numpy import savetxt
import numpy as np
import matplotlib.pyplot as plt
import math


class Sampler(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("sampler0")
        self.setattr_device("ttl0")
        self.setattr_device("ttl1")
        self.setattr_device("i2c_switch0")
        self.setattr_device("i2c_rj45_dir")

        self.data = []
        self.timestamps = []
        self.gains = [0] * 8

    @kernel
    def run(self):
        self.setup()

        # self.ttl()

        # self.set_zotino()
        self.ttl_and_sample()
        # for i in range(1):
        #     self.sample(100, 100)

    @kernel
    def setup(self):
        # self.core.reset()
        self.core.break_realtime()

        self.sampler0.init()

        self.set_dio_dir()

        for i in range(7):
            self.sampler0.set_gain_mu(i, self.gains[i])

    @kernel
    def ttl_and_sample(self):
        delay(1*ms)
        with parallel:
            with sequential:
                delay(50*us)
                for i in range(5):
                    self.ttl1.pulse(i * 30 * us)
                    delay(100 * us)
            self.sample(100, 4)

    @kernel
    def set_dio_dir(self):
        self.i2c_switch0.set(3)
        self.i2c_rj45_dir.set(0x00)

        # self.i2c_switch0.set(7)
        # self.i2c_rj45_dir.set2(0xFF)

        delay(700 * ms)

        self.ttl1.output()

        delay(700 * us)


    @kernel
    def ttl(self):
        delay(1*ms)
        self.ttl16.output()
        delay(1*ms)
        self.ttl16.on()
        delay(10*ms)


    @kernel
    def sample(self, n, t):
        data_all = [[0] * 8 for i in range(n)]
        timestamps = [0] * n

        # delay(1*ms)
        for i in range(n):
            timestamps[i] = now_mu()
            self.sampler0.sample_mu(data_all[i])
            delay(t * us)
        # delay(1*ms)
        self.ret_time(timestamps)
        self.ret_data(data_all)

    @rpc(flags={"async"})
    def ret_data(self, data):
        self.data.append(data)

    @rpc(flags={"async"})
    def ret_time(self, data):
        self.timestamps.append(data)

    def analyze(self):
        # avr = self.average_fft(self.data)
        # mchan = self.mchan
        # maximum = max(avr[mchan])
        # m = [i for i, j in enumerate(avr[mchan]) if j == maximum]
        # cross_talk = [20 * math.log10(avr[j][m[0]] / avr[mchan][m[0]]) for j in range(8)]
        # print(', '.join('{:.2f}'.format(k) for a, k in enumerate(cross_talk)))

        n = len(self.timestamps[0])
        timestamps = [self.core.mu_to_seconds(mu)*1000 for mu in self.timestamps[0]]
        timestamps = [d-timestamps[0] for d in timestamps]

        samples = [] * len(self.data)
        samples = [[adc_mu_to_volt(d[i], self.gains[i]) for d in self.data[0]] for i in range(8)]

        plt.figure(1)
        # channel_arragement = [4, 0, 5, 1, 6, 2, 7, 3]
        channel_arragement = list(range(8))
        for i, channel in enumerate(samples):
            plt.subplot(241+channel_arragement[i])
            # plt.xkcd()
            # print(timestamps)
            # print(samples[channel_arragement[i]])
            plt.plot(timestamps, samples[channel_arragement[i]], '-')
            plt.ylim(-10, 10)

            # plt.xlabel("F [Hz]")
            plt.title("Channel %d" % i)
            plt.grid()
        # print("Ts = %.2f us, Fs = %.2f kHz" % (ts * 1e6, 1 / ts / 1e3))
        plt.show()

    def average_fft(self, data):

        fft = [[[]] * 8] * len(data)
        n = len(samples[k][0])
            # for i, channel in enumerate(samples[k]):
            #     fft[k][i] = np.fft.fft(channel) / n
            #     fft[k][i] = np.fft.fftshift(fft[k][i])
            #     fft[k][i] = np.absolute(fft[k][i])[n // 2:]
        return samples
        avr = np.mean(fft, 0)
        return avr
