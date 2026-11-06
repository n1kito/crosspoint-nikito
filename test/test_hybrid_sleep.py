"""Exercise production sleep routing and file selection with host display/storage doubles."""

from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def method(path, signature, following):
    text = (ROOT / path).read_text()
    return signature + text.split(signature, 1)[1].split(following, 1)[0]


settings = (ROOT / "src/CrossPointSettings.h").read_text()
sleep_enum = settings.split("enum SLEEP_SCREEN_MODE {", 1)[1].split("};", 1)[0]
settings_list = (ROOT / "src/SettingsList.cpp").read_text()
labels = settings_list.split("static constexpr auto SLEEP_SCREEN_VALUES =", 1)[1].split("}();", 1)[0] + "}();"
label_ids = re.findall(r"StrId::(STR_\w+)", labels)

HARNESS = r"""
#include <array>
#include <atomic>
#include <functional>
#include <cassert>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

struct CrossPointSettings {
  enum SLEEP_SCREEN_MODE { SLEEP_ENUM };
  enum QUICK_RESUME_SLEEP_SCREEN { QUICK_RESUME_AFTER_TIMEOUT = 1 };
  uint8_t sleepScreen = DARK, quickResumeSleepScreen = 0, orientation = 0;
};
CrossPointSettings SETTINGS;
enum class StrId { LABEL_IDS };
static constexpr auto SLEEP_SCREEN_VALUES = LABELS
struct { bool lastSleepFromReader = false; } APP_STATE;

struct RenderLock {
  static inline int depth = 0;
  RenderLock() { ++depth; }
  ~RenderLock() { --depth; }
  void unlock() {}
};
class GfxRenderer {
 public:
  enum class Orientation { Portrait };
  bool bookPixels = false;
  int inversions = 0;
  void invertScreen() { ++inversions; }
  void setOrientation(Orientation) {}
};
class MappedInputManager {
 public:
  bool suppressed = true;
  bool consumeSuppressedRelease() { return suppressed; }
  bool wasHomeGesture() const { return false; }
  bool hasTouch() const { return false; }
  bool wasScreenTapped(int&, int&) const { return false; }
  bool wasLightPanelGesture() const { return false; }
};
using ActivityResult = int;
int outgoingTicks = 0;
constexpr int eIncrement = 1;
void xTaskNotify(int, int, int) {}
namespace bleturner { bool beforeScreenChange(int, bool) { return true; } }
namespace haptic_feedback { void touchAction() {} }
namespace HeaderBackTapTarget {
  bool contains(int, int) { return false; }
  void clear() {}
}
struct {
  bool inverted = false;
  bool isInverted() const { return inverted; }
  void setInverted(bool value) { inverted = value; }
} display;
struct { void drawPopup(GfxRenderer&, const char*) {} } GUI;
constexpr int STR_ENTERING_SLEEP = 1;
const char* tr(int) { return "sleep"; }
namespace ReaderUtils { void applyOrientation(GfxRenderer&, uint8_t) {} }
void delay(int) {}
#define LOG_ERR(...) ((void)0)
#define LOG_DBG(...) ((void)0)
enum class BmpReaderError { Ok };
class Bitmap {
 public:
  BmpReaderError rewindToData() const { return BmpReaderError::Ok; }
};

#define private public
#include "activities/boot_sleep/SleepActivity.h"
#undef private

struct ReaderActivity : Activity {
  using Activity::Activity;
  bool pageRenderSucceeded = true, menu = false, ended = false;
  bool isReaderActivity() const override { return true; }
  // Session readiness remains true even after a later page fails.
  bool acceptsRemoteInput() const { return true; }
  HAS_VISIBLE_PAGE
  void loop() override { ++outgoingTicks; renderer.bookPixels = false; }
  bool inputOverPage() const { assert(RenderLock::depth > 0); return menu; }
  bool isAtEndOfBook() const { assert(RenderLock::depth > 0); return ended; }
};
struct ActivityManager {
  enum class PendingAction { None, Replace, ReplaceForSleep, Push, Pop };
  GfxRenderer renderer;
  MappedInputManager mappedInput;
  std::unique_ptr<Activity> currentActivity, pendingActivity;
  std::vector<std::unique_ptr<Activity>> stackActivities;
  std::atomic<bool> requestedUpdate{false};
  int renderTaskHandle = 0, screenVisit = 0;
  PendingAction pendingAction = PendingAction::None;
  int redraws = 0;
  bool redrawSucceeds = true;
  void replaceActivity(std::unique_ptr<Activity> next) {
    pendingActivity = std::move(next);
    pendingAction = PendingAction::Replace;
  }
  void requestUpdateAndWait() {
    assert(RenderLock::depth == 0);
    ++redraws;
    auto& reader = *static_cast<ReaderActivity*>(currentActivity.get());
    reader.pageRenderSucceeded = redrawSucceeds;
    renderer.bookPixels = redrawSucceeds;
  }
  void loop();
  void exitActivity(const RenderLock&) { currentActivity->onExit(); currentActivity.reset(); }
  void goHome() { assert(false); }
  void pushActivity(std::unique_ptr<Activity>) { assert(false); }
  void requestUpdate() {}
  void goToSleep(bool fromTimeout);
  bool isForegroundReader() const;
};

struct FrontlightPanelActivity : Activity {
  FrontlightPanelActivity(GfxRenderer& renderer, MappedInputManager& input) : Activity("light", renderer, input) {}
};
enum class SleepRecentKind { Standard, Overlay };
constexpr const char* TRANSPARENT_SLEEP_ROOT_BMP = "/sleep-overlay.bmp";
constexpr const char* TRANSPARENT_SLEEP_ROOT_PNG = "/sleep-overlay.png";
constexpr const char* TRANSPARENT_SLEEP_DIR = "/.sleep-overlay";
constexpr const char* TRANSPARENT_SLEEP_LEGACY_DIR = "/sleep-overlay";
bool rootValid = true, filesPresent = true, decodeWorks = true;
int defaults = 0, quickResumes = 0, covers = 0, blanks = 0;
int preservedPopups = 0, standardPicks = 0, overlayPicks = 0;
std::vector<std::string> attempted;
bool selectRandomSleepFile(const char* primary, const char* legacy, SleepRecentKind kind, std::string& path) {
  if (kind == SleepRecentKind::Standard) {
    assert(std::string(primary) == "/.sleep" && std::string(legacy) == "/sleep");
    ++standardPicks;
  } else {
    assert(std::string(primary) == "/.sleep-overlay" && std::string(legacy) == "/sleep-overlay");
    ++overlayPicks;
  }
  if (filesPresent) path = std::string(primary) + "/random.bmp";
  return filesPresent;
}
bool drawSleepPopupPreservingFrame(GfxRenderer&) { ++preservedPopups; return true; }
void releaseSdFontCachesForDecode(const GfxRenderer&) {}
void SleepActivity::renderDefaultSleepScreen() const { ++defaults; }
void SleepActivity::renderLastScreenSleepScreen() const { ++quickResumes; }
void SleepActivity::renderBlankSleepScreen() const { ++blanks; }
void SleepActivity::renderCoverSleepScreen() const { ++covers; }
void SleepActivity::renderBitmapSleepScreen(const Bitmap&, bool) const {}
bool SleepActivity::renderCustomSleepBmp(const std::string& path) const {
  attempted.push_back(path);
  return path == "/sleep.bmp" ? rootValid : decodeWorks;
}
bool SleepActivity::renderSleepOverlayPath(const std::string& path) const {
  if (SETTINGS.sleepScreen == CrossPointSettings::CUSTOM_TRANSPARENT) assert(renderer.bookPixels);
  attempted.push_back(path);
  return path == TRANSPARENT_SLEEP_ROOT_BMP || path == TRANSPARENT_SLEEP_ROOT_PNG ? rootValid : decodeWorks;
}
""".replace("SLEEP_ENUM", sleep_enum).replace("LABEL_IDS", ",".join(label_ids)).replace("LABELS", labels)

