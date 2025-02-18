# generated from coininfo.py.mako
# do not edit manually!
from trezor.crypto.base58 import blake256d_32, groestl512d_32, keccak_32, sha256d_32
from trezor.crypto.scripts import blake256_ripemd160_digest, sha256_ripemd160_digest

# flake8: noqa


class CoinInfo:
    def __init__(
        self,
        coin_name: str,
        coin_shortcut: str,
        address_type: int,
        address_type_p2sh: int,
        maxfee_kb: int,
        signed_message_header: str,
        xpub_magic: int,
        xpub_magic_segwit_p2sh: int,
        xpub_magic_segwit_native: int,
        bech32_prefix: str,
        cashaddr_prefix: str,
        slip44: int,
        segwit: bool,
        fork_id: int,
        force_bip143: bool,
        bip115: bool,
        decred: bool,
        negative_fee: bool,
        curve_name: str,
        confidential_assets: dict,
    ):
        self.coin_name = coin_name
        self.coin_shortcut = coin_shortcut
        self.address_type = address_type
        self.address_type_p2sh = address_type_p2sh
        self.maxfee_kb = maxfee_kb
        self.signed_message_header = signed_message_header
        self.xpub_magic = xpub_magic
        self.xpub_magic_segwit_p2sh = xpub_magic_segwit_p2sh
        self.xpub_magic_segwit_native = xpub_magic_segwit_native
        self.bech32_prefix = bech32_prefix
        self.cashaddr_prefix = cashaddr_prefix
        self.slip44 = slip44
        self.segwit = segwit
        self.fork_id = fork_id
        self.force_bip143 = force_bip143
        self.bip115 = bip115
        self.decred = decred
        self.negative_fee = negative_fee
        self.curve_name = curve_name
        self.confidential_assets = confidential_assets
        if curve_name == "secp256k1-groestl":
            self.b58_hash = groestl512d_32
            self.sign_hash_double = False
            self.script_hash = sha256_ripemd160_digest
        elif curve_name == "secp256k1-decred":
            self.b58_hash = blake256d_32
            self.sign_hash_double = False
            self.script_hash = blake256_ripemd160_digest
        elif curve_name == "secp256k1-smart":
            self.b58_hash = keccak_32
            self.sign_hash_double = False
            self.script_hash = sha256_ripemd160_digest
        else:
            self.b58_hash = sha256d_32
            self.sign_hash_double = True
            self.script_hash = sha256_ripemd160_digest

    def __eq__(self, other):
        if not isinstance(other, CoinInfo):
            return NotImplemented
        return self.coin_name == other.coin_name


# fmt: off
<%
def hexfmt(x):
    if x is None:
        return None
    else:
        return "0x{:08x}".format(x)

def optional_dict(x):
    if x is None:
        return None
    return dict(x)

ATTRIBUTES = (
    ("coin_name", lambda _: "name"),
    ("coin_shortcut", black_repr),
    ("address_type", int),
    ("address_type_p2sh", int),
    ("maxfee_kb", int),
    ("signed_message_header", black_repr),
    ("xpub_magic", hexfmt),
    ("xpub_magic_segwit_p2sh", hexfmt),
    ("xpub_magic_segwit_native", hexfmt),
    ("bech32_prefix", black_repr),
    ("cashaddr_prefix", black_repr),
    ("slip44", int),
    ("segwit", bool),
    ("fork_id", black_repr),
    ("force_bip143", bool),
    ("bip115", bool),
    ("decred", bool),
    ("negative_fee", bool),
    ("curve_name", lambda r: repr(r.replace("_", "-"))),
    ("confidential_assets", optional_dict),
)
%>\
def by_name(name: str) -> CoinInfo:
    if False:
        pass
% for coin in supported_on("trezor2", bitcoin):
    elif name == ${black_repr(coin["coin_name"])}:
        return CoinInfo(
            % for attr, func in ATTRIBUTES:
            ${attr}=${func(coin[attr])},
            % endfor
        )
% endfor
    raise ValueError('Unknown coin name "%s"' % name)
