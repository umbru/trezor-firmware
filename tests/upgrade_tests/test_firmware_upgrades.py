#!/usr/bin/env python3
import os

from emulator_wrapper import EmulatorWrapper
from trezorlib import btc, debuglink, device
from trezorlib.tools import H_

MNEMONIC = " ".join(["all"] * 12)
PATH = [H_(44), H_(0), H_(0), 0, 0]
ADDRESS = "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
LABEL = "test"
LANGUAGE = "english"
STRENGTH = 128

ROOT = os.path.dirname(os.path.abspath(__file__)) + "/../../"
CORE_BUILD = ROOT + "core/build/unix/micropython"
LEGACY_BUILD = ROOT + "legacy/firmware/trezor.elf"
BIN_DIR = os.path.dirname(os.path.abspath(__file__)) + "/emulators"


def check_version(tag, ver_emu):
    if tag.startswith("v") and len(tag.split(".")) == 3:
        assert tag == "v" + ".".join(["%d" % i for i in ver_emu])


def test_upgrade_load(gen, from_tag, to_tag):
    def asserts(tag, client):
        check_version(tag, emu.client.version)
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.language == LANGUAGE
        assert btc.get_address(client, "Bitcoin", PATH) == ADDRESS

    with EmulatorWrapper(gen, from_tag) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client,
            mnemonic=MNEMONIC,
            pin="",
            passphrase_protection=False,
            label=LABEL,
            language=LANGUAGE,
        )
        device_id = emu.client.features.device_id
        asserts(from_tag, emu.client)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)


def test_upgrade_reset(gen, from_tag, to_tag):
    def asserts(tag, client):
        check_version(tag, emu.client.version)
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.language == LANGUAGE
        assert not client.features.needs_backup
        assert not client.features.unfinished_backup
        assert not client.features.no_backup

    with EmulatorWrapper(gen, from_tag) as emu:
        device.reset(
            emu.client,
            display_random=False,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label=LABEL,
            language=LANGUAGE,
        )
        device_id = emu.client.features.device_id
        asserts(from_tag, emu.client)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)


def test_upgrade_reset_skip_backup(gen, from_tag, to_tag):
    def asserts(tag, client):
        check_version(tag, emu.client.version)
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.language == LANGUAGE
        assert client.features.needs_backup
        assert not client.features.unfinished_backup
        assert not client.features.no_backup

    with EmulatorWrapper(gen, from_tag) as emu:
        device.reset(
            emu.client,
            display_random=False,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label=LABEL,
            language=LANGUAGE,
            skip_backup=True,
        )
        device_id = emu.client.features.device_id
        asserts(from_tag, emu.client)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)


def test_upgrade_reset_no_backup(gen, from_tag, to_tag):
    def asserts(tag, client):
        check_version(tag, emu.client.version)
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.language == LANGUAGE
        assert not client.features.needs_backup
        assert not client.features.unfinished_backup
        assert client.features.no_backup

    with EmulatorWrapper(gen, from_tag) as emu:
        device.reset(
            emu.client,
            display_random=False,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label=LABEL,
            language=LANGUAGE,
            no_backup=True,
        )
        device_id = emu.client.features.device_id
        asserts(from_tag, emu.client)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)


def check_file(gen, tag):
    if tag.startswith("/"):
        filename = tag
    else:
        filename = "%s/trezor-emu-%s-%s" % (BIN_DIR, gen, tag)
    if not os.path.exists(filename):
        raise ValueError(filename + " not found. Do not forget to build firmware.")


def get_tags():
    files = os.listdir(BIN_DIR)
    if not files:
        raise ValueError(
            "No files found. Use download_emulators.sh to download emulators."
        )
    core_tags = []
    legacy_tags = []
    for f in files:
        if "core" in f:
            core_tags.append(
                f[-6:]
            )  # TODO: this is very bad, it does not work for different version lengths
        elif "legacy" in f:
            legacy_tags.append(f[-6:])  # TODO: as above
    return core_tags, legacy_tags


def try_tags(gen, tags_from, tag_to):
    for tag_from in tags_from + [tag_to]:
        check_file(gen, tag_from)
        print("[%s] %s => %s" % (gen, tag_from, tag_to))
        print("- test_upgrade_load")
        test_upgrade_load(gen, tag_from, tag_to)
        if gen != "core":
            print("- test_upgrade_reset")
            test_upgrade_reset(gen, tag_from, tag_to)
            print("- test_upgrade_reset_skip_backup")
            test_upgrade_reset(gen, tag_from, tag_to)
            print("- test_upgrade_reset_no_backup")
            test_upgrade_reset(gen, tag_from, tag_to)


core_tags, legacy_tags = get_tags()

print("Found versions for CORE: ", core_tags)
print("Found versions for LEGACY: ", legacy_tags)
print()

# TODO: this is a bit stupid - we convert the filenames to tags, to be later
# converted to filenames again in emulator wrapper
try_tags("core", core_tags, CORE_BUILD)
try_tags("legacy", legacy_tags, LEGACY_BUILD)

print("ALL OK")