HARNESS += "\n".join([
    method("src/activities/boot_sleep/SleepActivity.cpp", "void SleepActivity::onEnter()", "bool SleepActivity::renderCustomSleepBmp("),
    method("src/activities/boot_sleep/SleepActivity.cpp", "void SleepActivity::renderCustomSleepScreen() const", "void SleepActivity::renderDefaultSleepScreen()"),
    method("src/activities/boot_sleep/SleepActivity.cpp", "void SleepActivity::renderTransparentCustomSleepScreen() const", "void SleepActivity::renderCoverSleepScreen()"),
    method("src/activities/ActivityManager.cpp", "void ActivityManager::goToSleep(bool fromTimeout)", "void ActivityManager::goToBoot()"),
    method("src/activities/ActivityManager.cpp", "bool ActivityManager::isForegroundReader() const", "bool ActivityManager::isRemoteReaderContext()"),
])
HARNESS += method("src/activities/ActivityManager.cpp", "void ActivityManager::loop()", "void ActivityManager::exitActivity(")
reader_header = (ROOT / "src/activities/reader/ReaderActivity.h").read_text()
visible_page = "bool hasVisiblePage() const" + reader_header.split("bool hasVisiblePage() const", 1)[1].split("\n", 1)[0]
HARNESS = HARNESS.replace("HAS_VISIBLE_PAGE", visible_page)

