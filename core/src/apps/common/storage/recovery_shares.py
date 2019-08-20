from trezor.crypto import slip39

from apps.common.storage import common

if False:
    from typing import List, Optional

# Mnemonics stored during SLIP-39 recovery process.
# Each mnemonic is stored under key = index.


def set(index: int, mnemonic: str) -> None:
    common._set(common._APP_RECOVERY_SHARES, index, mnemonic.encode())


def get(index: int) -> Optional[str]:
    m = common._get(common._APP_RECOVERY_SHARES, index)
    if m:
        return m.decode()
    return None

def get_index_from_group(index: int, group_index: int) -> Optional[str]:
    m = common._get(common._APP_RECOVERY_SHARES, index + (group_index-1) * 16)
    if m:
        return m.decode()
    return None


def fetch(group_count: int = 1) -> List[str]:
    mnemonics = []
    for index in range(0, slip39.MAX_SHARE_COUNT * group_count):
        m = get(index)
        if m:
            mnemonics.append(m)
    return mnemonics


def delete() -> None:
    for index in range(0, slip39.MAX_SHARE_COUNT):
        common._delete(common._APP_RECOVERY_SHARES, index)
