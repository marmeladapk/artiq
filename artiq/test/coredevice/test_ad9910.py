from artiq.experiment import *
from artiq.test.hardware_testbench import ExperimentCase
from artiq.coredevice.ad9910 import _AD9910_REG_FTW, _AD9910_REG_PROFILE0
from artiq.coredevice.urukul import (
        urukul_sta_smp_err, CFG_CLK_SEL0, CFG_CLK_SEL1)


class AD9910Exp(EnvExperiment):
    def build(self, runner):
        self.setattr_device("core")
        self.dev = self.get_device("urukul_ad9910")
        self.runner = runner

    def run(self):
        getattr(self, self.runner)()

    @kernel
    def instantiate(self):
        pass

    @kernel
    def init(self):
        self.core.break_realtime()
        self.dev.cpld.init()
        self.dev.init()

    @kernel
    def init_fail(self):
        self.core.break_realtime()
        self.dev.cpld.init()
        cfg = self.dev.cpld.cfg_reg
        cfg &= ~(1 << CFG_CLK_SEL1)
        cfg |= 1 << CFG_CLK_SEL0
        self.dev.cpld.cfg_write(cfg)
        # clk_sel=1, external SMA, should fail PLL lock
        self.dev.init()

    @kernel
    def set_get(self):
        self.core.break_realtime()
        self.dev.cpld.init()
        self.dev.init()
        self.dev.set_att(20*dB)
        f = 81.2345*MHz
        self.dev.set(frequency=f, phase=.33, amplitude=.89)
        self.set_dataset("ftw_set", self.dev.frequency_to_ftw(f))
        self.set_dataset("ftw_get", self.dev.read32(_AD9910_REG_FTW))

    @kernel
    def read_write64(self):
        self.core.break_realtime()
        self.dev.cpld.init()
        self.dev.init()
        lo = 0x12345678
        hi = 0x09abcdef
        self.dev.write64(_AD9910_REG_PROFILE0, hi, lo)
        self.dev.cpld.io_update.pulse_mu(8)
        read = self.dev.read64(_AD9910_REG_PROFILE0)
        self.set_dataset("write", (int64(hi) << 32) | lo)
        self.set_dataset("read", read)

    @kernel
    def set_speed(self):
        self.core.break_realtime()
        self.dev.cpld.init()
        self.dev.init()
        f = 81.2345*MHz
        n = 10
        t0 = self.core.get_rtio_counter_mu()
        for i in range(n):
            self.dev.set(frequency=f, phase=.33, amplitude=.89)
        self.set_dataset("dt", self.core.mu_to_seconds(
            self.core.get_rtio_counter_mu() - t0)/n)

    @kernel
    def set_speed_mu(self):
        self.core.break_realtime()
        self.dev.cpld.init()
        self.dev.init()
        n = 10
        t0 = self.core.get_rtio_counter_mu()
        for i in range(n):
            self.dev.set_mu(0x12345678, 0x1234, 0x4321)
        self.set_dataset("dt", self.core.mu_to_seconds(
            self.core.get_rtio_counter_mu() - t0)/n)

    @kernel
    def sync_window(self):
        self.core.break_realtime()
        self.dev.cpld.init()
        self.dev.init()
        err = [0] * 32
        for i in range(6):
            self.sync_scan(err, win=i)
            print(err)
            self.core.break_realtime()
        dly, win = self.dev.tune_sync_delay()
        self.sync_scan(err, win=win)
        # FIXME: win + 1  # tighten window by 2*75ps
        # after https://github.com/sinara-hw/Urukul/issues/16
        self.set_dataset("dly", dly)
        self.set_dataset("win", win)
        self.set_dataset("err", err)

    @kernel
    def sync_scan(self, err, win):
        for in_delay in range(len(err)):
            self.dev.set_sync(in_delay=in_delay, window=win)
            self.dev.clear_smp_err()
            # delay(10*us)  # integrate SMP_ERR statistics
            e = urukul_sta_smp_err(self.dev.cpld.sta_read())
            err[in_delay] = (e >> (self.dev.chip_select - 4)) & 1
            delay(50*us)  # slack

    @kernel
    def io_update_delay(self):
        self.core.break_realtime()
        self.dev.cpld.init()
        self.dev.init()
        bins1 = [0]*4
        bins2 = [0]*4
        self.scan_io_delay(bins1, bins2)
        self.set_dataset("bins1", bins1)
        self.set_dataset("bins2", bins2)
        self.set_dataset("dly", self.dev.tune_io_update_delay())

    @kernel
    def scan_io_delay(self, bins1, bins2):
        delay(100*us)
        n = 100
        for i in range(n):
            for j in range(len(bins1)):
                bins1[j] += self.dev.measure_io_update_alignment(j, j + 1)
                bins2[j] += self.dev.measure_io_update_alignment(j, j + 2)
        delay(10*ms)

    @kernel
    def sw_readback(self):
        self.core.break_realtime()
        self.dev.cpld.init()
        self.dev.init()
        self.dev.cfg_sw(0)
        self.dev.sw.on()
        sw_on = (self.dev.cpld.sta_read() >> (self.dev.chip_select - 4)) & 1
        delay(10*us)
        self.dev.sw.off()
        sw_off = (self.dev.cpld.sta_read() >> (self.dev.chip_select - 4)) & 1
        self.set_dataset("sw", (sw_on, sw_off))

    @kernel
    def profile_readback(self):
        self.core.break_realtime()
        self.dev.cpld.init()
        self.dev.init()
        for i in range(8):
            self.dev.set_mu(ftw=i, profile=i)
        ftw = [0] * 8
        for i in range(8):
            self.dev.cpld.set_profile(i)
            # If PROFILE is not alligned to SYNC_CLK a multi-bit change
            # doesn't transfer cleanly. Use IO_UPDATE to load the profile
            # again.
            self.dev.cpld.io_update.pulse_mu(8)
            ftw[i] = self.dev.read32(_AD9910_REG_FTW)
            delay(100*us)
        self.set_dataset("ftw", ftw)