HARNESS += r"""
void reset() {
  SETTINGS = CrossPointSettings{};
  APP_STATE.lastSleepFromReader = true;
  display.inverted = false;
  rootValid = filesPresent = decodeWorks = true;
  defaults = quickResumes = covers = blanks = preservedPopups = standardPicks = overlayPicks = 0;
  attempted.clear();
  outgoingTicks = 0;
}
void runHybrid(bool ready, bool menu, bool ended, bool child, bool pending, bool timeout, bool quick, bool redrawSucceeds = true) {
  reset();
  SETTINGS.sleepScreen = CrossPointSettings::CUSTOM_TRANSPARENT;
  SETTINGS.quickResumeSleepScreen = quick;
  ActivityManager manager;
  auto reader = std::make_unique<ReaderActivity>("reader", manager.renderer, manager.mappedInput);
  reader->pageRenderSucceeded = ready; reader->menu = menu; reader->ended = ended;
  if (child) manager.currentActivity = std::make_unique<Activity>("menu", manager.renderer, manager.mappedInput);
  else manager.currentActivity = std::move(reader);
  manager.redrawSucceeds = redrawSucceeds;
  if (pending) manager.pendingAction = ActivityManager::PendingAction::Push;
  // A sleep-plugin toast or background framebuffer loan has overwritten the pixels.
  manager.renderer.bookPixels = false;
  display.inverted = true;
  const bool page = ready && !menu && !ended && !child && !pending;
  manager.goToSleep(timeout);
  auto& sleep = *static_cast<SleepActivity*>(manager.currentActivity.get());
  const bool finalPage = page && ((timeout && quick) || redrawSucceeds);
  assert(sleep.fromReaderPage == finalPage);
  assert(manager.redraws == (page && !(timeout && quick) ? 1 : 0));
  assert(manager.pendingAction == ActivityManager::PendingAction::None);
  assert(outgoingTicks == 0);
  if (timeout && quick) {
    assert(quickResumes == 1 && standardPicks == 0 && overlayPicks == 0);
    assert(display.inverted);
  } else if (finalPage) {
    assert(overlayPicks == 1 && standardPicks == 0 && preservedPopups == 1);
    assert(attempted == std::vector<std::string>{"/.sleep-overlay/random.bmp"});
    assert(manager.renderer.inversions == 1 && !display.inverted);
  } else {
    assert(standardPicks == 1 && overlayPicks == 0 && preservedPopups == 0);
    assert(attempted == std::vector<std::string>{"/.sleep/random.bmp"});
  }
}
int main() {
  static_assert(CrossPointSettings::DARK == 0 && CrossPointSettings::LIGHT == 1);
  static_assert(CrossPointSettings::CUSTOM == 2 && CrossPointSettings::COVER == 3);
  static_assert(CrossPointSettings::COVER_CUSTOM == 4 && CrossPointSettings::BLANK == 5);
  static_assert(CrossPointSettings::QUICK_RESUME == 6 && CrossPointSettings::TRANSPARENT_CUSTOM == 7);
  static_assert(CrossPointSettings::COVER_TRANSPARENT == 8 && CrossPointSettings::CUSTOM_TRANSPARENT == 9);
  static_assert(SLEEP_SCREEN_VALUES[CrossPointSettings::CUSTOM_TRANSPARENT] == StrId::STR_CUSTOM_TRANSPARENT);
  for (bool timeout : {false, true}) for (bool quick : {false, true}) {
    runHybrid(true, false, false, false, false, timeout, quick);
    runHybrid(true, true, false, false, false, timeout, quick);  // in-reader toolbar
    runHybrid(true, false, false, true, false, timeout, quick);  // pushed menu/dictionary
    runHybrid(true, false, true, false, false, timeout, quick);  // end-of-book
    runHybrid(false, false, false, false, false, timeout, quick);  // loading/failure
    runHybrid(true, false, false, false, true, timeout, quick);  // pending transition
  }
  runHybrid(true, false, false, false, false, false, false, false);  // redraw fails after a good page
  runHybrid(true, false, false, false, false, true, false, false);
  GfxRenderer renderer;
  MappedInputManager input;
  for (bool page : {false, true}) for (bool present : {false, true}) {
    reset();
    SETTINGS.sleepScreen = CrossPointSettings::CUSTOM_TRANSPARENT;
    renderer.bookPixels = true;
    filesPresent = present;
    decodeWorks = false;
    SleepActivity sleep(renderer, input, false, page);
    sleep.onEnter();
    assert(defaults == 1);  // empty folders and decode failures use the existing fallback
  }
  reset();
  SETTINGS.sleepScreen = CrossPointSettings::CUSTOM;
  SleepActivity custom(renderer, input);
  custom.onEnter();
  assert(attempted == std::vector<std::string>{"/sleep.bmp"} && standardPicks == 0);
  reset();
  SETTINGS.sleepScreen = CrossPointSettings::TRANSPARENT_CUSTOM;
  SleepActivity transparent(renderer, input);
  transparent.onEnter();
  assert(attempted == std::vector<std::string>{"/sleep-overlay.bmp"} && overlayPicks == 0);
  reset();
  SETTINGS.sleepScreen = CrossPointSettings::COVER_TRANSPARENT;
  SleepActivity cover(renderer, input);
  cover.onEnter();
  assert(covers == 1);
}
"""

