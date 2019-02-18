#!/usr/bin/env python3

import argparse
import os
import subprocess
import struct

from migen import *
from migen.genlib.cdc import MultiReg

from misoc.interconnect.csr import *
from misoc.cores import gpio
from misoc.cores.a7_gtp import *
from misoc.targets.sayma_rtm import BaseSoC
from misoc.integration.builder import Builder, builder_args, builder_argdict

from artiq.gateware import rtio
from artiq.gateware.rtio.phy import ttl_serdes_7series
from artiq.gateware.drtio.transceiver import gtp_7series
from artiq.gateware.drtio.siphaser import SiPhaser7Series
from artiq.gateware.drtio.rx_synchronizer import XilinxRXSynchronizer
from artiq.gateware.drtio import *
from artiq.build_soc import add_identifier
from artiq import __artiq_dir__ as artiq_dir


def fix_serdes_timing_path(platform):
    # ignore timing of path from OSERDESE2 through the pad to ISERDESE2
    platform.add_platform_command(
        "set_false_path -quiet "
        "-through [get_pins -filter {{REF_PIN_NAME == OQ || REF_PIN_NAME == TQ}} "
            "-of [get_cells -filter {{REF_NAME == OSERDESE2}}]] "
        "-to [get_pins -filter {{REF_PIN_NAME == D}} "
            "-of [get_cells -filter {{REF_NAME == ISERDESE2}}]]"
    )


class _RTIOClockMultiplier(Module, AutoCSR):
    def __init__(self, rtio_clk_freq):
        self.pll_reset = CSRStorage(reset=1)
        self.pll_locked = CSRStatus()
        self.clock_domains.cd_rtiox4 = ClockDomain(reset_less=True)

        # See "Global Clock Network Deskew Using Two BUFGs" in ug472.
        clkfbout = Signal()
        clkfbin = Signal()
        rtiox4_clk = Signal()
        pll_locked = Signal()
        self.specials += [
            Instance("MMCME2_BASE",
                p_CLKIN1_PERIOD=1e9/rtio_clk_freq,
                i_CLKIN1=ClockSignal("rtio"),
                i_RST=self.pll_reset.storage,
                o_LOCKED=pll_locked,

                p_CLKFBOUT_MULT_F=8.0, p_DIVCLK_DIVIDE=1,

                o_CLKFBOUT=clkfbout, i_CLKFBIN=clkfbin,

                p_CLKOUT0_DIVIDE_F=2.0, o_CLKOUT0=rtiox4_clk,
            ),
            Instance("BUFG", i_I=clkfbout, o_O=clkfbin),
            Instance("BUFG", i_I=rtiox4_clk, o_O=self.cd_rtiox4.clk),

            MultiReg(pll_locked, self.pll_locked.status)
        ]


