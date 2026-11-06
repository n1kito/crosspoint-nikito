# Nikito customisations

This branch starts from upstream CrossPoint 2.0.0. It adds status-bar visibility controls, an SD-card logo picker, and a Custom + Transparent sleep-screen mode. Other features from the old fork are not ported.

## Status bar

In **Settings → Reader → Customise Status Bar**, enable **Hidden by default** to give EPUB, TXT and Markdown the full reading area. The preview still shows the configured bar.

Choose **Reveal Status Bar** under **Settings → Controls → Short Power Button**. Button-only devices also offer it under **Long Press Menu**; devices with a capacitive Home key offer it in that key's action menu.

The action shows the bar for five seconds. Repeating it restarts the timer. The bar covers the bottom strip of the page temporarily; showing and hiding it do not reflow the book or change the reading position. The power button's existing hold-to-sleep behavior remains available.

For 1-bit XTC books, select **Top** or **Bottom** for **XTC Status Bar** as well. Their existing overlay follows the same hidden/reveal setting. Choosing **Hide** still disables that overlay entirely. Upstream does not draw a status bar on 2-bit XTCH pages, so the reveal action has no effect there.

## Logos

The official CrossPoint logo is the default. Copy small logo files into a folder named **`logos` at the SD-card root**, then choose one under **Settings → Display → Logo**. The saved filename is used at boot and on the default Light/Dark sleep screen until you choose another logo. Select **CrossPoint (default)** to restore the official logo.

Supported files are uncompressed **1-bit black-and-white BMPs**, between 1×1 and 120×120 pixels, no larger than 4 KiB. Smaller images are centered without scaling. Filenames must be shorter than 96 UTF-8 bytes; hidden files and subdirectories are ignored. The picker displays the first 32 valid logos in the directory, sorted by filename. Reopen the picker after adding files.

Copy [flower.bmp](../sd-card/logos/flower.bmp) into `/logos/` to use the flower from the old fork. The firmware keeps using the official logo if the chosen file is missing, invalid, unreadable or cannot be decoded. The filename remains selected, so replacing the file restores the custom logo. Full-screen custom sleep images, book covers and transparent sleep overlays keep their existing behavior.

## Custom + Transparent sleep screen

Choose **Settings → Display → Sleep Screen → Custom + Transparent**.

- Sleeping directly from a rendered EPUB, TXT, Markdown or XTC page picks a random transparent BMP/PNG from `/.sleep-overlay/` or `/sleep-overlay/` and draws it over the retained page.
- Sleeping from Home, Settings, the file browser, a reader menu, a dictionary screen or an end-of-book screen picks a random full-screen BMP from `/.sleep/` or `/sleep/`.

The existing random selection cycles are reused. This mode ignores the single-file root overrides (`sleep.bmp`, `sleep-overlay.bmp`, `sleep-overlay.png`) so an image is selected from the folders each time. An empty folder, invalid image or decode failure falls back to the default sleep screen, including your selected logo. The separate **Quick Resume on Timeout** preference still overrides this mode on automatic sleep.

Before applying a transparent overlay, the reader redraws the page once. This removes sleep-event popups and restores framebuffer contents borrowed by background indexing. If that redraw fails to produce a book page, the mode uses a full-screen custom image instead. It can add a visible refresh and some sleep latency, while avoiding a second retained framebuffer. Menus and Quick Resume-on-timeout do not take this redraw path.

## Verification on the device

- Back up reading progress, open an EPUB and record a sentence near the bottom. Enable hidden mode, reopen the book, then reveal twice. Each press should give five seconds of visibility; hiding the bar should restore the text with no page jump.
- Repeat with TXT/Markdown, grayscale image pages, inverted colors, and all four reader orientations. Check that gray text does not show through the temporary bar. In 1-bit XTC, test both overlay positions.
- Check that touch long-press still selects text, the configured button does not also open the reader menu, and ordinary page turning works during a reveal. Confirm-hold must not also trigger its short-release action. Test automatic page turning and return from a child menu after the timer expires.
- Select the flower, restart, and sleep with both Light and Dark screens. Check the logo's orientation and contrast. Select the default again. Remove or corrupt the selected BMP and confirm that boot/sleep show CrossPoint without changing full-screen sleep images.
- For Custom + Transparent, put at least two BMPs in `/.sleep/` and two transparent BMP/PNGs in `/.sleep-overlay/`. Sleep directly from a book, then from Home and from reader menus/dictionary screens. Expect an overlay only on the actual book page. Repeat in all reader orientations, night mode, manual sleep and automatic sleep. Test empty folders and fixed root files; the new mode must ignore root overrides. With Quick Resume on Timeout enabled, automatic sleep must retain the page instead.
- On resource-constrained boards, measure internal free heap and largest block over repeated picker/reveal visits. On the A4, record internal RAM and PSRAM separately. Device heap, power and visual behavior have not been measured by the host checks.

The picker retains 3,072 bytes of filename storage while open and uses the existing virtualized list UI. Logo drawing allocates one checked `Bitmap` object and at most 46 bytes of row scratch, plus existing HAL file bookkeeping; those objects are released after drawing. Reveal state is reader-owned, guarded by the existing render lock, and starts no task, network connection or background timer.
