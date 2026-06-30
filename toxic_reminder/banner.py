"""Яркая красная плашка поверх всех окон с кнопками «Скрыть»/«Подключиться»."""

import AppKit
import objc

# Контроллеры держим в модульном списке, чтобы их не собрал GC, пока окно открыто.
_controllers: list["BannerController"] = []

# Геометрия плашки.
_HEIGHT = 160.0
_MARGIN = 40.0
_BUTTON_Y = 24.0
_BUTTON_H = 44.0
_BG_COLOR = (0.80, 0.05, 0.05, 1.0)  # насыщенно-красный


class BannerController(AppKit.NSObject):
    # Приватные хелперы названы с `__`: PyObjC не пытается превратить их в
    # Objective-C селекторы (в отличие от методов с одним `_`).

    def initWithTitle_time_link_(self, title, time_str, link):
        self = objc.super(BannerController, self).init()
        if self is None:
            return None
        self.link = link
        self.window = self.__build_window(f"{time_str}  {title}", bool(link))
        return self

    def __build_window(self, text, has_link):
        screen = AppKit.NSScreen.mainScreen().frame()
        rect = AppKit.NSMakeRect(0, screen.size.height - _HEIGHT, screen.size.width, _HEIGHT)
        window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, AppKit.NSWindowStyleMaskBorderless, AppKit.NSBackingStoreBuffered, False,
        )
        window.setLevel_(AppKit.NSScreenSaverWindowLevel)
        window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        window.setBackgroundColor_(
            AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(*_BG_COLOR)
        )
        window.setReleasedWhenClosed_(False)

        view = window.contentView()
        view.addSubview_(self.__make_label(text, screen.size.width))
        view.addSubview_(self.__make_button("Скрыть", _MARGIN, 160, "dismiss:"))
        if has_link:
            connect = self.__make_button("Подключиться", 212, 240, "connect:")
            connect.setKeyEquivalent_("\r")
            view.addSubview_(connect)

        window.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)
        return window

    def __make_label(self, text, screen_width):
        label = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(_MARGIN, 72, screen_width - 2 * _MARGIN, 70)
        )
        label.setStringValue_(text)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setTextColor_(AppKit.NSColor.whiteColor())
        label.setFont_(AppKit.NSFont.boldSystemFontOfSize_(32))
        return label

    def __make_button(self, title, x, width, action):
        button = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(x, _BUTTON_Y, width, _BUTTON_H)
        )
        button.setTitle_(title)
        button.setBezelStyle_(AppKit.NSBezelStyleRounded)
        button.setTarget_(self)
        button.setAction_(action)
        return button

    def connect_(self, sender):
        if self.link:
            url = AppKit.NSURL.URLWithString_(self.link)
            if url is not None:
                AppKit.NSWorkspace.sharedWorkspace().openURL_(url)
        self.__close()

    def dismiss_(self, sender):
        self.__close()

    def __close(self):
        self.window.orderOut_(None)
        if self in _controllers:
            _controllers.remove(self)


def show_banner(title: str, time_str: str, link: str | None) -> BannerController:
    controller = BannerController.alloc().initWithTitle_time_link_(title, time_str, link)
    _controllers.append(controller)
    return controller


if __name__ == "__main__":
    show_banner("Тестовая встреча", "12:30", "https://telemost.yandex.ru/j/0429743918")
    AppKit.NSApp.run()