class _SatelliteBase(BaseSoC):
    mem_map = {
        "drtioaux": 0x50000000,
    }
    mem_map.update(BaseSoC.mem_map)

    def __init__(self, rtio_clk_freq=150e6, **kwargs):
        BaseSoC.__init__(self,
                 cpu_type="or1k",
                 **kwargs)
        add_identifier(self)

        platform = self.platform

        disable_si5324_ibuf = Signal(reset=1)
        disable_si5324_ibuf.attr.add("no_retiming")
        si5324_clkout = platform.request("si5324_clkout")
        si5324_clkout_buf = Signal()
        self.specials += Instance("IBUFDS_GTE2",
            i_CEB=disable_si5324_ibuf,
            i_I=si5324_clkout.p, i_IB=si5324_clkout.n,
            o_O=si5324_clkout_buf)
        qpll_drtio_settings = QPLLSettings(
            refclksel=0b001,
            fbdiv=4,
            fbdiv_45=5,
            refclk_div=1)
        qpll = QPLL(si5324_clkout_buf, qpll_drtio_settings)
        self.submodules += qpll

        self.submodules.drtio_transceiver = gtp_7series.GTP(
            qpll_channel=qpll.channels[0],
            data_pads=[platform.request("sata", 0)],
            sys_clk_freq=self.clk_freq,
            rtio_clk_freq=rtio_clk_freq)
        self.csr_devices.append("drtio_transceiver")
        self.sync += disable_si5324_ibuf.eq(
            ~self.drtio_transceiver.stable_clkin.storage)

        self.submodules.rtio_tsc = rtio.TSC("sync", glbl_fine_ts_width=3)

        cdr = ClockDomainsRenamer({"rtio_rx": "rtio_rx0"})

        self.submodules.rx_synchronizer = cdr(XilinxRXSynchronizer())
        core = cdr(DRTIOSatellite(
            self.rtio_tsc, self.drtio_transceiver.channels[0],
            self.rx_synchronizer))
        self.submodules.drtiosat = core
        self.csr_devices.append("drtiosat")

        coreaux = cdr(DRTIOAuxController(core.link_layer))
        self.submodules.drtioaux0 = coreaux
        self.csr_devices.append("drtioaux0")

        memory_address = self.mem_map["drtioaux"]
        self.add_wb_slave(memory_address, 0x800,
                          coreaux.bus)
        self.add_memory_region("drtioaux0_mem", memory_address | self.shadow_base, 0x800)

        self.config["HAS_DRTIO"] = None
        self.add_csr_group("drtioaux", ["drtioaux0"])
        self.add_memory_group("drtioaux_mem", ["drtioaux0_mem"])

        self.config["RTIO_FREQUENCY"] = str(rtio_clk_freq/1e6)
        self.submodules.siphaser = SiPhaser7Series(
            si5324_clkin=platform.request("si5324_clkin"),
            rx_synchronizer=self.rx_synchronizer,
            ref_clk=self.crg.cd_sys.clk, ref_div2=True,
            rtio_clk_freq=rtio_clk_freq)
        platform.add_false_path_constraints(
            self.crg.cd_sys.clk, self.siphaser.mmcm_freerun_output)
        self.csr_devices.append("siphaser")
        i2c = self.platform.request("i2c")
        self.submodules.i2c = gpio.GPIOTristate([i2c.scl, i2c.sda])
        self.csr_devices.append("i2c")
        self.config["I2C_BUS_COUNT"] = 1
        self.config["HAS_SI5324"] = None
        self.config["SI5324_SOFT_RESET"] = None

        rtio_clk_period = 1e9/rtio_clk_freq
        gtp = self.drtio_transceiver.gtps[0]
        platform.add_period_constraint(gtp.txoutclk, rtio_clk_period)
        platform.add_period_constraint(gtp.rxoutclk, rtio_clk_period)
        platform.add_false_path_constraints(
            self.crg.cd_sys.clk,
            gtp.txoutclk, gtp.rxoutclk)

        self.submodules.rtio_crg = _RTIOClockMultiplier(rtio_clk_freq)
        self.csr_devices.append("rtio_crg")
        fix_serdes_timing_path(platform)

    def add_rtio(self, rtio_channels):
        self.submodules.rtio_moninj = rtio.MonInj(rtio_channels)
        self.csr_devices.append("rtio_moninj")

        self.submodules.local_io = SyncRTIO(self.rtio_tsc, rtio_channels)
        self.comb += self.drtiosat.async_errors.eq(self.local_io.async_errors)
        self.comb += self.drtiosat.cri.connect(self.local_io.cri)


class Satellite(_SatelliteBase):
    def __init__(self, **kwargs):
        _SatelliteBase.__init__(self, **kwargs)

        self.rtio_channels = []
        phy = ttl_serdes_7series.Output_8X(self.platform.request("allaki0_rfsw0"))
        self.submodules += phy
        self.rtio_channels.append(rtio.Channel.from_phy(phy))
        phy = ttl_serdes_7series.Output_8X(self.platform.request("allaki0_rfsw1"))
        self.submodules += phy
        self.rtio_channels.append(rtio.Channel.from_phy(phy))

        self.add_rtio(self.rtio_channels)


class SatmanSoCBuilder(Builder):
    def __init__(self, *args, **kwargs):
        Builder.__init__(self, *args, **kwargs)
        firmware_dir = os.path.join(artiq_dir, "firmware")
        self.software_packages = []
        self.add_software_package("satman", os.path.join(firmware_dir, "satman"))

    def initialize_memory(self):
        satman = os.path.join(self.output_dir, "software", "satman",
                              "satman.bin")
        with open(satman, "rb") as boot_file:
            boot_data = []
            unpack_endian = ">I"
            while True:
                w = boot_file.read(4)
                if not w:
                    break
                boot_data.append(struct.unpack(unpack_endian, w)[0])

        self.soc.main_ram.mem.init = boot_data


def main():
    parser = argparse.ArgumentParser(
        description="ARTIQ device binary builder for Kasli systems")
    builder_args(parser)
    parser.set_defaults(output_dir="artiq_sayma_rtm")
    args = parser.parse_args()

    soc = Satellite()
    builder = SatmanSoCBuilder(soc, **builder_argdict(args))
    try:
        builder.build()
    except subprocess.CalledProcessError as e:
        raise SystemExit("Command {} failed".format(" ".join(e.cmd)))


if __name__ == "__main__":
    main()