with tempfile.TemporaryDirectory(prefix="crosspoint-hybrid-sleep-") as directory:
    temporary = Path(directory)
    stub = temporary / "activities/Activity.h"
    stub.parent.mkdir()
    stub.write_text(r"""
#pragma once
class GfxRenderer;
class MappedInputManager;
#include <functional>
#include <string>
class Activity {
 public:
  std::string name;
  ActivityResult result = 0;
  std::function<void(ActivityResult)> resultHandler;
  Activity(const char* name, GfxRenderer& renderer, MappedInputManager&) : name(name), renderer(renderer) {}
  virtual ~Activity() = default;
  virtual void onEnter() {}
  virtual void onExit() {}
  virtual void loop() {}
  virtual bool requiresExclusiveStorageLoop() const { return false; }
  virtual bool isHomeActivity() const { return false; }
  virtual bool handleHomeGesture() { return false; }
  virtual bool isReaderActivity() const { return false; }
 protected:
  GfxRenderer& renderer;
};
""")
    source = temporary / "test.cpp"
    source.write_text(HARNESS)
    executable = temporary / "test"
    subprocess.run(["c++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-I", str(temporary),
                    "-I", str(ROOT / "src"), str(source), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
print("Hybrid sleep routing, context capture, redraw, random selection and fallback checks passed")
