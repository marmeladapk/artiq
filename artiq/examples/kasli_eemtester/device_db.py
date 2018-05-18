core_addr = "192.168.95.175"

device_db = {
    "core": {
        "type": "local",
        "module": "artiq.coredevice.core",
        "class": "Core",
        "arguments": {"host": core_addr, "ref_period": 1e-9}
    },
    "core_log": {
        "type": "controller",
        "host": "::1",
        "port": 1068,
        "command": "aqctl_corelog -p {port} --bind {bind} " + core_addr
    },
    "core_cache": {
        "type": "local",
        "module": "artiq.coredevice.cache",
        "class": "CoreCache"
    },
    "core_dma": {
        "type": "local",
        "module": "artiq.coredevice.dma",
        "class": "CoreDMA"
    },
    "i2c_rj45_dir": {
        "type": "local",
        "module": "artiq.coredevice.pcf8574a",
        "class": "PCF8574A",
        "arguments": {"address": 0x7c}
    },
    "i2c_switch0": {
        "type": "local",
        "module": "artiq.coredevice.i2c",
        "class": "PCA9548",
        "arguments": {"address": 0xe0}
    },
    "i2c_switch1": {
        "type": "local",
        "module": "artiq.coredevice.i2c",
        "class": "PCA9548",
        "arguments": {"address": 0xe2}
    },
}
dios = 3
channel_num = 0

for i in range(channel_num, channel_num + dios*8):
    device_db["ttl" + str(i)] = {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",  # if i < 4 else "TTLOut",
        "arguments": {"channel": i},
    }
    channel_num += 1

device_db.update(
    spi_sampler0_adc={
        "type": "local",
        "module": "artiq.coredevice.spi2",
        "class": "SPIMaster",
        "arguments": {"channel": channel_num}
    },
    spi_sampler0_pgia={
        "type": "local",
        "module": "artiq.coredevice.spi2",
        "class": "SPIMaster",
        "arguments": {"channel": channel_num+1}
    },
    ttl_sampler0_cnv={
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLOut",
        "arguments": {"channel": channel_num+2}
    },
    sampler0={
        "type": "local",
        "module": "artiq.coredevice.sampler",
        "class": "Sampler",
        "arguments": {
            "spi_adc_device": "spi_sampler0_adc",
            "spi_pgia_device": "spi_sampler0_pgia",
            "cnv_device": "ttl_sampler0_cnv",
        }
    }
)
channel_num += 3

# device_db.update(
#     spi_urukul0={
#         "type": "local",
#         "module": "artiq.coredevice.spi2",
#         "class": "SPIMaster",
#         "arguments": {"channel": channel_num}
#     },
#     ttl_urukul0_io_update={
#         "type": "local",
#         "module": "artiq.coredevice.ttl",
#         "class": "TTLOut",
#         "arguments": {"channel": channel_num+1}
#     },
#     ttl_urukul0_sw0={
#         "type": "local",
#         "module": "artiq.coredevice.ttl",
#         "class": "TTLOut",
#         "arguments": {"channel": channel_num+2}
#     },
#     ttl_urukul0_sw1={
#         "type": "local",
#         "module": "artiq.coredevice.ttl",
#         "class": "TTLOut",
#         "arguments": {"channel": channel_num+3}
#     },
#     ttl_urukul0_sw2={
#         "type": "local",
#         "module": "artiq.coredevice.ttl",
#         "class": "TTLOut",
#         "arguments": {"channel": channel_num+4}
#     },
#     ttl_urukul0_sw3={
#         "type": "local",
#         "module": "artiq.coredevice.ttl",
#         "class": "TTLOut",
#         "arguments": {"channel": channel_num+5}
#     },
#     urukul0_cpld={
#         "type": "local",
#         "module": "artiq.coredevice.urukul",
#         "class": "CPLD",
#         "arguments": {
#             "spi_device": "spi_urukul0",
#             "io_update_device": "ttl_urukul0_io_update",
#             "refclk": 125e6,
#             "clk_sel": 1
#         }
#     }
# )
# channel_num += 6
#
# for i in range(4):
#     device_db["urukul0_ch" + str(i)] = {
#         "type": "local",
#         "module": "artiq.coredevice.ad9912",
#         "class": "AD9912",
#         "arguments": {
#             "pll_n": 8, #was 32
#             "chip_select": 4 + i,
#             "cpld_device": "urukul0_cpld",
#             "sw_device": "ttl_urukul0_sw" + str(i)
#         }
#     }

device_db.update(
    spi_zotino0={
        "type": "local",
        "module": "artiq.coredevice.spi2",
        "class": "SPIMaster",
        "arguments": {"channel": channel_num}
    },
    ttl_zotino0_ldac={
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLOut",
        "arguments": {"channel": channel_num+1}
    },
    ttl_zotino0_clr={
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLOut",
        "arguments": {"channel": channel_num+2}
    },
    zotino0={
        "type": "local",
        "module": "artiq.coredevice.zotino",
        "class": "Zotino",
        "arguments": {
            "spi_device": "spi_zotino0",
            "ldac_device": "ttl_zotino0_ldac",
            "clr_device": "ttl_zotino0_clr"
        }
    }
)
channel_num += 3

device_db.update(
    led0={
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLOut",
        "arguments": {"channel": channel_num}
    },
    led1={
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLOut",
        "arguments": {"channel": channel_num+1}
    }
)
channel_num += 2