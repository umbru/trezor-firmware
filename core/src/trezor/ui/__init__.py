import math
import utime
from micropython import const
from trezorui import Display

from trezor import io, loop, res, utils

if False:
    from typing import Any, Generator, Iterable, Tuple, TypeVar

    Pos = Tuple[int, int]
    Area = Tuple[int, int, int, int]
    ResultValue = TypeVar("ResultValue")

# all rendering is done through a singleton of `Display`
display = Display()

# re-export constants from modtrezorui
NORMAL = Display.FONT_NORMAL
BOLD = Display.FONT_BOLD
MONO = Display.FONT_MONO
MONO_BOLD = Display.FONT_MONO_BOLD
SIZE = Display.FONT_SIZE
WIDTH = Display.WIDTH
HEIGHT = Display.HEIGHT

# viewport margins
VIEWX = const(6)
VIEWY = const(9)

# channel used to cancel layouts, see `Cancelled` exception
layout_chan = loop.chan()

# in debug mode, display an indicator in top right corner
if __debug__:

    def debug_display_refresh() -> None:
        display.bar(Display.WIDTH - 8, 0, 8, 8, 0xF800)
        display.refresh()
        if utils.SAVE_SCREEN:
            display.save("refresh")

    loop.after_step_hook = debug_display_refresh

# in both debug and production, emulator needs to draw the screen explicitly
elif utils.EMULATOR:
    loop.after_step_hook = display.refresh


def lerpi(a: int, b: int, t: float) -> int:
    return int(a + t * (b - a))


def rgb(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)


def blend(ca: int, cb: int, t: float) -> int:
    return rgb(
        lerpi((ca >> 8) & 0xF8, (cb >> 8) & 0xF8, t),
        lerpi((ca >> 3) & 0xFC, (cb >> 3) & 0xFC, t),
        lerpi((ca << 3) & 0xF8, (cb << 3) & 0xF8, t),
    )


# import style later to avoid circular dep
from trezor.ui import style  # isort:skip

# import style definitions into namespace
from trezor.ui.style import *  # isort:skip # noqa: F401,F403


def pulse(coef: int) -> float:
    # normalize sin from interval -1:1 to 0:1
    return 0.5 + 0.5 * math.sin(utime.ticks_us() / coef)


async def click() -> Pos:
    touch = loop.wait(io.TOUCH)
    while True:
        ev, *pos = await touch
        if ev == io.TOUCH_START:
            break
    while True:
        ev, *pos = await touch
        if ev == io.TOUCH_END:
            break
    return pos  # type: ignore


def backlight_fade(val: int, delay: int = 14000, step: int = 15) -> None:
    if __debug__:
        if utils.DISABLE_FADE:
            display.backlight(val)
            return
    current = display.backlight()
    if current > val:
        step = -step
    for i in range(current, val, step):
        display.backlight(i)
        utime.sleep_us(delay)


def header(
    title: str,
    icon: str = style.ICON_DEFAULT,
    fg: int = style.FG,
    bg: int = style.BG,
    ifg: int = style.GREEN,
) -> None:
    if icon is not None:
        display.icon(14, 15, res.load(icon), ifg, bg)
    display.text(44, 35, title, BOLD, fg, bg)


