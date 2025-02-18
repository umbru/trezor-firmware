from trezor import loop, ui, utils
from trezor.messages import ButtonRequestType
from trezor.messages.ButtonAck import ButtonAck
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.ui.text import Text

if __debug__:
    from apps.debug import confirm_signal


async def naive_pagination(
    ctx, lines, title, icon=ui.ICON_RESET, icon_color=ui.ORANGE, per_page=5
):
    from trezor.ui.scroll import CANCELLED, CONFIRMED, PaginatedWithButtons

    pages = []
    page_lines = paginate_lines(lines, per_page)

    for i, lines in enumerate(page_lines):
        if len(page_lines) > 1:
            paging = "%s/%s" % (i + 1, len(page_lines))
        else:
            paging = ""
        text = Text("%s %s" % (title, paging), icon, icon_color)
        text.normal(*lines)
        pages.append(text)

    paginated = PaginatedWithButtons(pages, one_by_one=True)

    while True:
        await ctx.call(ButtonRequest(code=ButtonRequestType.SignTx), ButtonAck)
        if __debug__:
            result = await loop.race(paginated, confirm_signal)
        else:
            result = await paginated
        if result is CONFIRMED:
            return True
        if result is CANCELLED:
            return False


def paginate_lines(lines, lines_per_page=5):
    """Paginates lines across pages with preserving formatting modifiers (e.g., mono)"""
    pages = []
    cpage = []
    nlines = 0
    last_modifier = None
    for line in lines:
        cpage.append(line)
        if not isinstance(line, int):
            nlines += 1
        else:
            last_modifier = line

        if nlines >= lines_per_page:
            pages.append(cpage)
            cpage = []
            nlines = 0
            if last_modifier is not None:
                cpage.append(last_modifier)

    if nlines > 0:
        pages.append(cpage)
    return pages


def format_amount(value):
    return "%s XMR" % utils.format_amount(value, 12)


def split_address(address):
    return utils.chunks(address, 16)
