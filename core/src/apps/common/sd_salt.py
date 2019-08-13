from micropython import const

from trezor import io, ui
from trezor.crypto import hmac
from trezor.crypto.hashlib import sha256
from trezor.ui.confirm import CONFIRMED, Confirm
from trezor.ui.text import Text
from trezor.utils import consteq

from apps.common import storage

if False:
    from typing import Optional


class SdSaltCancelled(Exception):
    pass


SD_SALT_LEN_BYTES = const(32)
SD_SALT_AUTH_TAG_LEN_BYTES = const(16)
SD_SALT_AUTH_KEY_LEN_BYTES = const(16)


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


async def request_sd_salt(salt_auth_key: bytes) -> bytearray:
    device_dir = "/trezor/device_%s" % storage.device.get_device_id()
    salt_path = "%s/salt" % device_dir
    new_salt_path = "%s/salt.new" % device_dir

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
                    salt = bytearray(SD_SALT_LEN_BYTES)  # type: Optional[bytearray]
                    salt_tag = bytearray(SD_SALT_AUTH_TAG_LEN_BYTES)
                    f.read(salt)
                    f.read(salt_tag)
            except OSError:
                salt = None

            try:
                with fs.open(new_salt_path, "r") as f:
                    new_salt = bytearray(SD_SALT_LEN_BYTES)  # type: Optional[bytearray]
                    new_salt_tag = bytearray(SD_SALT_AUTH_TAG_LEN_BYTES)
                    f.read(new_salt)
                    f.read(new_salt_tag)
            except OSError:
                new_salt = None

            if salt is not None and consteq(
                hmac.new(salt_auth_key, salt, sha256).digest()[
                    :SD_SALT_AUTH_TAG_LEN_BYTES
                ],
                salt_tag,
            ):
                return salt
            elif new_salt is not None and consteq(
                hmac.new(salt_auth_key, new_salt, sha256).digest()[
                    :SD_SALT_AUTH_TAG_LEN_BYTES
                ],
                new_salt_tag,
            ):
                # SD salt regeneration was interrupted earlier. Bring into consistent state.
                # TODO Possibly overwrite salt file with random data.
                try:
                    fs.unlink(salt_path)
                except OSError:
                    pass
                fs.rename(new_salt_path, salt_path)
                return new_salt
            else:
                await wrong_card_dialog()
    finally:
        fs.unmount()
        sd.power(False)


async def set_sd_salt(salt: bytes, salt_tag: bytes, filename: str = "salt") -> None:
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
            f.write(salt_tag)
    finally:
        fs.unmount()
        sd.power(False)


async def stage_sd_salt(salt: bytes, salt_tag: bytes) -> None:
    await set_sd_salt(salt, salt_tag, "salt.new")


async def commit_sd_salt() -> None:
    device_dir = "/trezor/device_%s" % storage.device.get_device_id()
    salt_path = "%s/salt" % device_dir
    new_salt_path = "%s/salt.new" % device_dir

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
        fs.rename(new_salt_path, salt_path)
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
