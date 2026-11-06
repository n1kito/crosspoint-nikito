"""Exercise the production reveal timer with a host C++ compiler."""

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

reader_source = (ROOT / "src/activities/reader/ReaderActivity.cpp").read_text()
render_method = "void ReaderActivity::render(" + reader_source.split(
    "void ReaderActivity::render(", 1
)[1].split("bool ReaderActivity::handleForcedRefresh()", 1)[0]
input_methods = "bool ReaderActivity::handleStatusBarInput()" + reader_source.split(
    "bool ReaderActivity::handleStatusBarInput()", 1
)[1]

HARNESS = r"""
#include <cassert>
#include <cstdint>
#include <atomic>
#include <memory>
#include <string>
#include <Memory.h>
#include "activities/reader/StatusBarReveal.h"
#include "util/HomeButtonInput.h"

uint32_t nowMs = 0;
uint32_t millis() { return nowMs; }
namespace trustedtime { int trustedNow() { return 0; } }
namespace ReaderUtils { constexpr unsigned long SKIP_HOLD_MS = 700; }
#define LOG_ERR(...) ((void)0)
struct RenderLock {
  enum class Mode { Try };
  static inline bool available = true;
  RenderLock() = default;
  explicit RenderLock(Mode) {}
  template<class T> explicit RenderLock(T&) {}
  bool ownsLock() const { return available; }
};
struct CrossPointSettings {
  enum { LP_MENU_STATUS_BAR = 7 };
  bool statusBarHiddenByDefault = false;
  int longPressMenuFunction = 0;
};
CrossPointSettings SETTINGS;
struct MappedInputManager {
  enum class Button { Confirm };
  HomeButtonAction action = HomeButtonAction::Ignore;
  bool touch = false, held = false;
  HomeButtonAction homeButtonAction() const { return action; }
  bool hasTouch() const { return touch; }
  bool wasLongPressed(Button, unsigned long) { bool result = held; held = false; return result; }
};
struct Renderer {
  void clearScreen() {}
  void displayBuffer() {}
};
struct EndOfBookOptions {
  explicit EndOfBookOptions(Renderer&) {}
  void loadOnce(const std::string&) {}
  void render(Renderer&, MappedInputManager&) {}
};
struct ReaderActivity {
  StatusBarReveal statusBarReveal;
  MappedInputManager mappedInput;
  Renderer renderer;
  std::unique_ptr<EndOfBookOptions> endOfBookOptions;
  std::atomic<bool> endOfBookOptionsReady{false};
  struct {
    void onRenderComplete(uint32_t, int, int) {}
  } readerSession;
  std::string bookPath;
  bool menu = false, renderedBar = false;
  bool pageRenderSucceeded = false, renderSucceeds = true;
  std::atomic<bool> pageRendered{false};
  int updateRequests = 0;
  bool inputOverPage() const { return menu; }
  bool isAtEndOfBook() const { return false; }
  int getProgressBasisPoints() const { return 0; }
  void onEndOfBookRendered() {}
  MARK_PAGE_RENDERED
  void requestUpdate() { ++updateRequests; }
  void renderBook() { renderedBar = isStatusBarVisible(); if (renderSucceeds) markPageRendered(); }
  bool handleStatusBarInput();
  void expireStatusBarReveal();
  bool isStatusBarVisible() const;
  void render(RenderLock&&);
};
""" + render_method + input_methods + r"""

int main() {
  ReaderActivity reader;
  assert(reader.isStatusBarVisible());
  SETTINGS.statusBarHiddenByDefault = true;
  assert(!reader.isStatusBarVisible());
  reader.mappedInput.action = HomeButtonAction::RevealStatusBar;
  assert(reader.handleStatusBarInput());
  assert(reader.updateRequests == 1 && reader.isStatusBarVisible());
  nowMs = 5001;
  // Simulate return from a child: ActivityManager renders before the next loop tick.
  reader.render(RenderLock{});
  assert(!reader.renderedBar);
  assert(reader.pageRenderSucceeded && reader.pageRendered.load());
  reader.renderSucceeds = false;
  reader.render(RenderLock{});
  assert(!reader.pageRenderSucceeded && reader.pageRendered.load());
  reader.renderSucceeds = true;
  reader.expireStatusBarReveal();
  assert(reader.updateRequests == 1);  // no second repaint of the same clean page

  reader.menu = true;
  assert(!reader.handleStatusBarInput());
  assert(reader.updateRequests == 1);
  reader.menu = false;
  reader.mappedInput.action = HomeButtonAction::Ignore;
  SETTINGS.longPressMenuFunction = 7;
  reader.mappedInput.held = true;
  assert(reader.handleStatusBarInput());
  assert(reader.updateRequests == 2);
  reader.mappedInput.touch = true;
  reader.mappedInput.held = true;
  assert(!reader.handleStatusBarInput());  // touch selection retains its long press
  nowMs = 10002;
  RenderLock::available = false;
  reader.expireStatusBarReveal();
  assert(reader.isStatusBarVisible());
  RenderLock::available = true;
  reader.expireStatusBarReveal();
  assert(!reader.isStatusBarVisible() && reader.updateRequests == 3);

  StatusBarReveal reveal;
  assert(!reveal.isVisible());
  assert(!reveal.expire(5000));
  reveal.show(0);
  assert(reveal.isVisible());
  assert(!reveal.expire(4999));
  assert(reveal.expire(5000));
  assert(!reveal.isVisible());
  assert(!reveal.expire(5001));

  reveal.show(6000);
  reveal.show(9000);
  assert(!reveal.expire(11000));
  assert(!reveal.expire(13999));
  assert(reveal.expire(14000));

  reveal.show(UINT32_MAX - 1999);
  assert(!reveal.expire(2999));
  assert(reveal.expire(3000));
  assert(!reveal.isVisible());
}
"""

reader_header = (ROOT / "src/activities/reader/ReaderActivity.h").read_text()
mark_page = "void markPageRendered()" + reader_header.split("void markPageRendered()", 1)[1].split("\n  void rememberBookOnceRendered", 1)[0]
HARNESS = HARNESS.replace("MARK_PAGE_RENDERED", mark_page)

with tempfile.TemporaryDirectory(prefix="crosspoint-status-bar-") as directory:
    source = Path(directory) / "test.cpp"
    executable = Path(directory) / "test"
    source.write_text(HARNESS)
    subprocess.run(
        ["c++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "src"),
         "-I", str(ROOT / "lib/Memory"),
         str(source), "-o", str(executable)],
        check=True,
    )
    subprocess.run([str(executable)], check=True)
print("Status-bar reveal timer, input and child-return checks passed")
