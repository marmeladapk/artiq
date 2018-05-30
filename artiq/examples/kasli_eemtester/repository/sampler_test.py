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
        self.setattr_device("urukul0_cpld")
        self.setattr_device("urukul0_ch0")
        self.setattr_device("urukul0_ch1")
        self.setattr_device("urukul0_ch2")
        self.setattr_device("urukul0_ch3")

        # Channel with carrier
        self.mchan = 0

    def run(self):
        self.data = []
        self.timestamps = []
        self.gains = [0] * 8
        self.gains[self.mchan] = 0

        self.set_urukul()
        for i in range(1):
            self.sample(128, 6)

    @kernel
    def set_urukul(self):
        self.core.reset()
        self.core.break_realtime()
        self.urukul0_cpld.init()
        self.urukul0_ch0.init()
        self.urukul0_ch1.init()
        self.urukul0_ch2.init()
        self.urukul0_ch3.init()
        delay(1000*us)

        self.urukul0_ch0.set(10*MHz)
        self.urukul0_ch0.sw.on()
        self.urukul0_ch0.set_att(10.)

        self.urukul0_ch1.set(15 * MHz)
        self.urukul0_ch1.sw.on()
        self.urukul0_ch1.set_att(10.)

        self.urukul0_ch2.set(5 * MHz)
        self.urukul0_ch2.sw.on()
        self.urukul0_ch2.set_att(10.)

        self.urukul0_ch3.set(13 * MHz)
        self.urukul0_ch3.sw.on()
        self.urukul0_ch3.set_att(10.)

    @kernel
    def sample(self, n, t):
        # self.core.reset()
        self.core.break_realtime()
        self.sampler0.init()
        for i in range(7):
            self.sampler0.set_gain_mu(i, self.gains[i])
        delay(1*ms)

        data_all = [[0] * 8 for i in range(n)]
        timestamps = [0] * n

        delay(1*ms)
        for i in range(n):
            timestamps[i] = now_mu()
            self.sampler0.sample_mu(data_all[i])
            delay(t * us)
        delay(1*ms)
        self.ret_time(timestamps)
        self.ret_data(data_all)

    @rpc(flags={"async"})
    def ret_data(self, data):
        self.data.append(data)

    @rpc(flags={"async"})
    def ret_time(self, data):
        self.timestamps.append(data)

    def analyze(self):
        avr = self.average_fft(self.data)
        mchan = self.mchan
        maximum = max(avr[mchan])
        m = [i for i, j in enumerate(avr[mchan]) if j == maximum]
        cross_talk = [20 * math.log10(avr[j][m[0]] / avr[mchan][m[0]]) for j in range(8)]
        print(', '.join('{:.2f}'.format(k) for a, k in enumerate(cross_talk)))

        n = len(self.timestamps[0])
        timestamps = [self.core.mu_to_seconds(mu) for mu in self.timestamps[0]]
        timestamps = [d-timestamps[0] for d in timestamps]
        ts = timestamps[1] - timestamps[0]
        nu = np.fft.fftfreq(n, ts)
        nu = np.fft.fftshift(nu)
        nu = nu[n // 2:]
        plt.figure(1)
        channel_arragement = [4, 0, 5, 1, 6, 2, 7, 3]
        for i, channel in enumerate(avr):
            plt.subplot(241+channel_arragement[i])
            plt.plot(nu, avr[i])
            plt.xlabel("F [Hz]")
            plt.title("Channel %d" % i)
            plt.grid()
        print("Ts = %.2f us, Fs = %.2f kHz" % (ts * 1e6, 1 / ts / 1e3))
        plt.show()

    def average_fft(self, data):
        samples = [[]] * len(data)
        fft = [[[]] * 8] * len(data)
        for k in range(len(data)):
            samples[k] = [[adc_mu_to_volt(d[i], self.gains[i]) for d in data[k]] for i in range(8)]
            n = len(samples[k][0])
            for i, channel in enumerate(samples[k]):
                fft[k][i] = np.fft.fft(channel) / n
                fft[k][i] = np.fft.fftshift(fft[k][i])
                fft[k][i] = np.absolute(fft[k][i])[n // 2:]
        avr = np.mean(fft, 0)
        return avr

    def crosstalk(self, data, timestamps):
        samples = [[adc_mu_to_volt(d[i], self.gains[i]) for d in data] for i in range(8)]
        # timestamps = [self.core.mu_to_seconds(mu) for mu in timestamps]
        # timestamps = [d-timestamps[0] for d in timestamps]
        n = len(samples[0])
        # ts = timestamps[1] - timestamps[0]
        # nu = np.fft.fftfreq(n, ts)
        # nu = np.fft.fftshift(nu)
        # nu = nu[n // 2:]
        # plt.figure(1)
        # channel_arragement = [4, 0, 5, 1, 6, 2, 7, 3]
        fft = [[]] * 8
        for i, channel in enumerate(samples):
            fft[i] = np.fft.fft(channel)/n
            fft[i] = np.fft.fftshift(fft[i])
            fft[i] = np.absolute(fft[i])[n // 2:]
            # plt.subplot(241+channel_arragement[i])
            # plt.plot(nu, fft[i])
            # plt.xlabel("F [Hz]")
            # plt.title("Channel %d" % i)
            # maximum = max(fft[i])
            # m = [i for i, j in enumerate(fft[i]) if j == maximum]
            # print("F%d = %.3f kHz" % (i, nu[m[0]]/1e3))

        # print("Ts = %.2f us, Fs = %.2f kHz" % (ts*1e6, 1/ts/1e3))
        for i in range(1):
            maximum = max(fft[i])
            m = [i for i, j in enumerate(fft[i]) if j == maximum]
            cross_talk = [20*math.log10(fft[j][m[0]]/fft[0][m[0]]) for j in range(8)]
        # plt.show()
        return cross_talk