def header_warning(message: str, clear: bool = True) -> None:
    display.bar(0, 0, WIDTH, 30, style.YELLOW)
    display.text_center(WIDTH // 2, 22, message, BOLD, style.BLACK, style.YELLOW)
    if clear:
        display.bar(0, 30, WIDTH, HEIGHT - 30, style.BG)


def header_error(message: str, clear: bool = True) -> None:
    display.bar(0, 0, WIDTH, 30, style.RED)
    display.text_center(WIDTH // 2, 22, message, BOLD, style.WHITE, style.RED)
    if clear:
        display.bar(0, 30, WIDTH, HEIGHT - 30, style.BG)


def grid(
    i: int,  # i-th cell of the table of which we wish to return Area (snake-like starting with 0)
    n_x: int = 3,  # number of rows in the table
    n_y: int = 5,  # number of columns in the table
    start_x: int = VIEWX,  # where the table starts on x-axis
    start_y: int = VIEWY,  # where the table starts on y-axis
    end_x: int = (WIDTH - VIEWX),  # where the table ends on x-axis
    end_y: int = (HEIGHT - VIEWY),  # where the table ends on y-axis
    cells_x: int = 1,  # number of cells to be merged into one in the direction of x-axis
    cells_y: int = 1,  # number of cells to be merged into one in the direction of y-axis
    spacing: int = 0,  # spacing size between cells
) -> Area:
    """
    Returns area (tuple of four integers, in pixels) of a cell on i-th possition
    in a table you define yourself.  Example:

    >>> ui.grid(4, n_x=2, n_y=3, start_x=20, start_y=20)
    (20, 160, 107, 70)

    Returns 5th cell from the following table.  It has two columns, three rows
    and starts on coordinates 20-20.

        |____|____|
        |____|____|
        |XXXX|____|
    """
    w = (end_x - start_x) // n_x
    h = (end_y - start_y) // n_y
    x = (i % n_x) * w
    y = (i // n_x) * h
    return (x + start_x, y + start_y, (w - spacing) * cells_x, (h - spacing) * cells_y)


def in_area(area: Area, x: int, y: int) -> bool:
    ax, ay, aw, ah = area
    return ax <= x <= ax + aw and ay <= y <= ay + ah


# Component events.  Should be different from `io.TOUCH_*` events.
# Event dispatched when components should draw to the display, if they are
# marked for re-paint.
RENDER = const(-255)
# Event dispatched when components should mark themselves for re-painting.
REPAINT = const(-256)

# How long, in microseconds, should the layout rendering task sleep betweeen
# the render calls.
_RENDER_DELAY_US = const(10000)  # 10 msec


class Component:
    """
    Abstract class.

    Components are GUI classes that inherit `Component` and form a tree, with a
    `Layout` at the root, and other components underneath.  Components that
    have children, and therefore need to dispatch events to them, usually
    override the `dispatch` method.  Leaf components usually override the event
    methods (`on_*`).  Components signal a completion to the layout by raising
    an instance of `Result`.
    """

    def dispatch(self, event: int, x: int, y: int) -> None:
        if event is RENDER:
            self.on_render()
        elif event is io.TOUCH_START:
            self.on_touch_start(x, y)
        elif event is io.TOUCH_MOVE:
            self.on_touch_move(x, y)
        elif event is io.TOUCH_END:
            self.on_touch_end(x, y)
        elif event is REPAINT:
            self.repaint = True

    def on_render(self) -> None:
        pass

    def on_touch_start(self, x: int, y: int) -> None:
        pass

    def on_touch_move(self, x: int, y: int) -> None:
        pass

    def on_touch_end(self, x: int, y: int) -> None:
        pass


class Result(Exception):
    """
    When components want to trigger layout completion, they do so through
    raising an instance of `Result`.

    See `Layout.__iter__` for details.
    """

    def __init__(self, value: ResultValue) -> None:
        self.value = value


class Cancelled(Exception):
    """
    Layouts can be explicitly cancelled.  This usually happens when another
    layout starts, because only one layout can be running at the same time,
    and is done by raising `Cancelled` on the cancelled layout.  Layouts
    should always re-raise such exceptions.

    See `Layout.__iter__` for details.
    """

    pass


class Layout(Component):
    """
    Abstract class.

    Layouts are top-level components.  Only one layout can be running at the
    same time.  Layouts provide asynchronous interface, so a running task can
    wait for the layout to complete.  Layouts complete when a `Result` is
    raised, usually from some of the child components.
    """

    async def __iter__(self) -> ResultValue:
        """
        Run the layout and wait until it completes.  Returns the result value.
        Usually not overriden.
        """
        value = None
        try:
            # If any other layout is running (waiting on the layout channel),
            # we close it with the Cancelled exception, and wait until it is
            # closed, just to be sure.
            if layout_chan.takers:
                await layout_chan.put(Cancelled())
            # Now, no other layout should be running.  In a loop, we create new
            # layout tasks and execute them in parallel, while waiting on the
            # layout channel.  This allows other layouts to cancel us, and the
            # layout tasks to trigger restart by exiting (new tasks are created
            # and we continue, because we are in a loop).
            while True:
                await loop.race(layout_chan.take, *self.create_tasks())
        except Result as result:
            # Result exception was raised, this means this layout is complete.
            value = result.value
        return value

    def __await__(self) -> Generator[Any, Any, ResultValue]:
        return self.__iter__()  # type: ignore

    def create_tasks(self) -> Iterable[loop.Task]:
        """
        Called from `__iter__`.  Creates and returns a sequence of tasks that
        run this layout.  Tasks are executed in parallel.  When one of them
        returns, the others are closed and `create_tasks` is called again.

        Usually overriden to add another task to the list."""
        return self.handle_input(), self.handle_rendering()

    def handle_input(self) -> loop.Task:  # type: ignore
        """Task that is waiting for the user input."""
        touch = loop.wait(io.TOUCH)
        while True:
            event, x, y = yield touch
            self.dispatch(event, x, y)
            # We dispatch a render event right after the touch.  Quick and dirty
            # way to get the lowest input-to-render latency.
            self.dispatch(RENDER, 0, 0)

    def handle_rendering(self) -> loop.Task:  # type: ignore
        """Task that is rendering the layout in a busy loop."""
        # Before the first render, we dim the display.
        backlight_fade(style.BACKLIGHT_DIM)
        # Clear the screen of any leftovers, make sure everything is marked for
        # repaint (we can be running the same layout instance multiple times)
        # and paint it.
        display.clear()
        self.dispatch(REPAINT, 0, 0)
        self.dispatch(RENDER, 0, 0)
        # Display is usually refreshed after every loop step, but here we are
        # rendering everything synchronously, so refresh it manually and turn
        # the brightness on again.
        display.refresh()
        backlight_fade(style.BACKLIGHT_NORMAL)
        sleep = loop.sleep(_RENDER_DELAY_US)
        while True:
            # Wait for a couple of ms and render the layout again.  Because
            # components use re-paint marking, they do not really draw on the
            # display needlessly.
            # TODO: remove the busy loop
            yield sleep
            self.dispatch(RENDER, 0, 0)
