from artiq.experiment import *
from artiq.coredevice.sampler import adc_mu_to_volt
import numpy as np
import matplotlib.pyplot as plt
import random


class Sampler(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("sampler1")
        self.setattr_device("zotino0")

        self.data = []
        self.timestamps = []
        # mchan = 0
        self.gains = [0] * 8
        # self.gains[mchan] = 0

        angles = [i for i in np.arange(0, 720, 1)]
        sin_table = [2*np.sin(np.radians(a)) for a in angles]
        r = [random.uniform(-5., 5.) for i in range(8)]
        self.voltages = [[r[x]+i for x in range(8)] for i in sin_table]
        self.n = len(sin_table)

    @kernel
    def run(self):
        self.setup_sampler()
        self.setup_zotino()
        delay(20 * us)

        # self.sine_1_channel()
        self.sine_8_channel()

    @kernel
    def sine_8_channel(self):
        data_all = [[0] * 8 for i in range(self.n)]
        timestamps = [0] * self.n

        n=8*3
        for i in range(self.n):
            self.zotino0.set_dac(self.voltages[i], list(range(n, n+8)))
            delay(400 * us)
            timestamps[i] = now_mu()
            self.sampler1.sample_mu(data_all[i])
            delay(800 * us)

        self.ret_time(timestamps)
        self.ret_data(data_all)

    @kernel
    def sine_1_channel(self):
        data_all = [[0] * 2 for i in range(self.n)]
        timestamps = [0] * self.n

        for i in range(self.n):
            self.zotino0.write_dac(0, self.voltages[i][0])
            self.zotino0.load()
            delay(1 * us)
            timestamps[i] = now_mu()
            self.sampler1.sample_mu(data_all[i])
            delay(89 * us)

        self.ret_time(timestamps)
        self.ret_data(data_all)

    @kernel
    def setup_zotino(self):
        self.core.break_realtime()
        self.zotino0.init()

        delay(10*ms)
        self.zotino0.set_leds(0xaa)
        delay(10 * ms)

        voltages = [0.] * 40
        self.zotino0.set_dac(voltages)

        delay(10*ms)

    @kernel
    def setup_sampler(self):
        self.core.break_realtime()
        self.sampler1.init()

        for i in range(7):
            self.sampler1.set_gain_mu(i, self.gains[i])

    @rpc(flags={"async"})
    def ret_data(self, data):
        self.data.append(data)

    @rpc(flags={"async"})
    def ret_time(self, data):
        self.timestamps.append(data)

    def analyze(self):
        self.process_data()
        self.plot_mpl()

    def process_data(self):
        self.timestamps = [item for sublist in self.timestamps for item in sublist]
        timestamps = [self.core.mu_to_seconds(mu)*1000 for mu in self.timestamps]
        self.time = [d-timestamps[0] for d in timestamps]

        self.data = [item for sublist in self.data for item in sublist]  # unpack many runs
        self.samples = [[adc_mu_to_volt(d[i], self.gains[i]) for d in self.data] for i in range(len(self.data[0]))]  # repack to list of channels

    def plot_mpl(self):
        plt.figure(1)
        channel_arragement = [0, 1, 2, 3, 4, 5, 6, 7]
        for i, channel in enumerate(self.samples):
            plt.subplot(241+channel_arragement[i])
            # plt.xkcd()
            plt.plot(self.time, self.samples[channel_arragement[i]])
            plt.ylim(-10.5, 10.5)

            plt.xlabel("Time [ms]")
            plt.ylabel("Voltage [V]")
            plt.title("Channel %d" % i)
            plt.grid()
        plt.show()