from trezor import config, ui, wire
from trezor.crypto import random
from trezor.crypto.hashlib import sha256
from trezor.messages import SdSaltOperationType
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.text import Text

from apps.common.confirm import require_confirm
from apps.common.sd_salt import (
    SD_SALT_LEN_BYTES,
    commit_sd_salt,
    remove_sd_salt,
    request_sd_salt,
    set_sd_salt,
    stage_sd_salt,
)
from apps.common.storage import device
from apps.management.change_pin import request_pin_ack

if False:
    from trezor.messages.SdSalt import SdSalt


async def sd_salt(ctx: wire.Context, msg: SdSalt) -> Success:
    if msg.operation == SdSaltOperationType.ENABLE:
        return await sd_salt_enable(ctx, msg)
    elif msg.operation == SdSaltOperationType.DISABLE:
        return await sd_salt_disable(ctx, msg)
    elif msg.operation == SdSaltOperationType.REGENERATE:
        return await sd_salt_regenerate(ctx, msg)
    else:
        raise wire.ProcessError("Unknown operation")


async def sd_salt_enable(ctx: wire.Context, msg: SdSalt) -> Success:
    salt_hash = device.get_sd_salt_hash()
    if salt_hash is not None:
        raise wire.ProcessError("SD card salt already enabled")

    await require_confirm_sd_salt(ctx, msg)

    # Get the current PIN.
    if config.has_pin():
        pin = pin_to_int(await request_pin_ack(ctx, "Enter PIN", config.get_pin_rem()))
    else:
        pin = pin_to_int("")

    # Check PIN and write salt.
    salt = random.bytes(SD_SALT_LEN_BYTES)
    try:
        await set_sd_salt(salt)
    except Exception:
        raise wire.ProcessError("Failed to write SD card salt")

    if not config.change_pin(pin, pin, None, salt):
        try:
            await remove_sd_salt()
        except Exception:
            pass
        raise wire.PinInvalid("PIN invalid")

    device.set_sd_salt_hash(sha256(salt).digest())

    return Success(message="SD card salt enabled")


async def sd_salt_disable(ctx: wire.Context, msg: SdSalt) -> Success:
    salt_hash = device.get_sd_salt_hash()
    if salt_hash is None:
        raise wire.ProcessError("SD card salt not enabled")

    # Confirm that user wants to proceed with the operation.
    await require_confirm_sd_salt(ctx, msg)

    # Get the current salt from the SD card.
    try:
        salt = await request_sd_salt(salt_hash)
    except Exception:
        raise wire.ProcessError("Failed to load SD card salt")

    # Get the current PIN.
    if config.has_pin():
        pin = pin_to_int(await request_pin_ack(ctx, "Enter PIN", config.get_pin_rem()))
    else:
        pin = pin_to_int("")

    # Check PIN and remove salt.
    if not config.change_pin(pin, pin, salt, None):
        raise wire.PinInvalid("PIN invalid")

    device.set_sd_salt_hash(None)

    try:
        await remove_sd_salt()
    except Exception:
        pass

    return Success(message="SD card salt disabled")


async def sd_salt_regenerate(ctx: wire.Context, msg: SdSalt) -> Success:
    salt_hash = device.get_sd_salt_hash()
    if salt_hash is None:
        raise wire.ProcessError("SD card salt not enabled")

    # Confirm that user wants to proceed with the operation.
    await require_confirm_sd_salt(ctx, msg)

    # Get the current salt from the SD card.
    try:
        old_salt = await request_sd_salt(salt_hash)
    except Exception:
        raise wire.ProcessError("Failed to load SD card salt")

    # Get the current PIN.
    if config.has_pin():
        pin = pin_to_int(await request_pin_ack(ctx, "Enter PIN", config.get_pin_rem()))
    else:
        pin = pin_to_int("")

    # Check PIN and change salt.
    new_salt = random.bytes(SD_SALT_LEN_BYTES)
    try:
        await stage_sd_salt(new_salt)
    except Exception:
        raise wire.ProcessError("Failed to write SD card salt")

    if not config.change_pin(pin, pin, old_salt, new_salt):
        raise wire.PinInvalid("PIN invalid")

    device.set_sd_salt_hash(sha256(new_salt).digest())

    try:
        await commit_sd_salt()
    except Exception:
        raise wire.ProcessError("Failed to write SD card salt")

    return Success(message="SD card salt regenerated")


def require_confirm_sd_salt(ctx: wire.Context, msg: SdSalt) -> None:
    if msg.operation == SdSaltOperationType.ENABLE:
        text = Text("Enable SD salt", ui.ICON_CONFIG)
        text.normal(
            "Do you really want to", "encrypt the storage", "with SD card salt?"
        )
    elif msg.operation == SdSaltOperationType.DISABLE:
        text = Text("Disable SD salt", ui.ICON_CONFIG)
        text.normal("Do you really want to", "remove SD card salt", "protection?")
    elif msg.operation == SdSaltOperationType.REGENERATE:
        text = Text("Regenerate SD salt", ui.ICON_CONFIG)
        text.normal(
            "Do you really want to",
            "replace the current",
            "SD card salt with a",
            "newly generated one?",
        )
    else:
        raise wire.ProcessError("Unknown operation")

    return require_confirm(ctx, text)
