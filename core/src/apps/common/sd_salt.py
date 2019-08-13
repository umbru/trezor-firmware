from trezor import io, ui
from trezor.crypto.hashlib import sha256
from trezor.ui.confirm import CONFIRMED, Confirm
from trezor.ui.text import Text

from apps.common import storage


class SdSaltCancelled(Exception):
    pass


SD_SALT_LEN_BYTES = 32


async def wrong_card_dialog() -> None:
    text = Text("SD card", ui.ICON_WRONG)
    text.normal("Wrong SD card inserted.", "Please insert a different", "card.")
    dialog = Confirm(text)
    if await dialog is not CONFIRMED:
        raise SdSaltCancelled


async def insert_card_dialog() -> None:
    text = Text("SD card")
    text.normal("Please insert your SD card.")
    dialog = Confirm(text)
    if await dialog is not CONFIRMED:
        raise SdSaltCancelled


async def request_sd_salt(salt_hash: bytes) -> bytearray:
    device_dir = "/trezor/device_%s" % storage.device.get_device_id()
    salt_path = "%s/salt" % device_dir
    salt_new_path = "%s/salt.new" % device_dir

    sd = io.SDCard()
    fs = io.FatFS()
    try:
        while True:
            if not sd.power(True):
                await insert_card_dialog()
                continue

            fs.mount()

            # Load salt and salt.new if it exists.
            try:
                with fs.open(salt_path, "r") as f:
                    salt = bytearray(SD_SALT_LEN_BYTES)
                    f.read(salt)
            except OSError:
                salt = None

            try:
                with fs.open(salt_new_path, "r") as f:
                    salt_new = bytearray(SD_SALT_LEN_BYTES)
                    f.read(salt_new)
            except OSError:
                salt_new = None

            if salt is not None and sha256(salt).digest() == salt_hash:
                return salt
            elif salt_new is not None and sha256(salt_new).digest() == salt_hash:
                # SD salt regeneration was interrupted earlier. Bring into consistent state.
                # TODO Possibly overwrite salt file with random data.
                try:
                    fs.unlink(salt_path)
                except OSError:
                    pass
                fs.rename(salt_new_path, salt_path)
                return salt
            else:
                await wrong_card_dialog()
    finally:
        fs.unmount()
        sd.power(False)


async def set_sd_salt(salt: bytes, filename: str = "salt") -> None:
    device_dir = "/trezor/device_%s" % storage.device.get_device_id()
    salt_path = "%s/%s" % (device_dir, filename)

    sd = io.SDCard()
    fs = io.FatFS()
    try:
        sd.power(True)
        fs.mount()
        try:
            fs.mkdir("/trezor")
            fs.mkdir(device_dir)
        except OSError:
            # Directory already exists.
            pass
        with fs.open(salt_path, "w") as f:
            f.write(salt)
    finally:
        fs.unmount()
        sd.power(False)


async def stage_sd_salt(salt: bytes) -> None:
    await set_sd_salt(salt, "salt.new")


async def commit_sd_salt() -> None:
    device_dir = "/trezor/device_%s" % storage.device.get_device_id()
    salt_path = "%s/salt" % device_dir
    salt_new_path = "%s/salt.new" % device_dir

    sd = io.SDCard()
    fs = io.FatFS()
    try:
        sd.power(True)
        fs.mount()
        # TODO Possibly overwrite salt file with random data.
        try:
            fs.unlink(salt_path)
        except OSError:
            pass
        fs.rename(salt_new_path, salt_path)
    finally:
        fs.unmount()
        sd.power(False)


async def remove_sd_salt() -> None:
    device_dir = "/trezor/device_%s" % storage.device.get_device_id()
    salt_path = "%s/salt" % device_dir

    sd = io.SDCard()
    fs = io.FatFS()
    try:
        sd.power(True)
        fs.mount()
        # TODO Possibly overwrite salt file with random data.
        fs.unlink(salt_path)
    finally:
        fs.unmount()
        sd.power(False)
