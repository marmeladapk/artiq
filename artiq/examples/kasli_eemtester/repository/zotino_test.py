from artiq.experiment import *
from artiq.coredevice.sampler import adc_mu_to_volt
from numpy import savetxt
import numpy as np
import matplotlib.pyplot as plt
import math


class Sampler(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("sampler1")
        self.setattr_device("zotino0")

        # Channel with carrier
        self.mchan = 0

        self.data = []
        self.timestamps = []
        self.gains = [0] * 8
        self.gains[self.mchan] = 0

    @kernel
    def run(self):
        self.setup_sampler()
        self.setup_zotino()
        delay(20 * us)
        self.set_zotino()

        # for i in range(1):
        self.sample(128, 200)

    @kernel
    def setup_zotino(self):
        self.core.break_realtime()
        self.zotino0.init()

        self.zotino0.calibrate(1, -10.0, 9.99969)
        self.zotino0.load()
        # self.zotino0.set_leds(0x5A)

    @kernel
    def set_zotino(self):
        # voltages = [0.5, 1.0, 1.5, 2.0, 3.5, 4.0, 4.5, 5.0] * 5
        # voltages = [5] * 40
        # voltages = [-5] * 40
        # while True:
        # delay(10 * ms)
        # self.zotino0.set_dac(voltages)
        self.zotino0.write_dac(1, 0.)
        # self.zotino0.write_dac_mu(1, 0x8000)
        self.zotino0.load()
        delay(135 * us)

    @kernel
    def setup_sampler(self):
        self.core.break_realtime()
        self.sampler1.init()

        for i in range(7):
            self.sampler1.set_gain_mu(i, self.gains[i])

    @kernel
    def sample(self, n, t):
        data_all = [[0] * 8 for i in range(n)]
        timestamps = [0] * n

        # delay(1*ms)
        for i in range(n):
            timestamps[i] = now_mu()
            self.sampler1.sample_mu(data_all[i])
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
        timestamps = [self.core.mu_to_seconds(mu) for mu in self.timestamps[0]]
        timestamps = [d-timestamps[0] for d in timestamps]

        samples = [] * len(self.data)
        samples = [[adc_mu_to_volt(d[i], self.gains[i]) for d in self.data[0]] for i in range(8)]
        print("%.5f" % samples[6][10])
        samples = samples[6]

        plt.figure(1)
        # channel_arragement = [4, 0, 5, 1, 6, 2, 7, 3]
        channel_arragement = [0, 1, 2, 3, 4, 5, 6, 7]
        for i, channel in enumerate(samples):
            # plt.subplot(241+channel_arragement[i])
            # plt.xkcd()
            # print(timestamps)
            # print(samples[channel_arragement[i]])
            # plt.plot(timestamps, samples[channel_arragement[i]])
            plt.plot(timestamps, samples)
            plt.ylim(-10.5, 10.5)

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