class AD9910Test(ExperimentCase):
    def test_instantiate(self):
        self.execute(AD9910Exp, "instantiate")

    def test_init(self):
        self.execute(AD9910Exp, "init")

    def test_init_fail(self):
        with self.assertRaises(ValueError):
            self.execute(AD9910Exp, "init_fail")

    def test_set_get(self):
        self.execute(AD9910Exp, "set_get")
        ftw_get = self.dataset_mgr.get("ftw_get")
        ftw_set = self.dataset_mgr.get("ftw_set")
        self.assertEqual(ftw_get, ftw_set)

    def test_read_write64(self):
        self.execute(AD9910Exp, "read_write64")
        write = self.dataset_mgr.get("write")
        read = self.dataset_mgr.get("read")
        self.assertEqual(hex(write), hex(read))

    def test_set_speed(self):
        self.execute(AD9910Exp, "set_speed")
        dt = self.dataset_mgr.get("dt")
        print(dt)
        self.assertLess(dt, 70*us)

    def test_set_speed_mu(self):
        self.execute(AD9910Exp, "set_speed_mu")
        dt = self.dataset_mgr.get("dt")
        print(dt)
        self.assertLess(dt, 11*us)

    def test_sync_window(self):
        self.execute(AD9910Exp, "sync_window")
        err = self.dataset_mgr.get("err")
        dly = self.dataset_mgr.get("dly")
        win = self.dataset_mgr.get("win")
        print(dly, win, err)
        # make sure one tap margin on either side of optimal delay
        for i in -1, 0, 1:
            self.assertEqual(err[i + dly], 0)

    def test_io_update_delay(self):
        self.execute(AD9910Exp, "io_update_delay")
        dly = self.dataset_mgr.get("dly")
        bins1 = self.dataset_mgr.get("bins1")
        bins2 = self.dataset_mgr.get("bins2")
        print(dly, bins1, bins2)
        n = max(bins2)
        # no edge at optimal delay
        self.assertEqual(bins2[(dly + 1) & 3], 0)
        # many edges near expected position
        self.assertGreater(bins2[(dly + 3) & 3], n*.9)

    def test_sw_readback(self):
        self.execute(AD9910Exp, "sw_readback")
        self.assertEqual(self.dataset_mgr.get("sw"), (1, 0))

    def test_profile_readback(self):
        self.execute(AD9910Exp, "profile_readback")
        self.assertEqual(self.dataset_mgr.get("ftw"), list(range(8)))
